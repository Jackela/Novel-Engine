# Codex: Evaluation & A/B Testing (EVALUATION.md)
*Document Version: 1.2*
*Last Updated: 2025-08-11*

This document defines the evaluation framework, metrics, and reporting standards for the Novel Engine.

## 1. Evaluation Objectives

The primary goal of our evaluation framework is to provide a quantitative, reproducible, and automated way to measure the quality and performance of the Engine. This enables data-driven improvements and prevents regressions.

## 2. Metric Definitions

The following metrics are calculated by the evaluation pipeline.

### 2.1 Quality Metrics
-   **Success Rate:**
    -   **Definition:** The percentage of seed scenarios that run to completion without critical errors.
    -   **Calculation:** `(Completed Runs / Total Runs) * 100`.
-   **Canon Consistency Score:**
    -   **Definition:** Measures how well agent actions align with the established canon and doctrine provided in their `TurnBrief`.
    -   **Calculation:** For each `CharacterAction`, an NLI (Natural Language Inference) model compares the `justification` field against the `doctrine_snippets`. The score is the percentage of actions that are not classified as a "contradiction".
-   **Persona Consistency Score:**
    -   **Definition:** Measures how well an agent's actions align with its core beliefs.
    -   **Calculation:** The `justification` text is encoded into a sentence vector. This is compared against the weighted average vector of the agent's `beliefs` from its `PersonaCardV2` using cosine similarity. The final score is the average similarity across all actions in a run.
-   **Story Coherence Score:**
    -   **Definition:** Measures the logical flow between narrative paragraphs.
    -   **Calculation:** An NLI model checks for "entailment" between consecutive paragraphs in the generated `ChronicleSpec`. The score is the percentage of paragraph pairs that meet the entailment threshold.

### 2.2 Performance & Cost Metrics
-   **Turn Latency (ms):**
    -   **Definition:** The wall-clock time to execute a single turn.
    -   **Calculation:** Measured for each turn. Reported as Average, P95 (95th percentile), and Max.
-   **Token Cost per Turn:**
    -   **Definition:** The number of tokens processed by the LLM for a single turn.
    -   **Calculation:** `prompt_tokens + completion_tokens`. Reported as Average and Total per run.

## 3. Evaluation Data: Seed Scenarios

-   **Location:** `evaluation/seeds/`
-   **Format:** YAML files defining the initial `WorldState` and the `PersonaCardV2`s for the participating agents.
-   **Quantity:** A minimum of 10 seed scenarios must be maintained to form the baseline evaluation set.
-   **Reproducibility:** Each seed must use a fixed random seed to ensure deterministic behavior where applicable.

## 4. Evaluation Pipelines

### 4.1 `evaluate_baseline.py`
-   **Input:** The directory containing seed scenarios (`evaluation/seeds/`).
-   **Process:** Executes all seed scenarios against the current version of the Engine. Calculates all defined metrics for each run. Aggregates the results.
-   **Output:** A single Markdown file: `reports/baseline_report_{timestamp}.md`.

### 4.2 `evaluate_ab.py`
-   **Input:** Two configuration files (`--configA`, `--configB`).
-   **Process:** Runs all seed scenarios twice, once for each configuration.
-   **Output:** A comparative report detailing the percentage change in each metric between A and B, including statistical significance where applicable.

## 5. Report Format

The `baseline_report.md` must contain the following sections:
1.  **Run Summary:** Timestamp, Code Version/Commit Hash, Total Runs, Success Rate.
2.  **Aggregated Quality Metrics:** A table showing the average score for Canon Consistency, Persona Consistency, and Story Coherence across all successful runs.
3.  **Aggregated Performance Metrics:** A table showing the Avg/P95/Max Latency and Avg/Total Token Cost.
4.  **Per-Scenario Breakdown:** A detailed table showing all metrics for each individual seed scenario.

## 6. Archiving

-   **Run ID:** Every simulation run, whether for evaluation or production, is assigned a unique `run_id`.
-   **Log Location:** All detailed logs, including replay data and metric calculations, are stored in `runs/{run_id}/`.
-   **Retention:** Evaluation reports and run logs are archived for historical comparison.
