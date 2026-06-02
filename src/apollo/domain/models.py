from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


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
