from typing import Optional

from apollo.domain.models import (
    AdminStateSnapshot,
    TargetConfiguration,
    TargetMetadata,
    TargetParameter,
    TargetStatement,
)
from apollo.mcp.server import mcp
from apollo.services.target import TargetService


@mcp.tool()
def configure_target(
    target_statement: str,
    parameter_name: str,
    admin_awareness_tier: str,
    is_control_target: bool = False,
    age_in_hours: Optional[int] = None,
    admin_psychological_context: Optional[str] = None,
    real_money_at_stake: bool = False,
    asset_financial_awareness: Optional[bool] = None,
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

    Returns:
        Confirmation string with the assigned target configuration ID.
    """
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
    )

    TargetService.create_target_configuration(config)
    return f"Target configuration created successfully with ID: {config.id}"
