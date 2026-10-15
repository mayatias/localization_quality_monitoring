# Vehicle Location Quality Monitor

A small pipeline for generating synthetic vehicle-location recordings, detecting data-quality anomalies, evaluating detections against ground truth, and storing results in DuckDB and Parquet.

## Requirements

- Python 3.10 or newer
- DuckDB (installed with the project)
- For the dashboard: Streamlit, Plotly, and pandas (install the `dashboard` extra)

## Install

From the project root, install the command-line application:

```powershell
python -m pip install -e .
```

To use the Streamlit dashboard as well:

```powershell
python -m pip install -e ".[dashboard]"
```

## Generate sample data

Generate the default 30 recordings with seed 42:

```powershell
vl-quality generate
```

This writes recordings to `data/raw/` and the corresponding ground-truth JSON files to `data/ground_truth/`. You can choose a count, seed, and output directories:

```powershell
vl-quality generate --count 30 --seed 42 --raw data/raw --truth data/ground_truth
```

The generator covers seven driving scenarios and injects data faults into selected recordings. Reusing the same count and seed produces the same dataset.

## Process recordings

Run anomaly detection, evaluation, and storage:

```powershell
vl-quality run
```

The command reads JSON recordings from `data/raw/`, loads thresholds from `src/thresholds.json`, evaluates detected events against `data/ground_truth/`, and writes the DuckDB warehouse to `data/quality.duckdb` and Parquet files to `data/processed/`.

Paths can be overridden:

```powershell
vl-quality run --raw data/raw --truth data/ground_truth --output data/processed --db data/quality.duckdb --thresholds src/thresholds.json
```

The anomaly-detection logic is in `src/pipeline.py`; `src/data_storage.py` writes the database and Parquet outputs; `src/evaluation.py` calculates evaluation metrics.

## Open the dashboard

After processing the data, start the dashboard from the project root:

```powershell
streamlit run src/dashboard.py
```

It reads `data/quality.duckdb` and displays event summaries and recording trajectories.

## Project layout

- `src/main.py` — command-line entry point for generation and processing
- `src/dataset_generation.py` — dataset orchestration and fault plans
- `src/scenario_generation.py` — valid driving scenarios and motion
- `src/fault_injection.py` — injected data faults
- `src/pipeline.py` — anomaly detection and event creation
- `src/evaluation.py` — ground-truth matching and metrics
- `src/data_storage.py` — DuckDB tables and Parquet export
- `src/dashboard.py` — Streamlit dashboard
- `tests/test_pipeline.py` — pipeline tests
