# Data Model

## Durable Tables

Physical PostgreSQL tables are schema-qualified according to Chapter 6. For example, candles live in `market.candle`, instruments in `instrument.instrument`, plugins in `plugin.plugin`, experiments in `research.experiment`, research runs in `research.research_run`, and live orders in `trading.live_order`.

All business entities use UUID primary keys, UTC `timestamptz` timestamps, explicit foreign keys, audit columns, and `NUMERIC` for financial values.

### instruments

Stores tradable instruments such as `EUR_USD`, `GBP_JPY`, or `XAU_USD`.

Key fields:

- `id`
- `symbol`
- `display_name`
- `asset_class`
- `pip_location`
- `is_active`

### candles

Stores permanent raw OHLCV candles from OANDA.

Key fields:

- `instrument_id`
- `granularity`
- `time`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `complete`
- `source`
- `created_at`

Unique key:

- `instrument_id`, `granularity`, `time`

### plugins

Stores common plugin registry metadata for every plugin type.

Key fields:

- `plugin_key`
- `name`
- `version`
- `plugin_type`
- `status`
- `metadata_json`

Plugin types are data, not separate table families. Supported examples include:

- indicator
- feature
- market_regime
- entry_model
- confirmation
- exit_model
- risk_model
- position_sizing
- trade_management
- validation
- ranking

### plugin_parameters

Stores plugin parameters and search spaces.

Key fields:

- `plugin_id`
- `name`
- `value_type`
- `default_value_json`
- `search_space_json`

### plugin_type_configs

Stores type-specific plugin metadata and runtime configuration.

Key fields:

- `plugin_id`
- `config_schema_json`
- `runtime_config_json`

### plugin_dependencies

Stores plugin dependency rules without creating type-specific plugin tables.

Key fields:

- `plugin_id`
- `dependency_plugin_id`
- `dependency_key`
- `version_constraint`

### plugin_compatibility_rules

Stores compatibility constraints between plugin types or concrete plugins.

Key fields:

- `plugin_id`
- `compatible_plugin_type`
- `compatible_plugin_key`
- `rule_json`

### plugin_execution_results

Stores plugin execution output for research, validation, or live explainability when the output is worth persisting.

Key fields:

- `plugin_id`
- `experiment_id`
- `research_run_id`
- `strategy_version_id`
- `execution_context`
- `input_hash`
- `output_json`
- `metrics_json`

### experiments

Stores the primary research unit. Every dataset, feature set, strategy template, parameter search, validation result, analytics report, and published strategy should trace back to an experiment.

Key fields:

- `experiment_key`
- `research_project_id`
- `dataset_id`
- `strategy_template_id`
- `objective`
- `hypothesis`
- `priority`
- `run_mode`
- `random_seed`
- `software_version`
- `success_criteria_json`
- `validation_config_json`
- `ranking_config_json`
- `optimization_config_json`
- `analytics_json`
- `published_strategy_version_id`
- `status`

### datasets

Stores reproducible dataset definitions for experiments.

Key fields:

- `dataset_key`
- `instrument_id`
- `timeframe_id`
- `start_time`
- `end_time`
- `source_uri`
- `trading_sessions_json`
- `spread_model_json`
- `missing_data_policy`
- `quality_report_json`

### experiment_plugin_configs

Stores explicit plugin versions and roles for an experiment.

Key fields:

- `experiment_id`
- `plugin_id`
- `plugin_role`
- `config_json`

### experiment_schedules

Stores EMS scheduling metadata.

Key fields:

- `experiment_id`
- `run_mode`
- `priority`
- `scheduled_at`
- `max_parallel_workers`
- `worker_group`

### experiment_resource_usage

Stores CPU, memory, queue, worker, and estimated completion information so research workloads do not affect live trading.

Key fields:

- `experiment_id`
- `cpu_seconds`
- `peak_memory_mb`
- `queue_seconds`
- `worker_id`
- `resource_json`

### feature_sets

Stores the feature bundle used by an experiment.

Key fields:

- `experiment_id`
- `feature_set_key`
- `feature_vector_uri`
- `metadata_json`

### parameter_searches

Stores the search space and selected parameters for an experiment.

Key fields:

- `experiment_id`
- `optimizer`
- `objective`
- `search_space_json`
- `best_parameters_json`
- `metrics_json`

### research_runs

Stores each execution attempt inside an experiment.

Key fields:

- `id`
- `experiment_id`
- `instrument_id`
- `granularity`
- `start_time`
- `end_time`
- `parameters_json`
- `metrics_json`
- `status`

### candidate_results

Stores strategies that passed validation and may be promoted to live trading.

Key fields:

- `id`
- `experiment_id`
- `research_run_id`
- `strategy_version_id`
- `parameters_json`
- `score`
- `validation_status`
- `approved_for_live`

### strategy_templates

Stores template definitions assembled from plugin components.

Key fields:

- `template_key`
- `name`
- `component_graph_json`

### strategy_versions

Stores immutable strategy versions that can move through research, validation, approval, and deployment.

Key fields:

- `template_id`
- `version`
- `status`
- `parameters_json`
- `component_versions_json`
- `approved_at`

### backtest_runs

Stores historical simulation runs for a strategy version.

Key fields:

- `strategy_version_id`
- `instrument_id`
- `granularity`
- `start_time`
- `end_time`
- `cost_model_json`
- `metrics_json`
- `status`

### validation_runs

Stores walk-forward, out-of-sample, and robustness validation gates.

Key fields:

- `strategy_version_id`
- `validation_type`
- `status`
- `thresholds_json`
- `metrics_json`
- `reason`

### experiment_analytics

Stores experiment-level comparisons, feature importance, parameter robustness, overfitting risk, and conclusions.

Key fields:

- `experiment_id`
- `analytics_type`
- `summary`
- `metrics_json`
- `recommendations_json`

### experiment_results

Stores immutable experiment result summaries.

Key fields:

- `experiment_id`
- `strategies_generated`
- `strategies_rejected`
- `best_strategy_version_id`
- `validation_summary_json`
- `ranking_distribution_json`
- `feature_importance_json`
- `parameter_importance_json`
- `execution_seconds`
- `result_hash`

### experiment_comparisons

Stores experiment-to-experiment comparisons.

Key fields:

- `baseline_experiment_id`
- `comparison_name`
- `metric_set_json`
- `comparison_result_json`
- `conclusion`

### experiment_comparison_members

Stores the experiments included in a comparison.

Key fields:

- `comparison_id`
- `experiment_id`
- `role`
- `rank_order`
- `metrics_json`

### published_strategies

Links an experiment to the approved strategy version it produced.

Key fields:

- `experiment_id`
- `strategy_version_id`
- `publication_reason`
- `promotion_metrics_json`
- `approved_by`
- `approved_at`

### strategy_deployments

Stores approved strategy versions deployed to paper or live environments.

Key fields:

- `strategy_version_id`
- `environment`
- `status`
- `deployed_at`
- `stopped_at`

### live_signals

Stores live signal decisions before risk and execution.

Key fields:

- `strategy_deployment_id`
- `instrument_id`
- `signal_time`
- `side`
- `confidence`
- `payload_json`

### live_orders

Stores every live order request and broker response.

Key fields:

- `id`
- `strategy_candidate_id`
- `instrument_id`
- `side`
- `units`
- `order_type`
- `status`
- `oanda_order_id`
- `request_json`
- `response_json`
- `created_at`

### live_positions

Stores live position state.

Key fields:

- `strategy_deployment_id`
- `instrument_id`
- `side`
- `units`
- `average_price`
- `status`

### risk_rules

Stores configurable live trading constraints.

Key fields:

- `rule_key`
- `name`
- `enabled`
- `config_json`

### kill_switches

Stores platform-level emergency trade blocks.

Key fields:

- `switch_key`
- `enabled`
- `reason`

## Derived Data

Indicator values are derived data. Do not store every RSI, EMA, ATR, MACD, or custom feature value by default.

Allowed exceptions:

- final research metrics
- strategy candidate summaries
- audit snapshots needed to explain a live trade
- Parquet research caches that can be regenerated
