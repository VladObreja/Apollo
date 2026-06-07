import factory
from datetime import UTC, datetime
from uuid import uuid4

from apollo.db.models import (
    CorpusRecord,
    EnvFingerprint,
    QuarantineRecord,
    ValidationRecord,
)


class CorpusRecordFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = CorpusRecord
        sqlalchemy_session = None  # Reassigned dynamically in conftest/fixtures
        sqlalchemy_session_persistence = "commit"

    target_statement = factory.Faker("sentence")
    parameter_name = factory.Iterator(["VAD", "RVD", "EBF"])
    is_control_target = False
    admin_awareness_tier = "TIER_1"
    admin_psychological_context = factory.Faker("sentence")

    status = "pending"
    available_after = factory.LazyFunction(lambda: datetime.now(UTC))


class QuarantineRecordFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = QuarantineRecord
        sqlalchemy_session = None  # Reassigned dynamically in conftest/fixtures
        sqlalchemy_session_persistence = "commit"

    corpus_record_id = factory.LazyFunction(uuid4)
    raw_email_bytes = b"fake raw email bytes"
    quarantine_reason = "extraction_schema_error"
    error_detail = "Test extraction schema error"
    quarantined_at = factory.LazyFunction(lambda: datetime.now(UTC))


class EnvFingerprintFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = EnvFingerprint
        sqlalchemy_session = None  # Reassigned dynamically in conftest/fixtures
        sqlalchemy_session_persistence = "commit"

    corpus_record_id = factory.LazyFunction(
        uuid4
    )  # dangling UUID — consistent with QuarantineRecordFactory
    fingerprinted_at = factory.LazyFunction(lambda: datetime.now(UTC))
    retrieval_status = "ok"


class ValidationRecordFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = ValidationRecord
        sqlalchemy_session = None  # Reassigned dynamically in conftest/fixtures
        sqlalchemy_session_persistence = "commit"

    corpus_record_id = factory.LazyFunction(
        uuid4
    )  # dangling UUID — consistent with other factories
    validated_at = factory.LazyFunction(lambda: datetime.now(UTC))
    validation_status = "hit"
    param_value = 75.0
