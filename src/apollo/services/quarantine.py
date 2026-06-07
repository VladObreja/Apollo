"""Quarantine service — exception path for failed extractions (Story 2.3).

When ExtractionService raises ExtractionSchemaError, QuarantineService:
  1. Re-fetches the corpus_record and copies raw_email_bytes into a new quarantine_record.
  2. Clears corpus_record.raw_email_bytes = None so the IMAP poller accepts Jane's reply.
  3. Renders clarification.jinja (coordinate + parameter only — zero target identity).
  4. Sends clarification via SMTP (fail-operational: tick continues on OSError).
  5. On SMTP success: records clarification_sent_at on the quarantine row.

Two-transaction pattern (same as SealingService):
  Transaction 1 — atomic: create quarantine_record, clear raw bytes.
  SMTP send between transactions (fail-operational).
  Transaction 2 — conditional: set clarification_sent_at on success.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from jinja2 import Environment
from sqlalchemy.orm import Session, sessionmaker

from apollo.db.models import CorpusRecord, QuarantineRecord
from apollo.domain.compartments import Compartment, requires
from apollo.domain.exceptions import ExtractionSchemaError, QuarantineError
from apollo.services.dispatch import AGENT_VERSION, SMTPClient

logger = logging.getLogger(__name__)


class QuarantineService:
    @staticmethod
    @requires(Compartment.EXTRACTION_WRITE)
    def quarantine(
        record: CorpusRecord,
        exc: ExtractionSchemaError,
        env: Environment,
        smtp_client: SMTPClient,
        session_factory: sessionmaker[Session],
        agent_version: str = AGENT_VERSION,
    ) -> None:
        """Quarantine a failed extraction and send a clarification email to the Asset.

        Args:
            record: The detached CorpusRecord that failed extraction (must have raw_email_bytes).
            exc: The ExtractionSchemaError that triggered quarantine.
            env: Configured Jinja2 Environment with access to clarification.jinja.
            smtp_client: SMTPClient implementation for sending the clarification.
            session_factory: SQLAlchemy sessionmaker for write transactions.
            agent_version: Apollo package version string.

        Raises:
            QuarantineError: If the record is not found, raw_email_bytes is None,
                or the clarification template is missing/invalid.
        """
        quarantine_id = uuid4()
        coordinate: str | None = None
        parameter: str | None = None

        # --- Transaction 1: create quarantine row, clear raw bytes (atomic) ---
        with session_factory.begin() as write_session:
            fresh: CorpusRecord | None = write_session.get(CorpusRecord, record.id)
            if fresh is None:
                raise QuarantineError(
                    f"Cannot quarantine: corpus_record {record.id} not found"
                )
            if fresh.raw_email_bytes is None:
                raise QuarantineError(
                    f"Cannot quarantine: corpus_record {record.id} has no raw_email_bytes"
                )

            # Cache values needed after the transaction closes
            coordinate = fresh.double_blind_coordinate
            parameter = fresh.parameter_name

            if not coordinate:
                raise QuarantineError(
                    f"Cannot render clarification: record {record.id} missing double_blind_coordinate"
                )

            qr = QuarantineRecord(
                id=quarantine_id,
                corpus_record_id=fresh.id,
                raw_email_bytes=fresh.raw_email_bytes,
                quarantine_reason="extraction_schema_error",
                error_detail=str(exc),
                quarantined_at=datetime.now(UTC),
            )
            write_session.add(qr)

            # Clear raw bytes so the IMAP poller can accept Jane's clarification reply
            fresh.raw_email_bytes = None
            write_session.add(fresh)
        # Committed here — quarantine_record exists, raw_email_bytes cleared

        # --- Render clarification email (no IO, no DB) ---
        template = env.get_template("clarification.jinja")
        rendered = template.render(coordinate=coordinate, parameter=parameter)

        lines = rendered.splitlines()
        subject_line = lines[0] if lines else ""
        if not subject_line.startswith("Subject: "):
            raise QuarantineError(
                "clarification.jinja did not produce a valid 'Subject: ' header"
            )

        subject = subject_line.removeprefix("Subject: ").strip()
        body = "\n".join(lines[1:]).lstrip("\n")

        if not body.strip():
            raise QuarantineError("clarification.jinja rendered an empty email body")

        # --- SMTP send (fail-operational, outside any transaction) ---
        from apollo.config import settings as _settings

        smtp_succeeded = False
        try:
            smtp_client.send_message(
                to=_settings.asset_email_address,
                subject=subject,
                body=body,
            )
            smtp_succeeded = True
        except OSError:
            logger.warning(
                "apollo.quarantine: clarification SMTP failed — quarantine_record committed",
                extra={
                    "record_id": str(record.id),
                    "quarantine_id": str(quarantine_id),
                },
            )

        # --- Transaction 2: record clarification dispatch time (only on SMTP success) ---
        if smtp_succeeded:
            with session_factory.begin() as write_session:
                fresh_qr: QuarantineRecord | None = write_session.get(
                    QuarantineRecord, quarantine_id
                )
                if fresh_qr is not None:
                    fresh_qr.clarification_sent_at = datetime.now(UTC)
                    fresh_qr.clarification_agent_version = agent_version
                    write_session.add(fresh_qr)
                else:
                    logger.warning(
                        "apollo.quarantine: quarantine_record vanished before T2 — clarification_sent_at not recorded",
                        extra={
                            "record_id": str(record.id),
                            "quarantine_id": str(quarantine_id),
                        },
                    )
