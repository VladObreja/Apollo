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
from apollo.domain.exceptions import ExtractionSchemaError
from apollo.services.dispatch import (
    AGENT_VERSION,
    DispatchService,
    SMTPClient,
    SMTPClientImpl,
)
from apollo.services.email_poller import (
    EmailPollerService,
    IMAPClient,
    IMAPClientImpl,
)
from apollo.services.extract import (
    ExtractionService,
    LLMClient,
    OllamaClientImpl,
)
from apollo.services.queue import DAILY_TARGET_CAP, QueueService, count_available_slots

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def tick(
    smtp_client: SMTPClient | None = None,
    llm_client: LLMClient | None = None,
    imap_client: IMAPClient | None = None,
) -> None:
    """Execute one worker tick: claim targets, dispatch emails, extract replies.

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

        Phase 3 — Email Ingestion & Extraction (dispatched, reply received):
            10. Poll IMAP for unseen Asset reply emails.
            11. Match each email to a dispatched record by coordinate.
            12. Store raw email bytes on matched record (durable before LLM call).
            13. For each match: call Ollama LLM with ExtractionResultSchema schema.
            14. On ExtractionSchemaError: log, leave record dispatched (Story 2.3 quarantines).
            15. On success: log result (Story 2.2 seals the record).

    Args:
        smtp_client: Optional SMTP client (DI for tests). Default: SMTPClientImpl.
        llm_client: Optional LLM client (DI for tests). Default: OllamaClientImpl.
        imap_client: Optional IMAP client (DI for tests). Default: IMAPClientImpl.

    No in-memory queue state is maintained between ticks.
    """
    from apollo.config import settings as _settings

    if smtp_client is None:
        smtp_client = SMTPClientImpl(_settings)

    if llm_client is None:
        llm_client = OllamaClientImpl(
            _settings.ollama_base_url,
            _settings.ollama_model_digest,
            _settings.ollama_timeout_seconds,
        )

    if imap_client is None:
        imap_client = IMAPClientImpl(_settings)

    env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=False)

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

    # ------------------------------------------------------------------
    # Phase 3: email ingestion & extraction (dispatched → extraction attempt)
    # ------------------------------------------------------------------
    with SessionFactory() as read_session:
        matched_pairs = EmailPollerService.fetch_new_session_emails(
            read_session, SessionFactory, imap_client
        )

    extraction_success = 0
    extraction_failed = 0

    for record, raw_bytes in matched_pairs:
        body = EmailPollerService.parse_email_body(raw_bytes)
        try:
            _result = ExtractionService.extract(record, body, llm_client, env)
            extraction_success += 1
            logger.info(
                "apollo.worker.tick: extraction succeeded",
                extra={"record_id": str(record.id)},
            )
            # Story 2.2: SealingService.seal(record, raw_bytes, _result) goes here
        except ExtractionSchemaError as exc:
            extraction_failed += 1
            logger.error(
                "apollo.worker.tick: extraction failed after retry",
                extra={"record_id": str(record.id), "error": str(exc)},
            )
            # Story 2.3: QuarantineService.quarantine(...) goes here
        except Exception as exc:
            extraction_failed += 1
            logger.error(
                "apollo.worker.tick: extraction crashed unexpectedly",
                extra={"record_id": str(record.id), "error": str(exc)},
            )

    if matched_pairs:
        logger.info(
            "apollo.worker.tick: extraction phase complete",
            extra={
                "success": extraction_success,
                "failed": extraction_failed,
            },
        )
