# Epistemological Schema Architecture (Radiesthesia Protocol)

Based on the foundational project axioms, the brainstorming session data, and the latest epistemological clarifications, the asset operates as a precision numerical instrument (Romanian radiesthesia). The complexity and ambiguity are pushed entirely upstream onto the system's ability to formulate questions and pair them with parameters.

## Core Schema Requirements

1. **The Target-Parameter Coordinate System:** The core of the protocol is the pairing of an Affirmation (e.g., "ABCD rises > 9% by June 10") with a specific Parameter (e.g., VAD). This pairing is assigned a CRV-style coordinate (XXXX/YYYY).
2. **Protocol Purity (Double-Blind vs. Front-Loaded):** The system must support varying degrees of asset front-loading. Initially, the asset sees only `XXXX/YYYY` and the instruction "Please measure the variable of interest associated with this target." Later, the system may explore fully front-loading the affirmation. The schema must track the exact protocol used for every session.
3. **Empirical Optimization:** Over time, the corpus must allow us to determine which affirmation formulations and parameter pairings yield the highest calibrated confidence. 
4. **Immutable Raw Data, Mutable Interpretation:** The raw email bytes are immutable. The extracted numerical values (`vad`, `rvd`, `ebf`) are derived child records.

---

## Proposed Database Schema (SQLAlchemy Core Models)

### 1. `corpus_record` (The Immutable Ledger)
This is the root table for all event-sourced facts.
```python
class CorpusRecord(Base):
    __tablename__ = 'corpus_record'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_type = Column(String(50), nullable=False) # 'raw_email', 'extraction', 'market_outcome'
    session_id = Column(UUID(as_uuid=True), ForeignKey('session.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    parent_id = Column(UUID(as_uuid=True), ForeignKey('corpus_record.id'), nullable=True)
    payload = Column(JSONB, nullable=False) # The actual data
    raw_hash = Column(String(64), nullable=False, unique=True) # SHA-256 for immutability
```

### 2. `asset` (Anonymization-by-Design)
```python
class Asset(Base):
    __tablename__ = 'asset'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codename = Column(String(50), unique=True, nullable=False) # e.g., 'Asset-1'
    research_email = Column(String(255), unique=True, nullable=False) # e.g., 'apollo.asset1@proton.me'
    # STRICTLY NO PII (Names, DOBS, personal addresses are forbidden by design)
```

### 3. `question_template`, `target`, and `parameter` (The Epistemological Vocabulary)
```python
class QuestionTemplate(Base):
    """
    Empirically ranked templates. The tasking question IS the trade specification.
    e.g., "{ticker} rises > {threshold}% by {expiry_date}"
    """
    __tablename__ = 'question_template'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_string = Column(String, nullable=False)
    question_class = Column(String(50)) # e.g., "directional", "magnitude"

class TargetInstance(Base):
    """
    The materialized target. Defines the criteria for validation (and manual bracket orders).
    """
    __tablename__ = 'target_instance'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey('question_template.id'), nullable=False)
    ticker = Column(String(20), nullable=False) # Can be a concept or non-financial entity
    threshold_value = Column(Float, nullable=True) # The Take Profit (TP) trigger for validation
    expiry_date = Column(DateTime(timezone=True), nullable=False)
    is_validatable = Column(Boolean, default=True) # False for historical/abstract targets (Brief Addendum)

class Parameter(Base):
    """
    The fluid registry of variables the asset can measure.
    """
    __tablename__ = 'parameter'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False) # e.g., "VAD", "RVD"
    scale = Column(String(50), nullable=False, default="0-100")
    unit = Column(String(20), nullable=False, default="%")
    is_active = Column(Boolean, default=True)
```

### 4. `session` and `session_event` (The Operational Envelope & Provenance Chain)
```python
class Session(Base):
    __tablename__ = 'session'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey('asset.id'), nullable=False)
    
    # The CRV Coordinate Assignment
    target_id = Column(UUID(as_uuid=True), ForeignKey('target_instance.id'), nullable=False)
    parameter_id = Column(UUID(as_uuid=True), ForeignKey('parameter.id'), nullable=False)
    coordinate = Column(String(9), nullable=False, unique=True) # e.g., "XXXX/YYYY"
    
    # Epistemological / Protocol Factors
    protocol_type = Column(String(50), nullable=False) # 'DoubleBlind_NoContext', 'FrontLoaded'
    
    # Operational timestamps
    issued_at = Column(DateTime(timezone=True), nullable=False)
    committed_closure_at = Column(DateTime(timezone=True), nullable=False)
    
    # Environmental / Contextual factors (Captured before session activation)
    admin_state_snapshot = Column(JSONB, nullable=True) # e.g., {"clarity": "high", "energy": "medium", "pressure": "low"}
    admin_awareness_tier = Column(String(50), nullable=False) # 'Naive', 'Ambient', 'Contaminated', 'Directed'
    purity_tier = Column(String(50), nullable=False) # 'Pure', 'Curated-Blind'
    social_field_coherence = Column(String(50), nullable=True) 
    
    # The 2x2 Stakes & Awareness Matrix
    real_money_at_stake = Column(Boolean, nullable=False, default=False) 
    asset_financial_awareness = Column(Boolean, nullable=True)
    
    # Retrocausal Variables
    t_delta = Column(Interval, nullable=True) 
    trng_source = Column(String(50), nullable=True)

class SessionEvent(Base):
    """
    The immutable provenance chain (#104). Records every touch: task generation, 
    dispatch, extraction receipt, sealing, outcome resolution, admin observation.
    """
    __tablename__ = 'session_event'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('session.id'), nullable=False)
    event_type = Column(String(50), nullable=False) # e.g., 'sealed', 'extracted', 'admin_observed'
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    agent_version = Column(String(50), nullable=True) # The exact LLM/Code version that took the action
    data_snapshot = Column(JSONB, nullable=True) # State of the data at the time of the event

class SessionFingerprint(Base):
    """
    Automated environmental snapshot joined to the asset's reported measurement time.
    """
    __tablename__ = 'session_fingerprint'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('session.id'), unique=True)
    
    # Astrophysical / Environmental Auto-Feeds
    local_sidereal_time = Column(Float, nullable=True)
    kp_index = Column(Float, nullable=True) # Geomagnetic
    solar_wind_speed = Column(Float, nullable=True)
    schumann_resonance_peaks = Column(JSONB, nullable=True)
    planetary_configuration = Column(JSONB, nullable=True) # Swiss Ephemeris data
    local_weather = Column(JSONB, nullable=True)

class EpistemologicalEpoch(Base):
    """
    Version-controls the interpretive framework (Brief: Epistemological epoch tracking).
    Allows retroactive reanalysis of the corpus under new hypotheses.
    """
    __tablename__ = 'epistemological_epoch'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(String(50), nullable=False, unique=True) # e.g., 'v1.0-baseline'
    description = Column(String, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
```

---

## Proposed Validation Schema (Pydantic Protocol)

When the worker daemon parses an incoming email from the asset, it extracts the exact numerical measurements. Because the asset might be blind to the specific parameter, the extraction simply looks for the numerical value associated with the instruction.

```python
class RadiesthesiaMeasurement(BaseModel):
    """
    The numerical measurements extracted from the asset's email report.
    Because the parameter schema is FLUID, this model is built dynamically at runtime.
    """
    measurements: Dict[str, float] = Field(
        ...,
        description="A dictionary mapping the requested parameter names (e.g., 'VAD', 'RVD', 'EBF') to their 0-100 percentage values."
    )
    
    # Asset-Reported Metadata (Extracted by LLM from free text/envelope)
    measurement_timestamp: Optional[datetime] = Field(
        None, description="The exact time the asset claims they performed the measurement."
    )
    asset_location: Optional[str] = Field(
        None, description="The physical location of the asset during the measurement."
    )
    sleep_quality: Optional[str] = Field(
        None, description="Asset's reported sleep quality."
    )
    psychological_state: Optional[str] = Field(
        None, description="Asset's reported psychological or somatic state."
    )
    motivation_state: Optional[str] = Field(
        None, description="Asset's self-assessed motivation or engagement level (Brief Addendum: Motivation-Psi Interaction)."
    )
    
    asset_notes: Optional[str] = Field(
        None, description="Any other free-text qualitative notes."
    )
```

## V1 Execution Constraint (Manual Execution)
Per the Product Brief Decision Log (D7), automated trade execution (IBKR integration) is explicitly OUT of scope for V1. The signal informs human decision, and execution remains manual. The `TargetInstance` thresholds still double as the strict parameters for the Bracket Order protocol, but the admin must manually enter these bracket orders at the broker.

## The Role of the LLM in Schema Fluidity
The entire reason we mandate LLM generation of tasking emails and extraction processing is to preserve this schema fluidity. 
When you define a new parameter in the database (e.g., `somatic_intensity`), you do not need to write new parsing code. 
1. **Tasking:** The LLM agent dynamically reads the `Parameter` registry and formulates the outgoing tasking email.
2. **Extraction:** The LLM extraction agent dynamically generates the Pydantic schema mapping expected parameters, instructing Ollama to extract the new variables from the unstructured email text automatically.

## The 2x2 Stakes Matrix (Psi Interference Study)
Because we axiomaticallly assume psi functioning is real, we must account for systemic psi interference. A market with billions of dollars on the line possesses a massive collective intent field. The act of the system placing *real* capital on a target might alter the asset's ability to measure it, purely due to the psychic "weight" of the capital, regardless of whether the asset consciously knows it. 
Therefore, the schema tracks a 2x2 matrix for every session:
1. `real_money_at_stake`: Was capital objectively risked?
2. `asset_financial_awareness`: Did the asset subjectively *believe* capital was risked?
This allows the analysis engine to isolate the "weight of objective capital" from "asset performance anxiety".

## User Review Required

Does this updated architecture accurately capture the separation of Affirmations and Parameters, the generation of the `XXXX/YYYY` coordinate, the tracking of the `protocol_type` (Double-Blind vs Front-Loaded), and the profound implications of the 2x2 Stakes Matrix?
