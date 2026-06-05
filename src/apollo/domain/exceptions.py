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
