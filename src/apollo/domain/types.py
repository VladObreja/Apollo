"""
Domain-level type definitions for Apollo.

Enums defined here are used for application-level type safety.
Database columns use plain String to preserve Alembic migration reversibility
(Postgres ENUM types require non-transactional ALTER TYPE ADD VALUE).
"""

from enum import Enum


class TargetStatus(str, Enum):
    """State machine for a corpus_record's lifecycle."""

    PENDING = "pending"
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    SEALED = "sealed"
