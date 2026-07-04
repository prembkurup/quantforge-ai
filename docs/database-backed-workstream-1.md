# Database-Backed Workstream 1

This upgrade wires Workstream 1 into the real PostgreSQL/CoreUI OANDA candle database.

The previous Workstream 1 runner proves the institutional strategy-library workflow and target accounting. The database-backed runner starts executing real experiment batches from stored candle windows.

## Data Source

The runner uses CoreUI's read-only `oanda_candles` table through `CoreUiCandleRepository`.

The candle database remains the source of truth:

- pair
- timeframe
- candle time
- OHLC mid prices
- volume
- completeness flag

## Workflow

1. Select pairs, timeframes, and date range.
2. Count stored candles in the database.
3. Check duplicate candles.
4. Load real candle rows for gap analysis and experiment windows.
5. Slice candle rows into rolling research windows.
6. Execute strategy-template experiment batches on each window.
7. Produce database-backed candidate Strategy Assets.
8. Store reproducibility keys and audit events.
9. Report coverage, real batches, candidate assets, and recommendations.

Weekend and market-closed gaps are reported but do not automatically block research. Duplicate candles and underfilled windows do block the affected slice.

## Demo

```powershell
.\.venv\Scripts\python .\scripts\database_strategy_library.py --pairs EUR_USD --timeframes H1 --from 2025-01-01 --to 2025-02-01 --max-batches 25
```

The script requires `QUANTFORGE_COREUI_HISTORY_DATABASE_URL` to point at the CoreUI history database.

## Safety

This runner performs research only. It does not place live orders. Database-backed candidate assets should still flow through validation, certification, paper/shadow trading, and capital-stage controls before live deployment.
