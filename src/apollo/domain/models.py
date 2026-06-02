from datetime import datetime, UTC
from typing import Literal, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator


class TargetStatement(BaseModel):
    statement: str = Field(
        description="The natural language description of the target."
    )


class TargetParameter(BaseModel):
    name: str = Field(
        description=(
            "The parameter governing what the Asset perceives. "
            "Must be one of the project's controlled vocabulary values: "
            "'vad' (Valence-Arousal-Dominance), 'rvd' (Remote Viewing Descriptor), "
            "'ebf' (Energy-Body-Field), 'receptivity', 'social_field', "
            "'purity_tier', 'admin_awareness_tier'."
        )
    )


class TargetMetadata(BaseModel):
    is_control_target: bool = Field(
        default=False,
        description="Flag indicating if this is a control target (used for calibration baselines).",
    )
    age_in_hours: Optional[int] = Field(
        default=None,
        ge=0,
        description="The age requirement for the target in hours. Must be zero or positive.",
    )


class AdminStateSnapshot(BaseModel):
    awareness_tier: str = Field(
        description="The awareness tier of the admin at session creation (e.g., 'tier1', 'tier2')."
    )
    psychological_context: Optional[str] = Field(
        default=None,
        description="Admin's psychological state narrative at target creation. Optional free-text.",
    )


class TargetConfiguration(BaseModel):
    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the target configuration.",
    )
    target: TargetStatement = Field(description="The target statement.")
    parameter: TargetParameter = Field(description="The parameter for the target.")
    target_metadata: TargetMetadata = Field(
        description="Metadata related to the target (control flag, age constraint)."
    )
    admin_state: AdminStateSnapshot = Field(
        description="The admin's psychological state snapshot at the time of target creation."
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp in UTC.",
    )


class ExtractionResultSchema(BaseModel):
    """LLM-extracted measurements from an Asset reply email.

    All fields carry detailed descriptions because Ollama uses them
    (via model_json_schema()) to understand what to extract from the
    unstructured email body. No field may use Any or be untyped.
    """

    param_value: float = Field(
        ge=0,
        le=100,
        description=(
            "The Asset's primary numerical measurement for the requested parameter "
            "(e.g., VAD, RVD, EBF), on a 0–100 scale. This is the value from the "
            "'PARAM (...)' line in the email reply."
        ),
    )
    measurement_timestamp: datetime | None = Field(
        default=None,
        description=(
            "The exact UTC datetime when the Asset performed the measurement. "
            "Extract from the 'Time of measurement (UTC)' field. "
            "Format as ISO-8601 (e.g., '2026-06-02T14:30:00Z')."
        ),
    )

    @field_validator("measurement_timestamp")
    def validate_tz(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("measurement_timestamp must be timezone-aware (UTC)")
        return v
    asset_location: str | None = Field(
        default=None,
        description=(
            "The Asset's physical location during the measurement session. "
            "Extract verbatim from the 'Location' field."
        ),
    )
    sleep_quality: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description=(
            "The Asset's self-reported sleep quality on a 0–100 scale. "
            "Extract from the 'Sleep quality (0–100)' field. Return null if missing."
        ),
    )
    psychological_state: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description=(
            "The Asset's self-reported psychological state on a 0–100 scale. "
            "Extract from the 'Psychological state (0–100)' field. Return null if missing."
        ),
    )
    social_field: Literal["Isolated", "Familiar", "Unfamiliar"] | None = Field(
        default=None,
        description=(
            "The Asset's social context during measurement. Must be exactly one of: "
            "'Isolated', 'Familiar', or 'Unfamiliar'. "
            "Extract from the 'Social Field' line. Return null if missing or unclear."
        ),
    )
    asset_notes: str | None = Field(
        default=None,
        description=(
            "Any additional qualitative notes or observations written by the Asset "
            "beyond the structured fields."
        ),
    )
