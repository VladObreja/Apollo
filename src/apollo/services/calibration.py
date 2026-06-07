from __future__ import annotations

import math
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from apollo.db.models import ValidationRecord
from apollo.domain.compartments import Compartment, requires
from apollo.domain.models import CalibrationStats, ConvictionBucket

logger = logging.getLogger(__name__)

_Z95 = 1.96
_N_BINS = 10
_N_BUCKETS = 10


def _wilson_ci(k: int, n: int) -> tuple[float | None, float | None]:
    """Wilson score 95% confidence interval for a proportion k/n."""
    if n == 0:
        return None, None
    p = k / n
    z2 = _Z95 * _Z95
    center = p + z2 / (2 * n)
    margin = _Z95 * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    denom = 1 + z2 / n
    return max(0.0, (center - margin) / denom), min(1.0, (center + margin) / denom)


def _prob_bin(prob: float) -> int:
    """Map predicted probability [0.0, 1.0] to bin index [0, N_BINS-1]."""
    return min(int(prob * _N_BINS), _N_BINS - 1)


def _param_bucket(param_value: float) -> int:
    """Map param_value [0.0, 100.0] to bucket index [0, N_BUCKETS-1]."""
    return max(0, min(int(param_value / (100.0 / _N_BUCKETS)), _N_BUCKETS - 1))


def _compute_brier_score(rows: list[ValidationRecord]) -> float | None:
    scorable = [r for r in rows if r.actual_positive is not None]
    if not scorable:
        return None
    return sum(
        (r.param_value / 100.0 - (1.0 if r.actual_positive else 0.0)) ** 2
        for r in scorable
    ) / len(scorable)


def _compute_ece(rows: list[ValidationRecord]) -> float | None:
    scorable = [r for r in rows if r.actual_positive is not None]
    n = len(scorable)
    if n == 0:
        return None
    bins: dict[int, list[ValidationRecord]] = {b: [] for b in range(_N_BINS)}
    for r in scorable:
        bins[_prob_bin(r.param_value / 100.0)].append(r)
    ece = 0.0
    for b_rows in bins.values():
        if not b_rows:
            continue
        avg_conf = sum(r.param_value / 100.0 for r in b_rows) / len(b_rows)
        frac_pos = sum(1 for r in b_rows if r.actual_positive) / len(b_rows)
        ece += (len(b_rows) / n) * abs(avg_conf - frac_pos)
    return ece


def _compute_hit_rate_with_ci(
    rows: list[ValidationRecord],
) -> tuple[float | None, float | None, float | None]:
    """Returns (hit_rate, ci_lower, ci_upper). All None if no scorable rows."""
    scorable = [r for r in rows if r.actual_positive is not None]
    n = len(scorable)
    if n == 0:
        return None, None, None
    k = sum(1 for r in scorable if r.actual_positive)
    ci_lower, ci_upper = _wilson_ci(k, n)
    return k / n, ci_lower, ci_upper


def _compute_conviction_buckets(rows: list[ValidationRecord]) -> list[ConvictionBucket]:
    """10 equal-width buckets by param_value (0–10, 10–20, … 90–100)."""
    scorable = [r for r in rows if r.actual_positive is not None]
    bucket_rows: dict[int, list[ValidationRecord]] = {b: [] for b in range(_N_BUCKETS)}
    for r in scorable:
        bucket_rows[_param_bucket(r.param_value)].append(r)

    step = 100 // _N_BUCKETS
    buckets: list[ConvictionBucket] = []
    for b in range(_N_BUCKETS):
        lo = b * step
        hi = lo + step
        b_rows = bucket_rows[b]
        bk_n = len(b_rows)
        if bk_n == 0:
            buckets.append(
                ConvictionBucket(
                    label=f"{lo}–{hi}", n=0, avg_conviction=None,
                    hit_rate=None, ci_lower=None, ci_upper=None,
                )
            )
            continue
        avg_conv = sum(r.param_value for r in b_rows) / bk_n
        k_hits = sum(1 for r in b_rows if r.actual_positive)
        hit_rate = k_hits / bk_n
        ci_lower, ci_upper = _wilson_ci(k_hits, bk_n)
        buckets.append(
            ConvictionBucket(
                label=f"{lo}–{hi}", n=bk_n, avg_conviction=avg_conv,
                hit_rate=hit_rate, ci_lower=ci_lower, ci_upper=ci_upper,
            )
        )
    return buckets


class CalibrationService:
    @staticmethod
    @requires(Compartment.CALIBRATION_READ)
    def get_stats(session_factory: sessionmaker[Session]) -> CalibrationStats:
        """Compute calibration statistics over all epistemologically closed sessions.

        Queries ONLY validation_record — never accesses extraction or target data.
        Offset sessions (temporal drift) are excluded from metric computations.
        """
        with session_factory() as session:
            stmt = select(ValidationRecord).where(
                ValidationRecord.closed_at.is_not(None)
            )
            all_rows: list[ValidationRecord] = list(
                session.execute(stmt).scalars().all()
            )

        n_total = len(all_rows)
        offset_rows = [r for r in all_rows if r.validation_status == "offset"]
        scored_rows = [r for r in all_rows if r.validation_status in ("hit", "miss")]
        n_offset = len(offset_rows)
        n_scored = len(scored_rows)

        brier = _compute_brier_score(scored_rows)
        ece = _compute_ece(scored_rows)
        hit_rate, ci_lower, ci_upper = _compute_hit_rate_with_ci(scored_rows)
        buckets = _compute_conviction_buckets(scored_rows)

        logger.info(
            "apollo.calibration: stats computed",
            extra={
                "n_total": n_total,
                "n_offset": n_offset,
                "n_scored": n_scored,
                "brier_score": brier,
                "ece": ece,
                "hit_rate": hit_rate,
            },
        )

        return CalibrationStats(
            n_total=n_total,
            n_offset=n_offset,
            n_scored=n_scored,
            brier_score=brier,
            ece=ece,
            hit_rate=hit_rate,
            hit_rate_ci_lower=ci_lower,
            hit_rate_ci_upper=ci_upper,
            conviction_buckets=buckets,
            computed_at=datetime.now(UTC),
        )
