import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from quantforge.validation import StrategyValidationPlatform  # noqa: E402


def main() -> None:
    report = StrategyValidationPlatform().validate("QF-2026-00431")

    print("Strategy")
    print(report.strategy_id)
    print()
    print("Walk Forward")
    print(report.walk_forward.status.value)
    print()
    print("Monte Carlo")
    print(report.monte_carlo.status.value)
    print()
    print("Cross Pair")
    print(report.cross_pair.status.value)
    print()
    print("Stress")
    print(report.stress_test.status.value)
    print()
    print("Confidence")
    print(f"{int(report.confidence * 100)}%")
    print()
    print("Deployment")
    print(report.deployment_decision.value)


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
