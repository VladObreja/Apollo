"""Unit tests for mcp/tools.py pure helper functions — no DB, no IO."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from apollo.mcp.tools import _parse_expiry_at


class TestParseExpiryAt:
    def test_none_returns_none(self) -> None:
        assert _parse_expiry_at(None) is None

    def test_z_suffix(self) -> None:
        result = _parse_expiry_at("2026-06-10T21:00:00Z")
        assert result == datetime(2026, 6, 10, 21, 0, tzinfo=UTC)
        assert result is not None and result.tzinfo is not None

    def test_positive_offset_converted_to_utc(self) -> None:
        result = _parse_expiry_at("2026-06-10T21:00:00+02:00")
        assert result == datetime(2026, 6, 10, 19, 0, tzinfo=UTC)
        assert result is not None and result.tzinfo is not None

    def test_negative_offset_converted_to_utc(self) -> None:
        result = _parse_expiry_at("2026-06-10T21:00:00-05:00")
        assert result == datetime(2026, 6, 11, 2, 0, tzinfo=UTC)
        assert result is not None and result.tzinfo is not None

    def test_date_only_defaults_to_utc_midnight(self) -> None:
        result = _parse_expiry_at("2026-06-10")
        assert result == datetime(2026, 6, 10, 0, 0, tzinfo=UTC)
        assert result is not None and result.tzinfo is not None

    def test_naive_datetime_assumed_utc(self) -> None:
        result = _parse_expiry_at("2026-06-10T21:00:00")
        assert result == datetime(2026, 6, 10, 21, 0, tzinfo=UTC)
        assert result is not None and result.tzinfo is not None

    def test_malformed_string_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            _parse_expiry_at("not-a-date")
