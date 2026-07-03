CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS btree_gin;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE SCHEMA IF NOT EXISTS instrument;
CREATE SCHEMA IF NOT EXISTS market;
CREATE SCHEMA IF NOT EXISTS plugin;
CREATE SCHEMA IF NOT EXISTS research;
CREATE SCHEMA IF NOT EXISTS strategy;
CREATE SCHEMA IF NOT EXISTS validation;
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS risk;
CREATE SCHEMA IF NOT EXISTS reporting;
CREATE SCHEMA IF NOT EXISTS admin;
CREATE SCHEMA IF NOT EXISTS infrastructure;

CREATE TABLE IF NOT EXISTS instrument.instrument (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(32) NOT NULL,
    display_name VARCHAR(120),
    asset_class VARCHAR(40) NOT NULL DEFAULT 'forex',
    pip_location INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    CONSTRAINT uq_instrument_symbol UNIQUE (symbol)
);

CREATE TABLE IF NOT EXISTS instrument.timeframe (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(10) NOT NULL,
    seconds INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    CONSTRAINT uq_timeframe_code UNIQUE (code)
);

CREATE TABLE IF NOT EXISTS market.candle (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id UUID NOT NULL REFERENCES instrument.instrument(id),
    timeframe_id UUID NOT NULL REFERENCES instrument.timeframe(id),
    candle_time TIMESTAMPTZ NOT NULL,
    open_price NUMERIC(18, 8) NOT NULL,
    high_price NUMERIC(18, 8) NOT NULL,
    low_price NUMERIC(18, 8) NOT NULL,
    close_price NUMERIC(18, 8) NOT NULL,
    volume NUMERIC(20, 8) NOT NULL DEFAULT 0,
    is_complete BOOLEAN NOT NULL DEFAULT TRUE,
    source VARCHAR(40) NOT NULL DEFAULT 'oanda',
    quality_status VARCHAR(40) NOT NULL DEFAULT 'validated',
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    CONSTRAINT uq_candle_instrument_timeframe_time UNIQUE (instrument_id, timeframe_id, candle_time)
);

CREATE INDEX IF NOT EXISTS idx_candle_instrument_timeframe_time
    ON market.candle (instrument_id, timeframe_id, candle_time DESC);

CREATE TABLE IF NOT EXISTS market.spread (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id UUID NOT NULL REFERENCES instrument.instrument(id),
    spread_time TIMESTAMPTZ NOT NULL,
    bid_price NUMERIC(18, 8) NOT NULL,
    ask_price NUMERIC(18, 8) NOT NULL,
    source VARCHAR(40) NOT NULL DEFAULT 'oanda',
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    CONSTRAINT uq_spread_instrument_time_source UNIQUE (instrument_id, spread_time, source)
);

CREATE INDEX IF NOT EXISTS idx_spread_instrument_time
    ON market.spread (instrument_id, spread_time DESC);

CREATE TABLE IF NOT EXISTS market.market_calendar (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id UUID REFERENCES instrument.instrument(id),
    calendar_date DATE NOT NULL,
    session_status VARCHAR(40) NOT NULL,
    reason TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    CONSTRAINT uq_market_calendar_instrument_date UNIQUE (instrument_id, calendar_date)
);

CREATE TABLE IF NOT EXISTS market.data_import_job (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(40) NOT NULL DEFAULT 'oanda',
    instrument_id UUID REFERENCES instrument.instrument(id),
    timeframe_id UUID REFERENCES instrument.timeframe(id),
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    rows_imported INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE TABLE IF NOT EXISTS market.missing_data_record (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id UUID NOT NULL REFERENCES instrument.instrument(id),
    timeframe_id UUID NOT NULL REFERENCES instrument.timeframe(id),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS plugin.plugin (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_key VARCHAR(120) NOT NULL,
    name VARCHAR(160) NOT NULL,
    version_name VARCHAR(40) NOT NULL,
    plugin_type VARCHAR(60) NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'discovered',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    CONSTRAINT uq_plugin_key_version UNIQUE (plugin_key, version_name)
);

CREATE INDEX IF NOT EXISTS idx_plugin_type_status ON plugin.plugin (plugin_type, status);
CREATE INDEX IF NOT EXISTS idx_plugin_name_trgm ON plugin.plugin USING GIN (name gin_trgm_ops);

CREATE TABLE IF NOT EXISTS plugin.plugin_parameter (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_id UUID NOT NULL REFERENCES plugin.plugin(id),
    name VARCHAR(120) NOT NULL,
    value_type VARCHAR(40) NOT NULL,
    default_value_json JSONB,
    search_space_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    CONSTRAINT uq_plugin_parameter_name UNIQUE (plugin_id, name)
);

CREATE INDEX IF NOT EXISTS idx_plugin_parameter_plugin_id ON plugin.plugin_parameter (plugin_id);

CREATE TABLE IF NOT EXISTS plugin.plugin_type_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_id UUID NOT NULL REFERENCES plugin.plugin(id),
    config_schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    runtime_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    CONSTRAINT uq_plugin_type_config_plugin UNIQUE (plugin_id)
);

CREATE TABLE IF NOT EXISTS plugin.plugin_dependency (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_id UUID NOT NULL REFERENCES plugin.plugin(id),
    dependency_plugin_id UUID REFERENCES plugin.plugin(id),
    dependency_key VARCHAR(120),
    version_constraint VARCHAR(80),
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_plugin_dependency_plugin_id ON plugin.plugin_dependency (plugin_id);

CREATE TABLE IF NOT EXISTS plugin.plugin_compatibility_rule (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_id UUID NOT NULL REFERENCES plugin.plugin(id),
    compatible_plugin_type VARCHAR(60),
    compatible_plugin_key VARCHAR(120),
    rule_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE TABLE IF NOT EXISTS strategy.strategy_template (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_key VARCHAR(120) NOT NULL,
    name VARCHAR(160) NOT NULL,
    description TEXT,
    component_graph_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    CONSTRAINT uq_strategy_template_key UNIQUE (template_key)
);

CREATE INDEX IF NOT EXISTS idx_strategy_template_name_trgm
    ON strategy.strategy_template USING GIN (name gin_trgm_ops);

CREATE TABLE IF NOT EXISTS strategy.strategy (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID REFERENCES strategy.strategy_template(id),
    strategy_key VARCHAR(120) NOT NULL,
    name VARCHAR(160) NOT NULL,
    lifecycle_status VARCHAR(40) NOT NULL DEFAULT 'draft',
    storage_class VARCHAR(20) NOT NULL DEFAULT 'warm',
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    CONSTRAINT uq_strategy_key UNIQUE (strategy_key)
);

CREATE INDEX IF NOT EXISTS idx_strategy_template_id ON strategy.strategy (template_id);

CREATE TABLE IF NOT EXISTS strategy.strategy_version (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID REFERENCES strategy.strategy(id),
    version_name VARCHAR(40) NOT NULL,
    parameters_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    component_versions_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    ranking_score NUMERIC(8, 4),
    deployment_status VARCHAR(40) NOT NULL DEFAULT 'not_deployed',
    approved_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    CONSTRAINT uq_strategy_version UNIQUE (strategy_id, version_name)
);

CREATE INDEX IF NOT EXISTS idx_strategy_version_strategy_id ON strategy.strategy_version (strategy_id);

CREATE TABLE IF NOT EXISTS research.research_project (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(160) NOT NULL,
    objective TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    archived_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS research.dataset (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_key VARCHAR(120) NOT NULL,
    instrument_id UUID NOT NULL REFERENCES instrument.instrument(id),
    timeframe_id UUID NOT NULL REFERENCES instrument.timeframe(id),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    source_uri TEXT,
    trading_sessions_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    spread_model_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    missing_data_policy VARCHAR(80) NOT NULL DEFAULT 'reject_incomplete',
    quality_report_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    storage_class VARCHAR(20) NOT NULL DEFAULT 'warm',
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    CONSTRAINT uq_dataset_key_version UNIQUE (dataset_key, version)
);

CREATE INDEX IF NOT EXISTS idx_dataset_instrument_timeframe ON research.dataset (instrument_id, timeframe_id);

CREATE TABLE IF NOT EXISTS research.experiment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_key VARCHAR(120) NOT NULL,
    research_project_id UUID REFERENCES research.research_project(id),
    dataset_id UUID REFERENCES research.dataset(id),
    strategy_template_id UUID REFERENCES strategy.strategy_template(id),
    name VARCHAR(160) NOT NULL,
    description TEXT,
    objective TEXT,
    hypothesis TEXT,
    market_regime VARCHAR(80),
    success_criteria_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    parameters_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    validation_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    ranking_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    optimization_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    analytics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    published_strategy_version_id UUID REFERENCES strategy.strategy_version(id),
    priority VARCHAR(20) NOT NULL DEFAULT 'normal',
    run_mode VARCHAR(30) NOT NULL DEFAULT 'immediate',
    random_seed INTEGER,
    software_version VARCHAR(80),
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    queued_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ,
    CONSTRAINT uq_experiment_key_version UNIQUE (experiment_key, version)
);

CREATE INDEX IF NOT EXISTS idx_experiment_project_id ON research.experiment (research_project_id);
CREATE INDEX IF NOT EXISTS idx_experiment_dataset_id ON research.experiment (dataset_id);
CREATE INDEX IF NOT EXISTS idx_experiment_template_id ON research.experiment (strategy_template_id);
CREATE INDEX IF NOT EXISTS idx_experiment_status_priority ON research.experiment (status, priority);

CREATE TABLE IF NOT EXISTS research.hypothesis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hypothesis_key VARCHAR(160) NOT NULL,
    statement TEXT NOT NULL,
    supported_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    confidence NUMERIC(8, 4) NOT NULL DEFAULT 0,
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'proposed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_hypothesis_key_version UNIQUE (hypothesis_key, version)
);

CREATE TABLE IF NOT EXISTS research.knowledge_record (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    object_type VARCHAR(40) NOT NULL,
    object_key VARCHAR(180) NOT NULL,
    outcome VARCHAR(40) NOT NULL,
    experiment_key VARCHAR(160) NOT NULL,
    hypothesis_key VARCHAR(160),
    instrument VARCHAR(32),
    timeframe VARCHAR(20),
    market_regime VARCHAR(80),
    session VARCHAR(80),
    metric_name VARCHAR(80) NOT NULL DEFAULT 'success_rate',
    metric_value NUMERIC(12, 6),
    stability NUMERIC(8, 4),
    importance NUMERIC(8, 4),
    sample_size INTEGER NOT NULL DEFAULT 1,
    lessons_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    context_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_record_object ON research.knowledge_record (object_type, object_key);
CREATE INDEX IF NOT EXISTS idx_knowledge_record_context ON research.knowledge_record (instrument, timeframe, market_regime, session);

CREATE TABLE IF NOT EXISTS research.knowledge_score (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    object_type VARCHAR(40) NOT NULL,
    object_key VARCHAR(180) NOT NULL,
    success_rate NUMERIC(8, 4) NOT NULL,
    stability NUMERIC(8, 4) NOT NULL,
    evidence_count INTEGER NOT NULL,
    score NUMERIC(8, 4) NOT NULL,
    recommendation VARCHAR(20) NOT NULL,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version INTEGER NOT NULL DEFAULT 1,
    CONSTRAINT uq_knowledge_score_object_version UNIQUE (object_type, object_key, version)
);

CREATE TABLE IF NOT EXISTS research.knowledge_recommendation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_key VARCHAR(180) NOT NULL,
    recommendation_type VARCHAR(60) NOT NULL,
    recommendation_text TEXT NOT NULL,
    source_object_type VARCHAR(40),
    source_object_key VARCHAR(180),
    confidence NUMERIC(8, 4) NOT NULL DEFAULT 0,
    status VARCHAR(40) NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    CONSTRAINT uq_knowledge_recommendation_key UNIQUE (recommendation_key)
);

CREATE TABLE IF NOT EXISTS research.experiment_plugin_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES research.experiment(id),
    plugin_id UUID NOT NULL REFERENCES plugin.plugin(id),
    plugin_role VARCHAR(60) NOT NULL,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    CONSTRAINT uq_experiment_plugin_config_role UNIQUE (experiment_id, plugin_id, plugin_role)
);

CREATE INDEX IF NOT EXISTS idx_experiment_plugin_config_experiment_id ON research.experiment_plugin_config (experiment_id);

CREATE TABLE IF NOT EXISTS research.experiment_schedule (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES research.experiment(id),
    run_mode VARCHAR(30) NOT NULL DEFAULT 'immediate',
    priority VARCHAR(20) NOT NULL DEFAULT 'normal',
    scheduled_at TIMESTAMPTZ,
    max_parallel_workers INTEGER NOT NULL DEFAULT 1,
    queue_position INTEGER,
    worker_group VARCHAR(80),
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_experiment_schedule_status_priority ON research.experiment_schedule (status, priority, scheduled_at);

CREATE TABLE IF NOT EXISTS research.experiment_resource_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES research.experiment(id),
    cpu_seconds NUMERIC(18, 4),
    peak_memory_mb NUMERIC(18, 4),
    queue_seconds NUMERIC(18, 4),
    worker_id VARCHAR(120),
    estimated_completion_at TIMESTAMPTZ,
    resource_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'recorded',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_experiment_resource_usage_experiment_id ON research.experiment_resource_usage (experiment_id);

CREATE TABLE IF NOT EXISTS research.research_run (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES research.experiment(id),
    research_project_id UUID REFERENCES research.research_project(id),
    instrument_id UUID NOT NULL REFERENCES instrument.instrument(id),
    timeframe_id UUID NOT NULL REFERENCES instrument.timeframe(id),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    parameters_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    storage_class VARCHAR(20) NOT NULL DEFAULT 'warm',
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_research_run_experiment_id ON research.research_run (experiment_id);
CREATE INDEX IF NOT EXISTS idx_research_run_project_id ON research.research_run (research_project_id);
CREATE INDEX IF NOT EXISTS idx_research_run_instrument_timeframe ON research.research_run (instrument_id, timeframe_id);

CREATE TABLE IF NOT EXISTS research.feature_definition (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_key VARCHAR(120) NOT NULL,
    name VARCHAR(160) NOT NULL,
    definition_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    CONSTRAINT uq_feature_definition_key_version UNIQUE (feature_key, version)
);

CREATE TABLE IF NOT EXISTS research.feature_set (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES research.experiment(id),
    research_run_id UUID REFERENCES research.research_run(id),
    feature_set_key VARCHAR(120) NOT NULL,
    feature_vector_uri TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_feature_set_experiment_id ON research.feature_set (experiment_id);

CREATE TABLE IF NOT EXISTS research.optimization_run (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES research.experiment(id),
    optimizer VARCHAR(80) NOT NULL,
    objective VARCHAR(120),
    search_space_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    best_parameters_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_optimization_run_experiment_id ON research.optimization_run (experiment_id);

CREATE TABLE IF NOT EXISTS research.parameter_search (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES research.experiment(id),
    optimizer VARCHAR(80) NOT NULL,
    objective VARCHAR(120) NOT NULL,
    search_space_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    constraints_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    best_parameters_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_parameter_search_experiment_id ON research.parameter_search (experiment_id);

CREATE TABLE IF NOT EXISTS research.backtest_run (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_version_id UUID REFERENCES strategy.strategy_version(id),
    experiment_id UUID REFERENCES research.experiment(id),
    instrument_id UUID NOT NULL REFERENCES instrument.instrument(id),
    timeframe_id UUID NOT NULL REFERENCES instrument.timeframe(id),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    cost_model_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_backtest_run_strategy_version_id ON research.backtest_run (strategy_version_id);
CREATE INDEX IF NOT EXISTS idx_backtest_run_experiment_id ON research.backtest_run (experiment_id);
CREATE INDEX IF NOT EXISTS idx_backtest_run_instrument_timeframe ON research.backtest_run (instrument_id, timeframe_id);

CREATE TABLE IF NOT EXISTS research.backtest_trade (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backtest_run_id UUID NOT NULL REFERENCES research.backtest_run(id),
    side VARCHAR(10) NOT NULL,
    entry_time TIMESTAMPTZ NOT NULL,
    exit_time TIMESTAMPTZ,
    entry_price NUMERIC(18, 8) NOT NULL,
    exit_price NUMERIC(18, 8),
    units NUMERIC(18, 4) NOT NULL,
    pnl NUMERIC(20, 8),
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'closed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_backtest_trade_run_entry_time ON research.backtest_trade (backtest_run_id, entry_time);

CREATE TABLE IF NOT EXISTS validation.validation_run (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES research.experiment(id),
    strategy_version_id UUID REFERENCES strategy.strategy_version(id),
    validation_type VARCHAR(60) NOT NULL,
    thresholds_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    reason TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_validation_run_experiment_id ON validation.validation_run (experiment_id);
CREATE INDEX IF NOT EXISTS idx_validation_run_strategy_version_id ON validation.validation_run (strategy_version_id);

CREATE TABLE IF NOT EXISTS research.experiment_validation_result (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES research.experiment(id),
    validation_run_id UUID REFERENCES validation.validation_run(id),
    validation_type VARCHAR(60) NOT NULL,
    passed BOOLEAN NOT NULL DEFAULT FALSE,
    metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    reason TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'complete',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_experiment_validation_result_experiment_id ON research.experiment_validation_result (experiment_id);

CREATE TABLE IF NOT EXISTS research.experiment_result (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES research.experiment(id),
    strategies_generated INTEGER NOT NULL DEFAULT 0,
    strategies_rejected INTEGER NOT NULL DEFAULT 0,
    best_strategy_version_id UUID REFERENCES strategy.strategy_version(id),
    validation_summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    ranking_distribution_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    feature_importance_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    parameter_importance_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    execution_seconds NUMERIC(18, 4),
    result_hash VARCHAR(128),
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'complete',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_experiment_result_experiment_id ON research.experiment_result (experiment_id);

CREATE TABLE IF NOT EXISTS research.experiment_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES research.experiment(id),
    analytics_type VARCHAR(80) NOT NULL,
    summary TEXT,
    metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    recommendations_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'complete',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_experiment_analytics_experiment_id ON research.experiment_analytics (experiment_id);

CREATE TABLE IF NOT EXISTS research.experiment_comparison (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    baseline_experiment_id UUID REFERENCES research.experiment(id),
    comparison_name VARCHAR(160) NOT NULL,
    metric_set_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    comparison_result_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    conclusion TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'complete',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE TABLE IF NOT EXISTS research.experiment_comparison_member (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comparison_id UUID NOT NULL REFERENCES research.experiment_comparison(id),
    experiment_id UUID NOT NULL REFERENCES research.experiment(id),
    role VARCHAR(40) NOT NULL DEFAULT 'candidate',
    rank_order INTEGER,
    metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    CONSTRAINT uq_experiment_comparison_member UNIQUE (comparison_id, experiment_id)
);

CREATE INDEX IF NOT EXISTS idx_experiment_comparison_member_experiment_id ON research.experiment_comparison_member (experiment_id);

CREATE TABLE IF NOT EXISTS research.candidate_result (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES research.experiment(id),
    research_run_id UUID REFERENCES research.research_run(id),
    strategy_version_id UUID REFERENCES strategy.strategy_version(id),
    score NUMERIC(8, 4),
    validation_status VARCHAR(40) NOT NULL DEFAULT 'pending',
    approved_for_live BOOLEAN NOT NULL DEFAULT FALSE,
    parameters_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'candidate',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_candidate_result_experiment_id ON research.candidate_result (experiment_id);

CREATE TABLE IF NOT EXISTS research.published_strategy (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES research.experiment(id),
    strategy_version_id UUID NOT NULL REFERENCES strategy.strategy_version(id),
    publication_reason TEXT,
    promotion_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'published',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    CONSTRAINT uq_published_strategy_experiment_version UNIQUE (experiment_id, strategy_version_id)
);

CREATE INDEX IF NOT EXISTS idx_published_strategy_experiment_id ON research.published_strategy (experiment_id);
CREATE INDEX IF NOT EXISTS idx_published_strategy_strategy_version_id ON research.published_strategy (strategy_version_id);

CREATE TABLE IF NOT EXISTS plugin.plugin_execution_result (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_id UUID NOT NULL REFERENCES plugin.plugin(id),
    experiment_id UUID REFERENCES research.experiment(id),
    research_run_id UUID REFERENCES research.research_run(id),
    strategy_version_id UUID REFERENCES strategy.strategy_version(id),
    execution_context VARCHAR(40) NOT NULL,
    input_hash VARCHAR(128),
    output_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'complete',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_plugin_execution_result_experiment_id ON plugin.plugin_execution_result (experiment_id);
CREATE INDEX IF NOT EXISTS idx_plugin_execution_result_research_run_id ON plugin.plugin_execution_result (research_run_id);

CREATE TABLE IF NOT EXISTS strategy.strategy_deployment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_version_id UUID NOT NULL REFERENCES strategy.strategy_version(id),
    environment VARCHAR(40) NOT NULL DEFAULT 'paper',
    deployed_at TIMESTAMPTZ,
    stopped_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'inactive',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_strategy_deployment_version_id ON strategy.strategy_deployment (strategy_version_id);

CREATE TABLE IF NOT EXISTS trading.signal (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_deployment_id UUID REFERENCES strategy.strategy_deployment(id),
    instrument_id UUID NOT NULL REFERENCES instrument.instrument(id),
    signal_time TIMESTAMPTZ NOT NULL,
    side VARCHAR(10),
    confidence NUMERIC(8, 4),
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'created',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_signal_instrument_time ON trading.signal (instrument_id, signal_time DESC);

CREATE TABLE IF NOT EXISTS trading.live_order (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_deployment_id UUID REFERENCES strategy.strategy_deployment(id),
    signal_id UUID REFERENCES trading.signal(id),
    instrument_id UUID NOT NULL REFERENCES instrument.instrument(id),
    side VARCHAR(10) NOT NULL,
    units NUMERIC(18, 4) NOT NULL,
    order_type VARCHAR(40) NOT NULL,
    oanda_order_id VARCHAR(80),
    request_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    response_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'created',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_live_order_signal_id ON trading.live_order (signal_id);
CREATE INDEX IF NOT EXISTS idx_live_order_instrument_created ON trading.live_order (instrument_id, created_at DESC);

CREATE TABLE IF NOT EXISTS trading.execution (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES trading.live_order(id),
    oanda_transaction_id VARCHAR(80),
    execution_time TIMESTAMPTZ NOT NULL,
    price NUMERIC(18, 8) NOT NULL,
    units NUMERIC(18, 4) NOT NULL,
    response_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'filled',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_execution_order_time ON trading.execution (order_id, execution_time DESC);

CREATE TABLE IF NOT EXISTS trading.position (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_deployment_id UUID REFERENCES strategy.strategy_deployment(id),
    instrument_id UUID NOT NULL REFERENCES instrument.instrument(id),
    side VARCHAR(10) NOT NULL,
    units NUMERIC(18, 4) NOT NULL,
    average_price NUMERIC(18, 8),
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_position_deployment_status ON trading.position (strategy_deployment_id, status);

CREATE TABLE IF NOT EXISTS trading.trade (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    position_id UUID REFERENCES trading.position(id),
    instrument_id UUID NOT NULL REFERENCES instrument.instrument(id),
    side VARCHAR(10) NOT NULL,
    opened_at TIMESTAMPTZ NOT NULL,
    closed_at TIMESTAMPTZ,
    entry_price NUMERIC(18, 8),
    exit_price NUMERIC(18, 8),
    units NUMERIC(18, 4) NOT NULL,
    realized_pnl NUMERIC(20, 8),
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_trade_instrument_opened ON trading.trade (instrument_id, opened_at DESC);

CREATE TABLE IF NOT EXISTS risk.risk_rule (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_key VARCHAR(120) NOT NULL,
    name VARCHAR(160) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    CONSTRAINT uq_risk_rule_key UNIQUE (rule_key)
);

CREATE TABLE IF NOT EXISTS risk.risk_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_key VARCHAR(120) NOT NULL,
    version_name VARCHAR(40) NOT NULL,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    CONSTRAINT uq_risk_profile_key_version UNIQUE (profile_key, version_name)
);

CREATE TABLE IF NOT EXISTS risk.kill_switch (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    switch_key VARCHAR(120) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    reason TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'inactive',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    CONSTRAINT uq_kill_switch_key UNIQUE (switch_key)
);

CREATE TABLE IF NOT EXISTS reporting.report (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_key VARCHAR(120) NOT NULL,
    report_type VARCHAR(80) NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    artifact_uri TEXT,
    storage_class VARCHAR(20) NOT NULL DEFAULT 'warm',
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'created',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_report_type_created ON reporting.report (report_type, created_at DESC);

CREATE TABLE IF NOT EXISTS admin.system_configuration (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key VARCHAR(120) NOT NULL,
    version_name VARCHAR(40) NOT NULL,
    value_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    CONSTRAINT uq_system_configuration_key_version UNIQUE (config_key, version_name)
);

CREATE TABLE IF NOT EXISTS admin.audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor UUID,
    action VARCHAR(120) NOT NULL,
    entity_type VARCHAR(120),
    entity_id UUID,
    details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'recorded',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON admin.audit_log (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON admin.audit_log (created_at DESC);

CREATE TABLE IF NOT EXISTS infrastructure.service_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name VARCHAR(120) NOT NULL,
    log_level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'recorded',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_service_log_service_created
    ON infrastructure.service_log (service_name, created_at DESC);
