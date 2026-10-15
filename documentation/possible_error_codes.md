## Possible Error Types

These are the Python exception types the project raises directly in code, as opposed to the anomaly events written to the pipeline `events` table.

| Exception type | Raised in | Meaning and detection condition |
|---|---|---|
| `ValueError` | `src/scenario_generation.py`, `src/dataset_generation.py`, `src/fault_injection.py`, `src/pipeline.py` | Invalid arguments or unsupported values, such as negative frame counts, point counts below one, unknown scenario names, unsupported timestamp fault subtypes, not enough frames for a requested fault, or invalid sampling-rate input. |
| `FileNotFoundError` | `scripts/visualize_driving.py`, `scripts/export_and_inspect.py` | Missing required data files such as JSON recordings or the DuckDB database file. |
| `RuntimeError` | `src/data_storage.py` | Missing optional runtime dependency: DuckDB is not installed. |
| `OSError` | `src/pipeline.py`, `src/evaluation.py` | A drive file or truth file cannot be read or written because of filesystem issues. |
| `json.JSONDecodeError` | `src/pipeline.py`, `src/evaluation.py` | JSON data is malformed or cannot be parsed. |
| `Exception` | `src/dashboard.py` | A broad runtime failure while reading or processing the DuckDB warehouse in the Streamlit dashboard; this is caught and displayed as a UI error rather than re-raised. |

There are also environment-level dependency issues that may surface as `ImportError` when optional libraries are missing, but the project converts those to `RuntimeError` where it explicitly handles them. The project also emits `input_error`-style anomaly events when a drive record is malformed, but those are stored in the `events` output table and are not Python exceptions.