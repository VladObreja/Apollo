"""Target configuration service.

Handles persistence of admin-configured targets. This is the sole
authorised write path for corpus_record identity columns.
"""

from datetime import timedelta

from apollo.db.models import CorpusRecord
from apollo.db.session import get_session_factory
from apollo.domain.compartments import Compartment, requires
from apollo.domain.models import TargetConfiguration


class TargetService:
    @staticmethod
    @requires(Compartment.TARGET_WRITE)
    def create_target_configuration(config: TargetConfiguration) -> None:
        """Persist a target configuration to the database.

        Uses ``Session.begin()`` for automatic commit on success and
        rollback on any exception — no silent dirty-state leaks.

        Sets ``available_after`` from ``age_in_hours`` to enforce the
        Age-In protocol: the worker daemon will not pick up the target
        until the configured delay has elapsed.
        """
        # Calculate Age-In gate: NOW + age_in_hours (default 0 = immediately available)
        available_after = config.created_at + timedelta(
            hours=config.target_metadata.age_in_hours or 0
        )

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
                available_after=available_after,
                real_money_at_stake=config.real_money_at_stake,
                asset_financial_awareness=config.asset_financial_awareness,
                ticker=config.ticker,
                expiry_at=config.expiry_at,
                threshold_pct=config.threshold_pct,
                threshold_direction=config.threshold_direction,
                # status defaults to 'pending' via server_default and ORM default
            )
            session.add(record)
