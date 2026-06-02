"""Unit tests for domain models — pure Python, no IO or DB calls."""

from apollo.domain.models import (
    AdminStateSnapshot,
    ExtractionResultSchema,
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


class TestExtractionResultSchema:
    def test_json_schema_is_valid_dict(self) -> None:
        """model_json_schema() must return a non-empty dict with typed properties."""
        schema = ExtractionResultSchema.model_json_schema()
        assert isinstance(schema, dict)
        assert len(schema) > 0
        # Every property must have a type or anyOf (no bare {} untyped properties)
        properties = schema.get("properties", {})
        assert len(properties) > 0
        for prop_name, prop_schema in properties.items():
            assert "type" in prop_schema or "anyOf" in prop_schema, (
                f"Property '{prop_name}' has no type constraint"
            )

    def test_json_schema_has_required_param_value(self) -> None:
        """param_value must appear as a required property."""
        schema = ExtractionResultSchema.model_json_schema()
        properties = schema.get("properties", {})
        assert "param_value" in properties
        required = schema.get("required", [])
        assert "param_value" in required

    def test_param_value_valid(self) -> None:
        """param_value within 0-100 is accepted."""
        s = ExtractionResultSchema(param_value=75.0)
        assert s.param_value == 75.0

    def test_param_value_rejects_above_100(self) -> None:
        """param_value > 100 must be rejected."""
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ExtractionResultSchema(param_value=101.0)

    def test_param_value_rejects_below_0(self) -> None:
        """param_value < 0 must be rejected."""
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ExtractionResultSchema(param_value=-1.0)

    def test_optional_fields_default_to_none(self) -> None:
        """All optional fields must default to None."""
        s = ExtractionResultSchema(param_value=50.0)
        assert s.measurement_timestamp is None
        assert s.asset_location is None
        assert s.sleep_quality is None
        assert s.psychological_state is None
        assert s.social_field is None
        assert s.asset_notes is None

    def test_sleep_quality_rejects_out_of_range(self) -> None:
        """sleep_quality must be 0-100 when provided."""
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ExtractionResultSchema(param_value=50.0, sleep_quality=150.0)

    def test_all_fields_populated(self) -> None:
        """All fields can be set together."""
        from datetime import UTC, datetime

        s = ExtractionResultSchema(
            param_value=72.5,
            measurement_timestamp=datetime(2026, 6, 2, 14, 30, 0, tzinfo=UTC),
            asset_location="Bucharest",
            sleep_quality=85.0,
            psychological_state=70.0,
            social_field="Isolated",
            asset_notes="Strong signal, clear impression.",
        )
        assert s.param_value == 72.5
        assert s.asset_location == "Bucharest"
        assert s.social_field == "Isolated"


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
