# Physical PostgreSQL Schema Standards

Source: `QuantForge AI - Chapter 6.pdf`.

Chapter 6 defines the physical PostgreSQL architecture standards. Detailed schema sections are expected in later Chapter 6 subsections, but these standards apply immediately.

## Database Architecture

QuantForge AI uses one PostgreSQL cluster with multiple schemas in Version 1:

- `market`
- `instrument`
- `plugin`
- `research`
- `strategy`
- `validation`
- `trading`
- `risk`
- `reporting`
- `admin`
- `infrastructure`

This gives one backup strategy, easier joins, simpler administration, lower operational complexity, and easier local development. Future versions may move schemas to dedicated databases.

## Ownership

- `market`: Data Service
- `instrument`: Data Service
- `plugin`: Strategy Service
- `research`: Research Service
- `strategy`: Strategy Service
- `validation`: Research Service
- `trading`: Trading Service
- `risk`: Risk Service
- `reporting`: Reporting Service
- `admin`: API Service
- `infrastructure`: API Service

Only the owning service may modify records in its schema.

## Required Extensions

- `pgcrypto` for UUID generation with `gen_random_uuid()`
- `pg_stat_statements` for performance monitoring
- `btree_gin` for advanced indexing
- `pg_trgm` for text search across plugins, strategies, and logs

## Standards

- Business entity primary keys use UUID.
- All relationships use explicit foreign keys.
- Foreign keys are indexed.
- Every table has `id`, `created_at`, `updated_at`, `created_by`, and `updated_by`.
- Business tables also include `version` and `status`.
- Soft-delete capable tables include `deleted_at` and `deleted_by`.
- All timestamps are UTC `timestamptz`.
- Financial values use `NUMERIC`, not floating point.
- Lookup tables are preferred over PostgreSQL enum types.
- JSONB is allowed for flexible metadata only.
- Large files are stored in filesystem/object storage, with metadata in PostgreSQL.

## Partitioning

Only very large tables are partitioned.

Initial candidates:

- `market.candle`
- `market.tick`
- `research.backtest_trade`
- `trading.execution`
- `infrastructure.log`

Partition by time.

## Retention

- Market data: permanent
- Strategies: permanent
- Trades: permanent
- Validation: permanent
- Research cache: configurable
- System logs: 365 days
- Audit logs: permanent

## Transactions And Concurrency

Business transactions use ACID transactions and roll back on failure.

Critical examples:

- Strategy approval
- Risk approval
- Order creation
- Trade execution

Optimistic locking applies to strategies, configurations, plugins, experiments, and research runs. Pessimistic locking is limited to live trade execution where necessary.

## Security And Backup

Sensitive columns are encrypted. Database roles follow least privilege.

Backup strategy:

- Full backups daily
- Incremental backups hourly
- WAL archiving enabled
- Point-in-time recovery enabled
