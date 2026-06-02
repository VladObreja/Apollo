import factory
from datetime import UTC, datetime

from apollo.db.models import CorpusRecord


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
