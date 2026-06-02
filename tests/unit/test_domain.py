"""Unit tests for domain models — pure Python, no IO or DB calls."""
from apollo.domain.models import (
    AdminStateSnapshot,
    TargetConfiguration,
    TargetMetadata,
    TargetParameter,
    TargetStatement,
)


def test_target_configuration_creation() -> None:
    target = TargetStatement(statement="The target is a red apple.")
    parameter = TargetParameter(name="vad")
    target_metadata = TargetMetadata(is_control_target=True, age_in_hours=48)
    admin_state = AdminStateSnapshot(
        awareness_tier="tier1", psychological_context="calm"
    )

    config = TargetConfiguration(
        target=target,
        parameter=parameter,
        target_metadata=target_metadata,
        admin_state=admin_state,
    )

    assert config.target.statement == "The target is a red apple."
    assert config.parameter.name == "vad"
    assert config.target_metadata.is_control_target is True
    assert config.target_metadata.age_in_hours == 48
    assert config.admin_state.awareness_tier == "tier1"
    assert config.admin_state.psychological_context == "calm"
    assert config.id is not None
    assert config.created_at is not None


def test_age_in_hours_rejects_negative() -> None:
    """age_in_hours must be >= 0."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TargetMetadata(is_control_target=False, age_in_hours=-1)


def test_target_configuration_defaults() -> None:
    """Verify optional fields default correctly."""
    config = TargetConfiguration(
        target=TargetStatement(statement="Test target"),
        parameter=TargetParameter(name="rvd"),
        target_metadata=TargetMetadata(),
        admin_state=AdminStateSnapshot(awareness_tier="tier2"),
    )

    assert config.target_metadata.is_control_target is False
    assert config.target_metadata.age_in_hours is None
    assert config.admin_state.psychological_context is None
