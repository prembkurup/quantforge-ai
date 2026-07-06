from __future__ import annotations

import argparse
from datetime import UTC, datetime

from quantforge.live import (
    DailyLearningLoop,
    DailyOperationsDashboardBuilder,
    DailyReportGenerator,
    DailyRiskState,
    IntradayMetricsCalculator,
    SessionPortfolioManager,
    default_intraday_profile,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the QuantForge AI Version 2 intraday daily operations snapshot.")
    parser.add_argument("--timestamp", help="UTC timestamp, for example 2026-07-06T12:30:00Z. Defaults to now.")
    parser.add_argument("--todays-pl", type=float, default=420.50)
    parser.add_argument("--open-positions", type=int, default=1)
    parser.add_argument("--trades-today", type=int, default=4)
    parser.add_argument("--realized-daily-loss", type=float, default=0.004)
    parser.add_argument("--daily-drawdown", type=float, default=0.006)
    parser.add_argument("--risk-paused", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    timestamp = _parse_timestamp(args.timestamp) if args.timestamp else datetime.now(UTC)
    profile = default_intraday_profile()
    portfolios = SessionPortfolioManager().build({"QF-INTRADAY-DEMO": profile})
    risk_state = DailyRiskState(
        realized_daily_loss=args.realized_daily_loss,
        current_daily_drawdown=args.daily_drawdown,
        trades_today=args.trades_today,
        daily_exposure=0.18,
        strategy_allocation=0.12,
        currency_exposure=0.16,
    )
    snapshot = DailyOperationsDashboardBuilder().snapshot(
        profile,
        risk_state,
        portfolios,
        timestamp,
        todays_pl=args.todays_pl,
        open_positions=args.open_positions,
        risk_paused=args.risk_paused,
    )
    metrics = IntradayMetricsCalculator().calculate(
        (
            {"profit": args.todays_pl, "trades": args.trades_today, "average_trade_duration_minutes": 64, "drawdown": args.daily_drawdown, "trading_hours": 5.5},
            {"profit": 185.25, "trades": 3, "average_trade_duration_minutes": 58, "drawdown": 0.004, "trading_hours": 4.0},
            {"profit": -95.10, "trades": 2, "average_trade_duration_minutes": 72, "drawdown": 0.012, "trading_hours": 3.5},
        ),
        daily_signals=(9, 7, 5),
        daily_executions=(args.trades_today, 3, 2),
        daily_exposure=(0.18, 0.14, 0.11),
        daily_slippage=(0.2, 0.1, 0.3),
    )
    report = DailyReportGenerator().generate(snapshot, metrics)
    learning = DailyLearningLoop().update_priorities(report)

    print("QuantForge AI Version 2.0")
    print("Intraday Daily Operations")
    print()
    print("Current Session")
    print(snapshot.current_session.value)
    print()
    print("Trading Status")
    print(snapshot.trading_status.value)
    print()
    print("Today's P/L")
    print(snapshot.todays_pl)
    print()
    print("Today's Trades")
    print(snapshot.todays_trades)
    print()
    print("Open Positions")
    print(snapshot.open_positions)
    print()
    print("Remaining Daily Risk")
    print(snapshot.remaining_daily_risk)
    print()
    print("Daily Drawdown")
    print(snapshot.daily_drawdown)
    print()
    print("Session Portfolio")
    print(snapshot.session_portfolio)
    print()
    print("Active Strategies")
    print(", ".join(snapshot.active_strategies) if snapshot.active_strategies else "NONE")
    print()
    print("Daily Metrics")
    print(f"Average Daily Profit: {metrics.performance.average_daily_profit}")
    print(f"Winning Days: {metrics.performance.winning_days}")
    print(f"Losing Days: {metrics.performance.losing_days}")
    print(f"Average Trades Per Day: {metrics.performance.average_trades_per_day}")
    print(f"Average Trade Duration: {metrics.performance.average_trade_duration_minutes} minutes")
    print(f"Profit Per Trading Hour: {metrics.performance.profit_per_trading_hour}")
    print(f"Daily Expectancy: {metrics.performance.daily_expectancy}")
    print(f"Maximum Daily Drawdown: {metrics.risk.maximum_daily_drawdown}")
    print(f"Daily Risk Utilization: {metrics.risk.daily_risk_utilization}")
    print(f"Average Daily Signals: {metrics.operational.average_daily_signals}")
    print(f"Average Daily Executions: {metrics.operational.average_daily_executions}")
    print(f"Average Daily Exposure: {metrics.operational.average_daily_exposure}")
    print(f"Average Daily Slippage: {metrics.operational.average_daily_slippage}")
    print()
    print("Daily Report")
    print(report.report_id)
    print()
    print("Knowledge Updates")
    print(", ".join(report.knowledge_updates))
    print()
    print("Improvement Recommendations")
    print("; ".join(report.improvement_recommendations))
    print()
    print("Research Priorities")
    print("; ".join(learning["research_priorities"]))
    print()
    print("Future Campaigns")
    print(", ".join(learning["future_campaigns"]))


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
