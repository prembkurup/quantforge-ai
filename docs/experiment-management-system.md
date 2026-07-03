# Experiment Management System

Source: `QuantForge AI - Chapter 8.pdf`.

The Experiment Management System, or EMS, is the Research Service component responsible for planning, executing, monitoring, tracking, comparing, and reproducing quantitative trading research.

Every research activity inside QuantForge AI is an experiment. Strategies are outputs of experiments, not the primary object.

## Purpose

The EMS answers research questions that a strategy-first trading application usually loses:

- Which hypothesis is being tested?
- Which dataset was used?
- Which feature set was used?
- Which strategy template and plugins were used?
- Which parameter space was explored?
- Which validation methods were applied?
- Is the result reproducible?
- Is the result statistically significant?

## Lifecycle

Every experiment follows a standard lifecycle:

1. Draft
2. Configured
3. Queued
4. Running
5. Completed
6. Validated
7. Published
8. Archived

Failed experiments retain metadata and results. They are useful learning data and must not be discarded.

## Experiment Components

An experiment contains:

- objective
- hypothesis
- dataset
- feature set
- market regime
- strategy template
- plugin configuration
- parameter space
- optimization configuration
- validation configuration
- ranking configuration
- results

## Definitions

Each experiment records:

- name
- description
- owner
- objective
- instruments
- timeframes
- date range
- strategy templates
- plugin set
- feature set
- validation rules
- success criteria

Every experiment begins with a hypothesis. The hypothesis prevents random research and gives the experiment a clear testable purpose.

## Reproducibility

The EMS records the inputs needed to rerun an experiment:

- dataset version
- plugin versions
- feature set version
- parameter space
- optimization algorithm
- random seed
- software version

Running the same experiment again with the same inputs should produce equivalent results.

## Scheduling

Experiments may run:

- immediately
- scheduled
- sequentially
- in parallel

Priority levels:

- critical
- high
- normal
- low

The scheduler protects shared research resources and prevents offline research from affecting live trading.

## Results

Experiment results include:

- strategies generated
- strategies rejected
- validation summary
- best strategy
- ranking distribution
- feature importance
- parameter importance
- execution time
- resource usage

No result is overwritten.

## Comparison

Experiments can be compared by:

- net profit
- profit factor
- Sharpe ratio
- drawdown
- robustness
- trade count
- feature importance
- execution time

Comparison lets researchers identify the most effective hypotheses, templates, feature sets, plugins, and validation approaches over time.

## Analytics

The Analytics Engine provides:

- success rate by template
- success rate by market regime
- feature importance trends
- plugin performance
- optimization efficiency
- validation pass rate
- strategy publication rate

These analytics guide future research priorities.

## Publication

Only experiments that produce validated strategies can publish to the Strategy Repository.

Publication workflow:

1. Completed
2. Validation passed
3. Strategy ranked
4. Approved
5. Published

Publication is controlled and does not happen automatically.

## Principles

- Every research activity is an experiment.
- Every experiment starts with a hypothesis.
- Every experiment is reproducible.
- Every result is traceable.
- Failed experiments are valuable learning data.
- Strategies are outputs, not the primary object.
- Research quality is more important than research speed.
- Experiment metadata is never discarded.
