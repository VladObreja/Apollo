from __future__ import annotations

import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

from apollo.domain.models import (
    AdminStateSnapshot,
    TargetConfiguration,
    TargetMetadata,
    TargetParameter,
    TargetStatement,
)
from apollo.mcp.server import mcp
from apollo.services.target import TargetService


def _parse_expiry_at(expiry_at: str | None) -> datetime | None:
    """Parse an ISO-8601 datetime or date string into a UTC-aware datetime.

    Accepts a `Z` suffix, explicit `+HH:MM`/`-HH:MM` offsets, or a bare
    date/naive datetime (assumed UTC). Returns `None` if `expiry_at` is `None`.
    """
    if expiry_at is None:
        return None
    try:
        parsed = datetime.fromisoformat(expiry_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            f"expiry_at must be a valid ISO-8601 datetime or date (e.g. '2026-06-10T21:00:00Z' or '2026-06-10'): {exc}"
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


@mcp.tool()
def configure_target(
    target_statement: str,
    parameter_name: str,
    admin_awareness_tier: str,
    is_control_target: bool = False,
    age_in_hours: int | None = None,
    admin_psychological_context: str | None = None,
    real_money_at_stake: bool = False,
    asset_financial_awareness: bool | None = None,
    ticker: str | None = None,
    expiry_at: str | None = None,
    threshold_pct: float | None = None,
    threshold_direction: str | None = None,
) -> str:
    """
    Configure a new target and persist it to the database.

    Args:
        target_statement: Natural language description of the target.
        parameter_name: Domain parameter (e.g. 'vad', 'rvd', 'ebf').
        admin_awareness_tier: Admin's awareness tier at session creation.
        is_control_target: True if this is a calibration control target.
        age_in_hours: Optional age constraint for the target in hours (≥ 0).
        admin_psychological_context: Optional free-text admin state narrative.
        real_money_at_stake: 2x2 Stakes Matrix — whether real capital is objectively at stake.
        asset_financial_awareness: 2x2 Stakes Matrix — whether the Asset believes capital is at stake.
        ticker: Market symbol for ground-truth validation (e.g. 'GC=F' for Gold, 'EURUSD=X' for EUR/USD).
        expiry_at: ISO-8601 datetime or date when the market outcome should be checked (e.g. '2026-06-10T21:00:00Z'). Accepts a 'Z' suffix, explicit '+HH:MM'/'-HH:MM' offsets, or a bare date/naive datetime (assumed UTC).
        threshold_pct: Required percentage change for a positive outcome (e.g. 9.0 means 9%).
        threshold_direction: Direction for a positive outcome: 'UP' or 'DOWN'.

    Returns:
        Confirmation string with the assigned target configuration ID.
    """
    expiry_dt = _parse_expiry_at(expiry_at)

    target = TargetStatement(statement=target_statement)
    parameter = TargetParameter(name=parameter_name)
    target_metadata = TargetMetadata(
        is_control_target=is_control_target,
        age_in_hours=age_in_hours,
    )
    admin_state = AdminStateSnapshot(
        awareness_tier=admin_awareness_tier,
        psychological_context=admin_psychological_context,
    )

    config = TargetConfiguration(
        target=target,
        parameter=parameter,
        target_metadata=target_metadata,
        admin_state=admin_state,
        real_money_at_stake=real_money_at_stake,
        asset_financial_awareness=asset_financial_awareness,
        ticker=ticker,
        expiry_at=expiry_dt,
        threshold_pct=threshold_pct,
        threshold_direction=threshold_direction,
    )

    TargetService.create_target_configuration(config)
    return f"Target configuration created successfully with ID: {config.id}"


@mcp.tool()
def trigger_closure_ceremony() -> str:
    """Trigger an immediate closure ceremony, ignoring the configured interval.

    Aggregates all validated-but-not-yet-closed sessions and dispatches
    the definitive outcomes email to the Asset. Can be called at any time
    regardless of when the last scheduled ceremony was sent.

    Returns:
        Confirmation string with count of sessions closed, 'No sessions pending closure'
        if nothing was pending, or 'SMTP failed — check logs' if delivery failed.
    """
    from pathlib import Path

    from jinja2 import Environment, FileSystemLoader

    from apollo.config import settings as _settings
    from apollo.db.session import get_session_factory
    from apollo.services.closure import ClosureService
    from apollo.services.dispatch import SMTPClientImpl

    try:
        smtp_client = SMTPClientImpl(_settings)
        env = Environment(
            loader=FileSystemLoader(str(Path(__file__).parent.parent / "templates")),
            autoescape=False,
        )
        session_factory = get_session_factory()
    except Exception as exc:
        return f"Closure ceremony setup failed: {exc}"

    try:
        closed_count, email_sent = ClosureService.close_pending(
            session_factory,
            smtp_client,
            env,
            _settings.asset_email_address,
            interval_days=None,  # On-demand: bypass interval check
        )
    except Exception as exc:
        return f"Closure ceremony failed unexpectedly: {exc}"

    if email_sent:
        return f"Closure ceremony dispatched: {closed_count} session(s) epistemologically closed."
    if closed_count == 0:
        return "No validated sessions pending closure."
    return "SMTP delivery failed — sessions remain open for retry. Check logs."


@mcp.tool()
def get_calibration_stats() -> str:
    """Compute and return statistical calibration metrics over all closed sessions.

    Calculates Brier score, Expected Calibration Error (ECE), and empirical hit
    rates with Wilson 95% confidence intervals. Sessions flagged as 'offset'
    (temporal drift > 2h) are excluded from scoring but reported separately.
    Operates exclusively over the validation_record table — the extraction
    compartment is never accessed (double-blind integrity preserved).

    Returns:
        A formatted human-readable calibration readout.
    """
    from apollo.db.session import get_session_factory
    from apollo.services.calibration import CalibrationService

    try:
        session_factory = get_session_factory()
        stats = CalibrationService.get_stats(session_factory)
    except Exception as exc:
        logger.exception("apollo.calibration_stats: unexpected error")
        return f"Calibration stats failed: {exc}"

    def _fmt_rate(v: float | None) -> str:
        return f"{v * 100:.2f}%" if v is not None else "—"

    def _fmt_ci(lo: float | None, hi: float | None) -> str:
        if lo is None or hi is None:
            return "—"
        return f"[{lo * 100:.2f}% – {hi * 100:.2f}%]"

    def _fmt_float(v: float | None, decimals: int = 4) -> str:
        return f"{v:.{decimals}f}" if v is not None else "—"

    lines = [
        "=== Apollo Calibration Statistics ===",
        f"Corpus: {stats.n_total} closed session(s)"
        f" ({stats.n_offset} offset excluded, {stats.n_scored} scored)",
        f"Computed: {stats.computed_at.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
        "--- Overall Metrics ---",
        f"Brier Score:   {_fmt_float(stats.brier_score)}"
        "  (lower → better; random ≈ 0.25)",
        f"ECE:           {_fmt_float(stats.ece)}",
        f"Hit Rate:      {_fmt_rate(stats.hit_rate)}"
        f"  Wilson 95% CI: {_fmt_ci(stats.hit_rate_ci_lower, stats.hit_rate_ci_upper)}",
        "",
        "--- Conviction Buckets (param_value range → hit rate) ---",
        f"{'Bucket':>8}  {'N':>5}  {'Hit Rate':>10}  {'95% CI':>25}",
    ]

    for bk in stats.conviction_buckets:
        rate_str = _fmt_rate(bk.hit_rate)
        ci_str = _fmt_ci(bk.ci_lower, bk.ci_upper)
        lines.append(
            f"{bk.label:>8}  {bk.n:>5}  {rate_str:>10}  {ci_str:>25}"
        )

    return "\n".join(lines)
