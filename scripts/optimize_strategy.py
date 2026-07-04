import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from quantforge.research import OptimizationLaboratory  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Optimization Laboratory demo.")
    parser.add_argument("--strategy", default="Trend Pullback")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = OptimizationLaboratory().run(args.strategy)
    best = report.best_region

    print("Strategy")
    print(report.strategy_name)
    print()
    print("Parameters Tested")
    print(f"{report.parameters_tested:,}")
    print()
    print("Stable Regions")
    print(len(report.stable_regions))
    print()
    print("Recommended Regions")
    print(len(report.recommended_regions))
    print()
    print("Best Region")
    print("EMA Fast")
    print(_format_bounds(best.parameter_bounds["ema_fast"]))
    print()
    print("EMA Slow")
    print(_format_bounds(best.parameter_bounds["ema_slow"]))
    print()
    print("ATR")
    print(_format_bounds(best.parameter_bounds["atr_multiplier"]))
    print()
    print("Robustness")
    print(best.robustness.value.title())
    print()
    print("Research Review Board")
    print(report.review.decision.value)


def _format_bounds(bounds: tuple[float, float]) -> str:
    start, end = bounds
    return f"{start:g}-{end:g}"


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
