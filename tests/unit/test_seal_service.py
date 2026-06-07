"""Unit tests for SealingService — no DB, no IO."""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock

import pytest

from apollo.domain.exceptions import SealingError
from apollo.domain.models import ExtractionResultSchema
from apollo.domain.types import TargetStatus
from apollo.services.seal import SealingService


def _make_dispatched_record(raw_bytes: bytes = b"test email bytes") -> MagicMock:
    record = MagicMock()
    record.id = "test-record-id"
    record.status = TargetStatus.DISPATCHED.value
    record.raw_email_bytes = raw_bytes
    return record


def _make_extraction(param_value: float = 75.0) -> ExtractionResultSchema:
    return ExtractionResultSchema(param_value=param_value)


class TestSealService:
    def test_seal_success(self) -> None:
        record = _make_dispatched_record()
        extraction = _make_extraction()
        session = MagicMock()

        result = SealingService.seal(record, extraction, session, agent_version="1.0.0")

        assert isinstance(result, str)
        assert len(result) == 64
        assert record.status == TargetStatus.SEALED.value
        assert record.extraction_payload == extraction.model_dump(mode="json")
        assert record.sealed_at is not None
        assert record.sealed_at.tzinfo is not None
        assert record.seal_agent_version == "1.0.0"
        session.add.assert_called_once_with(record)

    def test_seal_raw_hash_is_sha256_of_bytes(self) -> None:
        known_bytes = b"known test bytes for hashing"
        record = _make_dispatched_record(raw_bytes=known_bytes)
        extraction = _make_extraction()
        session = MagicMock()

        result = SealingService.seal(record, extraction, session, agent_version="1.0.0")

        assert result == hashlib.sha256(known_bytes).hexdigest()
        assert record.raw_hash == hashlib.sha256(known_bytes).hexdigest()

    def test_seal_extraction_payload_matches_schema(self) -> None:
        record = _make_dispatched_record()
        extraction = _make_extraction(param_value=42.5)
        session = MagicMock()

        SealingService.seal(record, extraction, session, agent_version="1.0.0")

        assert record.extraction_payload == extraction.model_dump(mode="json")

    def test_seal_raises_on_wrong_status(self) -> None:
        record = _make_dispatched_record()
        record.status = TargetStatus.QUEUED.value
        extraction = _make_extraction()
        session = MagicMock()

        with pytest.raises(SealingError, match="expected 'dispatched'"):
            SealingService.seal(record, extraction, session, agent_version="1.0.0")

        session.add.assert_not_called()

    def test_seal_raises_on_missing_raw_bytes(self) -> None:
        record = _make_dispatched_record(raw_bytes=b"")
        extraction = _make_extraction()
        session = MagicMock()

        with pytest.raises(SealingError, match="raw_email_bytes is missing"):
            SealingService.seal(record, extraction, session, agent_version="1.0.0")

        session.add.assert_not_called()

    def test_seal_sealed_at_is_utc_aware(self) -> None:
        record = _make_dispatched_record()
        extraction = _make_extraction()
        session = MagicMock()

        SealingService.seal(record, extraction, session, agent_version="1.0.0")

        assert record.sealed_at.tzinfo is not None
