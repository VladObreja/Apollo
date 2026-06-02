from apollo.domain.compartments import Compartment, requires
from apollo.domain.models import TargetConfiguration
from apollo.db.session import get_session_factory
from apollo.db.models import CorpusRecord


class TargetService:
    @staticmethod
    @requires(Compartment.TARGET_WRITE)
    def create_target_configuration(config: TargetConfiguration) -> None:
        """
        Persist a target configuration to the database.

        Uses `Session.begin()` for automatic commit on success and
        rollback on any exception — no silent dirty-state leaks.
        """
        SessionFactory = get_session_factory()
        with SessionFactory.begin() as session:
            record = CorpusRecord(
                id=config.id,
                target_statement=config.target.statement,
                parameter_name=config.parameter.name,
                is_control_target=config.target_metadata.is_control_target,
                age_in_hours=config.target_metadata.age_in_hours,
                admin_awareness_tier=config.admin_state.awareness_tier,
                admin_psychological_context=config.admin_state.psychological_context,
                created_at=config.created_at,
            )
            session.add(record)
