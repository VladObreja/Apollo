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

from sqlalchemy.exc import IntegrityError

from apollo.db.models import CorpusRecord
from apollo.db.session import get_session_factory
from apollo.domain.exceptions import (
    ExtractionSchemaError,
    SealingError,
)
from apollo.domain.types import TargetStatus
from apollo.services.dispatch import (
    AGENT_VERSION,
    DispatchService,
    SMTPClient,
    SMTPClientImpl,
)
from apollo.services.fingerprint import (
    EnvDataClient,
    FingerprintService,
    NoaaClientImpl,
)
from apollo.services.closure import ClosureService
from apollo.services.validate import (
    MarketDataClient,
    ValidationService,
    YahooFinanceClientImpl,
)
from apollo.services.quarantine import QuarantineService
from apollo.services.seal import SealingService
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

# The only unique constraint that can fire on a concurrent Phase 3 seal commit:
# two ticks both compute the same SHA-256 of identical raw_email_bytes and both
# attempt to set corpus_record.raw_hash (f6a7b8c9d0e1_add_sealing_columns.py:64).
_CONCURRENT_SEAL_CONSTRAINT = "ix_corpus_record_raw_hash"


def _is_concurrent_seal_collision(exc: IntegrityError) -> bool:
    """True if `exc` is the expected concurrent-seal unique constraint violation.

    Reads the Postgres constraint name off the underlying psycopg2 diagnostics
    (`exc.orig.diag.constraint_name`) defensively via getattr, since `exc.orig`
    is typed as `BaseException | None` and may not carry `.diag` (e.g. in tests
    that construct a plain `Exception()` as `.orig`).
    """
    constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    return constraint_name == _CONCURRENT_SEAL_CONSTRAINT


def tick(
    smtp_client: SMTPClient | None = None,
    llm_client: LLMClient | None = None,
    imap_client: IMAPClient | None = None,
    env_client: EnvDataClient | None = None,
    market_client: MarketDataClient | None = None,
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
            15. On success: seal record, then attach environmental fingerprint (Story 2.4).

        Phase 4 — Ground-Truth Validation (sealed, past expiry → validation_record):
            16. Query sealed records with ticker + expiry_at set, past expiry, no validation_record.
            17. Fetch OHLCV for each via MarketDataClient.
            18. Compute actual_change_pct; compare to threshold + direction.
            19. Write validation_record (new derived row, never alters corpus_record).
            20. If market data unavailable: log, skip, retry on next tick (no row = pending).

        Phase 5 — Closure Ceremony (validated, un-closed → closed, email dispatched):
            21. Check if interval constraint satisfied (elapsed >= closure_ceremony_interval_days).
            22. Fetch all validation_records with closed_at=NULL via JOIN with corpus_record.
            23. Render closure.jinja with full outcome data (target revealed — double-blind lifted).
            24. Send closure ceremony email to Asset via SMTP.
            25. On success: batch-update closed_at for all included validation_records atomically.
            26. On SMTP failure: log, leave records un-closed for retry on next tick.

    Args:
        smtp_client: Optional SMTP client (DI for tests). Default: SMTPClientImpl.
        llm_client: Optional LLM client (DI for tests). Default: OllamaClientImpl.
        imap_client: Optional IMAP client (DI for tests). Default: IMAPClientImpl.
        env_client: Optional env data client (DI for tests). Default: NoaaClientImpl.
        market_client: Optional market data client (DI for tests). Default: YahooFinanceClientImpl.

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

    if env_client is None:
        env_client = NoaaClientImpl()

    if market_client is None:
        market_client = YahooFinanceClientImpl()

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
            _measurement_ts = _result.measurement_timestamp
            _sealed_hash: str | None = None
            _real_money: bool | None = None
            _awareness: bool | None = None
            with SessionFactory.begin() as write_session:
                fresh_seal: CorpusRecord | None = write_session.get(
                    CorpusRecord, record.id
                )
                if fresh_seal is None:
                    extraction_failed += 1
                    logger.warning(
                        "apollo.worker.tick: record vanished before sealing",
                        extra={"record_id": str(record.id)},
                    )
                elif fresh_seal.status != TargetStatus.DISPATCHED.value:
                    extraction_failed += 1
                    logger.warning(
                        "apollo.worker.tick: record no longer dispatched before sealing",
                        extra={
                            "record_id": str(record.id),
                            "status": fresh_seal.status,
                        },
                    )
                else:
                    _sealed_hash = SealingService.seal(
                        fresh_seal, _result, write_session
                    )
                    _real_money = fresh_seal.real_money_at_stake
                    _awareness = fresh_seal.asset_financial_awareness
            if _sealed_hash is not None:
                extraction_success += 1
                logger.info(
                    "apollo.worker.tick: record sealed",
                    extra={
                        "record_id": str(record.id),
                        "raw_hash": _sealed_hash,
                        "seal_agent_version": AGENT_VERSION,
                        "real_money_at_stake": _real_money,
                        "asset_financial_awareness": _awareness,
                    },
                )
                try:
                    FingerprintService.attach(
                        record, _measurement_ts, env_client, SessionFactory
                    )
                except Exception as fp_exc:
                    logger.error(
                        "apollo.worker.tick: fingerprint failed after sealing — record sealed but unfingerprintable",
                        extra={"record_id": str(record.id), "error": str(fp_exc)},
                    )
        except IntegrityError as exc:
            # Narrow to the expected concurrent-seal unique constraint violation
            # (ix_corpus_record_raw_hash). Any other IntegrityError is unexpected
            # and counted/logged distinctly — it must not be silently treated as
            # "already sealed".
            if _is_concurrent_seal_collision(exc):
                logger.warning(
                    "apollo.worker.tick: concurrent seal detected — record already sealed",
                    extra={
                        "record_id": str(record.id),
                        "constraint": _CONCURRENT_SEAL_CONSTRAINT,
                    },
                )
            else:
                extraction_failed += 1
                logger.error(
                    "apollo.worker.tick: unexpected integrity error during sealing",
                    extra={"record_id": str(record.id), "error": str(exc)},
                )
        except ExtractionSchemaError as exc:
            extraction_failed += 1
            logger.error(
                "apollo.worker.tick: extraction failed — quarantining",
                extra={"record_id": str(record.id), "error": str(exc)},
            )
            try:
                QuarantineService.quarantine(
                    record, exc, env, smtp_client, SessionFactory
                )
            except Exception as qe:
                logger.error(
                    "apollo.worker.tick: quarantine failed",
                    extra={"record_id": str(record.id), "error": str(qe)},
                )
        except SealingError as exc:
            extraction_failed += 1
            logger.error(
                "apollo.worker.tick: sealing pre-condition failed",
                extra={"record_id": str(record.id), "error": str(exc)},
            )
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

    # ------------------------------------------------------------------
    # Phase 3b: dead-letter records stuck with raw_email_bytes == b"" (AC5)
    #
    # A dispatched record with raw_email_bytes already set to b"" (non-None
    # but falsy) is permanently invisible to
    # EmailPollerService.fetch_new_session_emails (its `is not None` check
    # skips it forever). Route it through QuarantineService — the same path
    # used for ExtractionSchemaError — to clear raw_email_bytes (un-sticking
    # the poller) and record durable evidence of the dead-letter.
    # ------------------------------------------------------------------
    with SessionFactory() as read_session:
        stuck_records = SealingService.fetch_stuck_empty_bytes_records(read_session)

    for stuck_record in stuck_records:
        logger.warning(
            "apollo.worker.tick: dead-lettering record stuck with empty raw_email_bytes",
            extra={"record_id": str(stuck_record.id)},
        )
        try:
            QuarantineService.quarantine(
                stuck_record,
                ExtractionSchemaError("raw_email_bytes is empty (b'') — dead-lettered"),
                env,
                smtp_client,
                SessionFactory,
            )
        except Exception as exc:
            logger.error(
                "apollo.worker.tick: dead-letter quarantine failed",
                extra={"record_id": str(stuck_record.id), "error": str(exc)},
            )

    # ------------------------------------------------------------------
    # Phase 4: ground-truth validation (sealed, past expiry → validation_record)
    # ------------------------------------------------------------------
    validated_count, skipped_count = ValidationService.validate_pending(
        SessionFactory, market_client
    )
    if validated_count > 0 or skipped_count > 0:
        logger.info(
            "apollo.worker.tick: validation phase complete",
            extra={"validated": validated_count, "skipped": skipped_count},
        )

    # ------------------------------------------------------------------
    # Phase 5: closure ceremony (validated, un-closed → closed + email)
    # ------------------------------------------------------------------
    try:
        closed_count, email_sent = ClosureService.close_pending(
            SessionFactory,
            smtp_client,
            env,
            _settings.asset_email_address,
            interval_days=_settings.closure_ceremony_interval_days,
        )
        if email_sent:
            logger.info(
                "apollo.worker.tick: closure ceremony dispatched",
                extra={"closed_count": closed_count},
            )
    except Exception as exc:
        logger.error(
            "apollo.worker.tick: closure ceremony crashed",
            extra={"error": str(exc)},
        )
