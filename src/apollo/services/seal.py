"""Epistemological sealing service.

Implements the dispatched → sealed lifecycle transition: hashes raw email bytes,
stores the validated extraction payload, and writes provenance columns.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from apollo.db.models import CorpusRecord
from apollo.domain.compartments import Compartment, requires
from apollo.domain.exceptions import SealingError
from apollo.domain.models import ExtractionResultSchema
from apollo.domain.types import TargetStatus
from apollo.services.dispatch import AGENT_VERSION


class SealingService:
    @staticmethod
    @requires(Compartment.EXTRACTION_WRITE)
    def seal(
        record: CorpusRecord,
        extraction: ExtractionResultSchema,
        session: Session,
        agent_version: str = AGENT_VERSION,
    ) -> str:
        """Seal a corpus_record: hash raw bytes, store extraction, advance to 'sealed'.

        Args:
            record: A dispatched CorpusRecord with raw_email_bytes set.
            extraction: Validated ExtractionResultSchema from the LLM.
            session: Active SQLAlchemy session within a transaction.
            agent_version: Apollo package version string.

        Returns:
            raw_hash: SHA-256 hex digest of raw_email_bytes.

        Raises:
            SealingError: If record is not dispatched or raw_email_bytes is missing.
        """
        if record.status != TargetStatus.DISPATCHED.value:
            raise SealingError(
                f"Cannot seal record {record.id}: expected 'dispatched', got '{record.status}'"
            )
        if not record.raw_email_bytes:
            raise SealingError(
                f"Cannot seal record {record.id}: raw_email_bytes is missing"
            )

        raw_hash = hashlib.sha256(record.raw_email_bytes).hexdigest()

        record.extraction_payload = extraction.model_dump(mode="json")
        record.raw_hash = raw_hash
        record.status = TargetStatus.SEALED.value
        record.sealed_at = datetime.now(UTC)
        record.seal_agent_version = agent_version
        session.add(record)

        return raw_hash
