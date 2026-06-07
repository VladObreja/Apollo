"""Domain-specific exceptions for Apollo.

Never raise generic Exception or ValueError — use these named exceptions
so the worker daemon can handle specific failure modes safely.
"""


class ExtractionSchemaError(Exception):
    """Raised when the LLM fails to produce a valid ExtractionResultSchema after one retry.

    Caught in worker.tick() Phase 3 per-record loop. The raw email bytes
    are already stored on the corpus_record; Story 2.3 will route this
    to the quarantine table.
    """


class SealingError(Exception):
    """Raised when sealing preconditions fail (wrong status or missing raw bytes).

    Caught in worker.tick() Phase 3 per-record loop.
    """


class QuarantineError(Exception):
    """Raised when quarantine pre-conditions fail (record not found, raw_email_bytes missing,
    or template/rendering failure). Caught in worker.tick() Phase 3 per-record loop.
    Non-fatal — logged and tick continues.
    """


class MarketDataError(Exception):
    """Raised when market data cannot be fetched or parsed for a validation record.

    Caught in ValidationService.validate_pending(). Never propagates to tick() caller.
    """
