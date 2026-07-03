from quantforge.domain import StrategyLifecycleStatus


STRATEGY_LIFECYCLE: tuple[StrategyLifecycleStatus, ...] = (
    StrategyLifecycleStatus.DRAFT,
    StrategyLifecycleStatus.GENERATED,
    StrategyLifecycleStatus.OPTIMIZED,
    StrategyLifecycleStatus.BACKTESTED,
    StrategyLifecycleStatus.VALIDATED,
    StrategyLifecycleStatus.PAPER_TRADING,
    StrategyLifecycleStatus.APPROVED,
    StrategyLifecycleStatus.PRODUCTION,
    StrategyLifecycleStatus.RETIRED,
    StrategyLifecycleStatus.ARCHIVED,
)


def can_transition(current: StrategyLifecycleStatus, target: StrategyLifecycleStatus) -> bool:
    current_index = STRATEGY_LIFECYCLE.index(current)
    target_index = STRATEGY_LIFECYCLE.index(target)
    return target_index == current_index + 1

