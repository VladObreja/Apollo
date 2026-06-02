"""Apollo worker daemon — stateless tick function.

Designed to be called by a cron/systemd timer via ``apollo tick``.
Each invocation is perfectly idempotent: running N times is equivalent
to running once if no new state arrives between calls.

Idempotency is guaranteed by:
1. FOR UPDATE SKIP LOCKED — concurrent ticks skip already-claimed records.
2. Status state machine — only 'pending' records are eligible for claiming.
"""

import logging

from apollo.db.session import get_session_factory
from apollo.services.queue import DAILY_TARGET_CAP, QueueService, count_available_slots

logger = logging.getLogger(__name__)


def tick() -> None:
    """Execute one worker tick: claim pending targets and assign coordinates.

    Steps:
        1. Open a DB transaction.
        2. Count dispatched-today to compute available slots.
        3. If slots available, claim eligible pending records (SKIP LOCKED).
        4. Assign a cryptographic double-blind coordinate to each.
        5. Commit (automatic on SessionFactory.begin() context exit).
        6. Log a structured summary.

    No in-memory queue state is maintained between ticks.
    """
    SessionFactory = get_session_factory()
    with SessionFactory.begin() as session:
        available_slots = count_available_slots(session)

        if available_slots <= 0:
            logger.info(
                "apollo.worker.tick: daily cap reached",
                extra={"daily_cap": DAILY_TARGET_CAP, "slots_available": 0},
            )
            return

        records = QueueService.claim_pending_targets(session, limit=available_slots)

        if not records:
            logger.info(
                "apollo.worker.tick: no pending targets available",
                extra={"slots_available": available_slots},
            )
            return

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
