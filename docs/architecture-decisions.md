# Architecture Decisions

## AD-003: Plugin Registry With Type-Specific Metadata

Status: Approved

QuantForge AI will use a single plugin registry instead of separate tables for each plugin type.

The `plugins` table stores common plugin identity and lifecycle data:

- plugin key
- name
- version
- plugin type
- status
- common metadata

Companion tables store plugin-specific details:

- `plugin_parameters`
- `plugin_type_configs`
- `plugin_dependencies`
- `plugin_compatibility_rules`
- `plugin_execution_results`

This avoids duplicated schemas for entry, exit, risk, confirmation, market regime, and future plugin types. It also keeps versioning consistent and lets new plugin types be added through metadata rather than database redesign.

This decision supports the template-based, plugin-driven strategy architecture from the approved architecture updates and Chapter 4 domain model.

## AD-004: Experiment-Centric Research Model

Status: Approved

QuantForge AI will organize research around experiments instead of indicators or isolated strategy runs.

An `Experiment` is the primary unit of research work. It connects:

- experiment definition
- dataset
- feature set
- strategy template
- parameter search
- optimization and backtest runs
- validation results
- analytics
- published strategy versions

Indicators remain derived inputs, not the organizing center of the platform. A research run is an execution record within an experiment, while the experiment is the durable object used for traceability, reproducibility, comparison, and publishing.

This makes QuantForge AI behave like a scientific research system. Each published strategy can be traced back to the exact experiment, data window, feature set, template, plugin versions, parameter search, validation gates, and analytics that produced it.
