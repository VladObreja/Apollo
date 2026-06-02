"""Apollo worker daemon — stateless tick function.

Designed to be called by a cron/systemd timer via ``apollo tick``.
Each invocation is perfectly idempotent: running N times is equivalent
to running once if no new state arrives between calls.

Idempotency is guaranteed by:
1. FOR UPDATE SKIP LOCKED — concurrent ticks skip already-claimed records.
2. Status state machine — only 'pending' records are eligible for claiming,
   and only 'queued' records are eligible for dispatch.
3. Per-record SMTP transactions — a send failure leaves the record in
   'queued' so the next tick retries it (fail-operational).
"""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from apollo.db.models import CorpusRecord
from apollo.db.session import get_session_factory
from apollo.services.dispatch import (
    AGENT_VERSION,
    DispatchService,
    SMTPClient,
    SMTPClientImpl,
)
from apollo.services.queue import DAILY_TARGET_CAP, QueueService, count_available_slots

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def tick(smtp_client: SMTPClient | None = None) -> None:
    """Execute one worker tick: claim pending targets, assign coordinates, dispatch emails.

    Steps:
        Phase 1 — Coordinate Assignment (pending → queued):
            1. Open a DB transaction.
            2. Count dispatched-today to compute available slots.
            3. If slots available, claim eligible pending records (SKIP LOCKED).
            4. Assign a cryptographic double-blind coordinate to each.
            5. Commit (automatic on SessionFactory.begin() context exit).

        Phase 2 — Email Dispatch (queued → dispatched):
            6. Fetch ALL queued records (including any left over from prior ticks).
            7. For each: render Jinja2 tasking email, send via SMTP.
            8. On success: mark dispatched (individual transaction per record).
            9. On SMTP failure: log error, leave record in 'queued', continue.

    Args:
        smtp_client: Optional SMTP client for dependency injection in tests.
                     If None, creates SMTPClientImpl(settings) at runtime.

    No in-memory queue state is maintained between ticks.
    """
    if smtp_client is None:
        from apollo.config import settings as _settings

        smtp_client = SMTPClientImpl(_settings)

    SessionFactory = get_session_factory()

    # ------------------------------------------------------------------
    # Phase 1: pending → queued
    # ------------------------------------------------------------------
    with SessionFactory.begin() as session:
        available_slots = count_available_slots(session)

        if available_slots <= 0:
            logger.info(
                "apollo.worker.tick: daily cap reached",
                extra={"daily_cap": DAILY_TARGET_CAP, "slots_available": 0},
            )
        else:
            records = QueueService.claim_pending_targets(session, limit=available_slots)

            if not records:
                logger.info(
                    "apollo.worker.tick: no pending targets available",
                    extra={"slots_available": available_slots},
                )
            else:
                for record in records:
                    QueueService.assign_coordinate(record, session)

                logger.info(
                    "apollo.worker.tick: coordinates assigned",
                    extra={
                        "assigned_count": len(records),
                        "slots_available": available_slots,
                        "daily_cap": DAILY_TARGET_CAP,
                    },
                )
    # Phase 1 transaction committed here

    # ------------------------------------------------------------------
    # Phase 2: queued → dispatched
    # ------------------------------------------------------------------
    env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=False)

    from apollo.config import settings as _settings

    with SessionFactory() as read_session:
        queued = DispatchService.fetch_queued_for_dispatch(read_session)

        dispatched_count = 0
        failed_count = 0

        for record in queued:
            try:
                subject, body = DispatchService.render_tasking_email(record, env)
                smtp_client.send_message(
                    to=_settings.asset_email_address,
                    subject=subject,
                    body=body,
                )
                with SessionFactory.begin() as write_session:
                    fresh: CorpusRecord | None = write_session.get(
                        CorpusRecord, record.id
                    )
                    if fresh is not None:
                        from apollo.domain.types import TargetStatus

                        if fresh.status == TargetStatus.QUEUED.value:
                            DispatchService.mark_dispatched(
                                fresh, write_session, AGENT_VERSION
                            )
                        else:
                            logger.warning(
                                "apollo.worker.tick: record no longer queued",
                                extra={
                                    "record_id": str(record.id),
                                    "status": fresh.status,
                                },
                            )
                dispatched_count += 1
            except Exception as exc:
                failed_count += 1
                logger.error(
                    "apollo.worker.tick: dispatch failed",
                    extra={"record_id": str(record.id), "error": str(exc)},
                )

    if queued:
        logger.info(
            "apollo.worker.tick: dispatch phase complete",
            extra={
                "dispatched_count": dispatched_count,
                "failed_count": failed_count,
            },
        )
