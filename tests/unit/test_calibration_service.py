"""Unit tests for CalibrationService and its pure math helpers.

Frozen corpus: 10 scored sessions + 1 offset, with hand-computed expected values.

Corpus (param_value, actual_positive, status):
  80.0  True  hit
  70.0  True  hit
  60.0  False miss
  90.0  True  hit
  30.0  False miss
  50.0  True  hit
  55.0  True  hit
  40.0  False miss
  75.0  True  hit
  85.0  False miss
  65.0  True  offset  ← excluded from scoring

Expected (hand-computed):
  Brier:    0.19875
  ECE:      0.355
  Hit rate: 0.6    Wilson 95% CI: [0.31267, 0.83182]
"""
from __future__ import annotations

import pytest
from datetime import UTC, datetime
from unittest.mock import MagicMock

from apollo.services.calibration import (
    _compute_brier_score,
    _compute_ece,
    _compute_hit_rate_with_ci,
    _compute_conviction_buckets,
    _wilson_ci,
    CalibrationService,
)
from apollo.domain.models import CalibrationStats


def _make_vr(
    param_value: float,
    actual_positive: bool | None,
    status: str = "hit",
    closed_at: datetime | None = None,
) -> MagicMock:
    r = MagicMock()
    r.param_value = param_value
    r.actual_positive = actual_positive
    r.validation_status = status
    r.closed_at = closed_at or datetime.now(UTC)
    return r


SCORED_ROWS = [
    _make_vr(80.0, True,  "hit"),
    _make_vr(70.0, True,  "hit"),
    _make_vr(60.0, False, "miss"),
    _make_vr(90.0, True,  "hit"),
    _make_vr(30.0, False, "miss"),
    _make_vr(50.0, True,  "hit"),
    _make_vr(55.0, True,  "hit"),
    _make_vr(40.0, False, "miss"),
    _make_vr(75.0, True,  "hit"),
    _make_vr(85.0, False, "miss"),
]

OFFSET_ROW = _make_vr(65.0, True, "offset")
ALL_ROWS = SCORED_ROWS + [OFFSET_ROW]


class TestWilsonCI:
    def test_zero_n_returns_none(self) -> None:
        lo, hi = _wilson_ci(0, 0)
        assert lo is None
        assert hi is None

    def test_all_hits(self) -> None:
        lo, hi = _wilson_ci(5, 5)
        assert lo is not None and hi is not None
        assert lo < 1.0 <= hi

    def test_zero_hits(self) -> None:
        lo, hi = _wilson_ci(0, 5)
        assert lo is not None and hi is not None
        assert lo <= 0.0 < hi

    def test_known_values(self) -> None:
        lo, hi = _wilson_ci(6, 10)
        assert lo == pytest.approx(0.31267, abs=1e-4)
        assert hi == pytest.approx(0.83182, abs=1e-4)

    def test_bounds_within_zero_one(self) -> None:
        for k in range(11):
            lo, hi = _wilson_ci(k, 10)
            assert lo is not None and hi is not None
            assert 0.0 <= lo <= 1.0
            assert 0.0 <= hi <= 1.0


class TestBrierScore:
    def test_hand_computed_value(self) -> None:
        result = _compute_brier_score(SCORED_ROWS)
        assert result == pytest.approx(0.19875, abs=1e-6)

    def test_empty_returns_none(self) -> None:
        assert _compute_brier_score([]) is None

    def test_perfect_predictor(self) -> None:
        rows = [
            _make_vr(100.0, True),
            _make_vr(100.0, True),
        ]
        result = _compute_brier_score(rows)
        assert result == pytest.approx(0.0, abs=1e-6)

    def test_worst_predictor(self) -> None:
        rows = [
            _make_vr(100.0, False),
            _make_vr(0.0, True),
        ]
        result = _compute_brier_score(rows)
        assert result == pytest.approx(1.0, abs=1e-6)

    def test_rows_with_none_actual_positive_excluded(self) -> None:
        rows = SCORED_ROWS + [_make_vr(50.0, None)]
        result = _compute_brier_score(rows)
        assert result == pytest.approx(0.19875, abs=1e-6)


class TestECE:
    def test_hand_computed_value(self) -> None:
        result = _compute_ece(SCORED_ROWS)
        assert result == pytest.approx(0.355, abs=1e-6)

    def test_empty_returns_none(self) -> None:
        assert _compute_ece([]) is None

    def test_perfect_calibration_zero_ece(self) -> None:
        # Bins that match fraction of positives perfectly
        rows = [
            _make_vr(90.0, True),
            _make_vr(90.0, True),
            _make_vr(90.0, True),
            _make_vr(90.0, True),
            _make_vr(90.0, True),
            _make_vr(90.0, True),
            _make_vr(90.0, True),
            _make_vr(90.0, True),
            _make_vr(90.0, True),
            _make_vr(90.0, False),
        ]
        result = _compute_ece(rows)
        assert result is not None
        assert result == pytest.approx(0.0, abs=1e-2)

    def test_non_negative(self) -> None:
        result = _compute_ece(SCORED_ROWS)
        assert result is not None
        assert result >= 0.0


class TestHitRateWithCI:
    def test_hand_computed_values(self) -> None:
        hr, lo, hi = _compute_hit_rate_with_ci(SCORED_ROWS)
        assert hr == pytest.approx(0.6, abs=1e-6)
        assert lo == pytest.approx(0.31267, abs=1e-4)
        assert hi == pytest.approx(0.83182, abs=1e-4)

    def test_empty_returns_all_none(self) -> None:
        hr, lo, hi = _compute_hit_rate_with_ci([])
        assert hr is None and lo is None and hi is None

    def test_all_miss(self) -> None:
        rows = [_make_vr(20.0, False, "miss")] * 5
        hr, lo, hi = _compute_hit_rate_with_ci(rows)
        assert hr == pytest.approx(0.0, abs=1e-6)
        assert lo is not None and hi is not None

    def test_none_actual_excluded(self) -> None:
        rows = SCORED_ROWS + [_make_vr(50.0, None)]
        hr, _, _ = _compute_hit_rate_with_ci(rows)
        assert hr == pytest.approx(0.6, abs=1e-6)


class TestConvictionBuckets:
    def test_returns_ten_buckets(self) -> None:
        buckets = _compute_conviction_buckets(SCORED_ROWS)
        assert len(buckets) == 10

    def test_bucket_labels(self) -> None:
        buckets = _compute_conviction_buckets(SCORED_ROWS)
        assert buckets[0].label == "0–10"
        assert buckets[5].label == "50–60"
        assert buckets[9].label == "90–100"

    def test_bucket_counts(self) -> None:
        buckets = _compute_conviction_buckets(SCORED_ROWS)
        assert buckets[0].n == 0   # 0-10
        assert buckets[3].n == 1   # 30-40: 30.0
        assert buckets[4].n == 1   # 40-50: 40.0
        assert buckets[5].n == 2   # 50-60: 50.0, 55.0
        assert buckets[6].n == 1   # 60-70: 60.0
        assert buckets[7].n == 2   # 70-80: 70.0, 75.0
        assert buckets[8].n == 2   # 80-90: 80.0, 85.0
        assert buckets[9].n == 1   # 90-100: 90.0

    def test_bucket_hit_rates(self) -> None:
        buckets = _compute_conviction_buckets(SCORED_ROWS)
        assert buckets[5].hit_rate == pytest.approx(1.0, abs=1e-6)   # 50-60: 2/2
        assert buckets[7].hit_rate == pytest.approx(1.0, abs=1e-6)   # 70-80: 2/2
        assert buckets[8].hit_rate == pytest.approx(0.5, abs=1e-6)   # 80-90: 1/2
        assert buckets[9].hit_rate == pytest.approx(1.0, abs=1e-6)   # 90-100: 1/1

    def test_empty_bucket_has_none_values(self) -> None:
        buckets = _compute_conviction_buckets(SCORED_ROWS)
        assert buckets[0].hit_rate is None
        assert buckets[0].ci_lower is None
        assert buckets[0].ci_upper is None
        assert buckets[0].avg_conviction is None

    def test_bucket_80_90_wilson_ci(self) -> None:
        # k=1, n=2 → Wilson CI
        buckets = _compute_conviction_buckets(SCORED_ROWS)
        assert buckets[8].ci_lower == pytest.approx(0.0945, abs=1e-3)
        assert buckets[8].ci_upper == pytest.approx(0.9055, abs=1e-3)

    def test_empty_rows_returns_ten_empty_buckets(self) -> None:
        buckets = _compute_conviction_buckets([])
        assert len(buckets) == 10
        assert all(b.n == 0 for b in buckets)


class TestOffsetExclusion:
    def test_offset_rows_excluded_from_brier(self) -> None:
        brier_without_offset = _compute_brier_score(SCORED_ROWS)
        brier_with_offset = _compute_brier_score(ALL_ROWS)
        # offset row has status='offset' but _compute_brier_score
        # receives only scored rows; this test verifies isolation by
        # simulating what CalibrationService does (filter before passing)
        assert brier_without_offset == pytest.approx(0.19875, abs=1e-6)
        assert brier_with_offset != pytest.approx(0.19875, abs=1e-6)

    def test_get_stats_excludes_offset(self) -> None:
        from unittest.mock import MagicMock
        from sqlalchemy.orm import sessionmaker

        mock_session_factory = MagicMock(spec=sessionmaker)
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_session_factory.return_value = mock_ctx

        mock_ctx.execute.return_value.scalars.return_value.all.return_value = ALL_ROWS

        stats = CalibrationService.get_stats(mock_session_factory)

        assert stats.n_total == 11
        assert stats.n_offset == 1
        assert stats.n_scored == 10
        assert stats.brier_score == pytest.approx(0.19875, abs=1e-6)
        assert stats.hit_rate == pytest.approx(0.6, abs=1e-6)


class TestCalibrationServiceEmptyCorpus:
    def test_empty_corpus_returns_null_metrics(self) -> None:
        from unittest.mock import MagicMock
        from sqlalchemy.orm import sessionmaker

        mock_session_factory = MagicMock(spec=sessionmaker)
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_session_factory.return_value = mock_ctx

        mock_ctx.execute.return_value.scalars.return_value.all.return_value = []

        stats = CalibrationService.get_stats(mock_session_factory)

        assert isinstance(stats, CalibrationStats)
        assert stats.n_total == 0
        assert stats.n_scored == 0
        assert stats.brier_score is None
        assert stats.ece is None
        assert stats.hit_rate is None
        assert stats.hit_rate_ci_lower is None
        assert stats.hit_rate_ci_upper is None
        assert len(stats.conviction_buckets) == 10
