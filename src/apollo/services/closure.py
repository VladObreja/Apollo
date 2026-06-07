"""Closure ceremony service — aggregate validated sessions and dispatch closure email (Story 3.2).

Two-step fail-operational pattern:
    1. Fetch pending sessions, acquire advisory lock, and check interval (read-only).
    2. Render closure.jinja and send SMTP.
    3. On SMTP success: batch-commit closed_at in one transaction.
    On SMTP failure: log, return (0, False) — records remain open for retry.
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from jinja2 import Environment
from sqlalchemy import func, select, text, update as sa_update
from sqlalchemy.orm import Session, sessionmaker

from apollo.db.models import CorpusRecord, ValidationRecord
from apollo.domain.compartments import Compartment, requires
from apollo.services.dispatch import SMTPClient

logger = logging.getLogger(__name__)

# Stable advisory lock key for the closure ceremony — prevents concurrent ticks from
# double-sending when the systemd timer fires twice or a manual trigger overlaps a tick.
_CLOSURE_ADVISORY_LOCK_KEY = 0x636C6F73  # hex("clos")


@dataclass(frozen=True)
class ClosureSessionSummary:
    validation_record_id: UUID
    coordinate: str
    parameter_name: str
    target_statement: str
    param_value: float
    validation_status: str
    actual_change_pct: float | None
    actual_positive: bool | None
    predicted_positive: bool | None
    validated_at: datetime


class ClosureService:
    @staticmethod
    @requires(Compartment.CALIBRATION_WRITE)
    def close_pending(
        session_factory: sessionmaker[Session],
        smtp_client: SMTPClient,
        env: Environment,
        recipient: str,
        interval_days: int | None = None,
        limit: int = 500,
    ) -> tuple[int, bool]:
        """Aggregate un-closed validated sessions and send closure ceremony email.

        Uses a Postgres advisory lock to prevent concurrent ticks from sending
        duplicate ceremonies. The second caller bails out gracefully if the lock
        is already held.

        Three-step fail-operational pattern:
            1. Acquire advisory lock + fetch pending sessions + check interval (read-only).
            2. Render closure.jinja and send SMTP.
            3. On SMTP success: batch-commit closed_at in one atomic transaction.
               On SMTP failure: log, return (0, False) — records remain open for retry.
               On write failure after send: log, return (0, False) — duplicate ceremony
               possible on next tick but preferable to silent data loss.

        Returns: (closed_count, email_sent)
        """
        now = datetime.now(UTC)

        with session_factory() as session:
            # Advisory lock: non-blocking — if another tick holds it, bail out.
            lock_acquired = session.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": _CLOSURE_ADVISORY_LOCK_KEY},
            ).scalar()
            if not lock_acquired:
                logger.info(
                    "apollo.closure: advisory lock held by another process — skipping this tick"
                )
                return 0, False

            try:
                if interval_days is not None and interval_days > 0:
                    last_sent = ClosureService._get_last_ceremony_timestamp(session)
                    if last_sent is not None:
                        elapsed_days = (now - last_sent).total_seconds() / 86400.0
                        if elapsed_days < interval_days:
                            return 0, False

                pending = ClosureService._fetch_pending(session, limit)
            finally:
                session.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": _CLOSURE_ADVISORY_LOCK_KEY},
                )

        if not pending:
            return 0, False

        subject, body = ClosureService._render_email(pending, env, now)

        try:
            smtp_client.send_message(to=recipient, subject=subject, body=body)
        except (OSError, smtplib.SMTPException, ValueError) as exc:
            logger.error(
                "apollo.closure: SMTP send failed — sessions remain open for retry",
                extra={"pending_count": len(pending), "error": str(exc)},
            )
            return 0, False

        ids = [s.validation_record_id for s in pending]
        try:
            with session_factory.begin() as write_session:
                updated = ClosureService._mark_closed(ids, write_session, now)
                if updated == 0:
                    logger.warning(
                        "apollo.closure: _mark_closed affected 0 rows — records may have been closed concurrently",
                        extra={"expected_ids": len(ids)},
                    )
        except Exception as exc:
            logger.error(
                "apollo.closure: DB write failed after SMTP send — ceremony email sent but closed_at not committed; retry possible on next tick",
                extra={"closed_count": len(ids), "error": str(exc)},
            )
            return 0, False

        logger.info(
            "apollo.closure: closure ceremony dispatched",
            extra={
                "closed_count": len(pending),
                "validation_record_ids": [str(i) for i in ids],
            },
        )
        return len(pending), True

    @staticmethod
    def _get_last_ceremony_timestamp(session: Session) -> datetime | None:
        """Return the most recent closed_at value, or None if nothing has ever been closed."""
        return session.execute(
            select(func.max(ValidationRecord.closed_at))
        ).scalar_one_or_none()

    @staticmethod
    def _fetch_pending(session: Session, limit: int) -> list[ClosureSessionSummary]:
        """JOIN validation_record with corpus_record to fetch un-closed sessions."""
        stmt = (
            select(ValidationRecord, CorpusRecord)
            .join(CorpusRecord, ValidationRecord.corpus_record_id == CorpusRecord.id)
            .where(ValidationRecord.closed_at.is_(None))
            .order_by(ValidationRecord.validated_at.asc())
            .limit(limit)
        )
        rows = session.execute(stmt).all()
        if len(rows) == limit:
            logger.warning(
                "apollo.closure: _fetch_pending result capped at limit — additional records may be pending",
                extra={"limit": limit},
            )
        return [
            ClosureSessionSummary(
                validation_record_id=vr.id,
                coordinate=cr.double_blind_coordinate or "(no coordinate)",
                parameter_name=cr.parameter_name,
                target_statement=cr.target_statement,
                param_value=vr.param_value,
                validation_status=vr.validation_status,
                actual_change_pct=vr.actual_change_pct,
                actual_positive=vr.actual_positive,
                predicted_positive=vr.predicted_positive,
                validated_at=vr.validated_at,
            )
            for vr, cr in rows
        ]

    @staticmethod
    def _mark_closed(
        validation_ids: list[UUID],
        session: Session,
        now: datetime,
    ) -> int:
        """Batch-update closed_at for all validation records in one statement. Returns row count."""
        result = session.execute(
            sa_update(ValidationRecord)
            .where(ValidationRecord.id.in_(validation_ids))
            .values(closed_at=now)
        )
        return result.rowcount

    @staticmethod
    def _render_email(
        sessions: list[ClosureSessionSummary],
        env: Environment,
        now: datetime,
    ) -> tuple[str, str]:
        """Render closure.jinja and extract subject + body (same convention as dispatch.py)."""
        generated_at = now.strftime("%Y-%m-%d %H:%M UTC")
        template = env.get_template("closure.jinja")
        rendered = template.render(sessions=sessions, generated_at=generated_at)

        lines = rendered.splitlines()
        subject_line = lines[0] if lines else ""
        if not subject_line.startswith("Subject: "):
            raise ValueError("closure.jinja did not produce a valid 'Subject: ' header")

        subject = subject_line.removeprefix("Subject: ").strip()
        body = "\n".join(lines[1:]).lstrip("\n")

        if not body.strip():
            raise ValueError("closure.jinja rendered an empty email body")

        return subject, body
