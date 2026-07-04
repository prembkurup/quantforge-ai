import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from quantforge.backtesting import BacktestEngine  # noqa: E402


def main() -> None:
    report = BacktestEngine().run().report
    if report is None:
        raise RuntimeError("Backtest report was not produced.")

    print("Strategy")
    print(report.strategy_name)
    print()
    print("Trades")
    print(f"{report.metrics.trades:,}")
    print()
    print("Profit Factor")
    print(f"{report.metrics.profit_factor:.2f}")
    print()
    print("Max DD")
    print(f"{report.metrics.max_drawdown * 100:.1f}%")
    print()
    print("Sharpe")
    print(f"{report.metrics.sharpe:.2f}")
    print()
    print("Validation Ready")
    print("YES" if report.validation_ready else "NO")


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
