
### Release Notes Next Version

#### i. Product Description

The Vehicle Location Quality Monitor is a data-processing and analysis tool designed to identify suspicious data-quality issues in vehicle-location recordings. It processes vehicle-drive data, validates frame and 3D point records, calculates motion metrics, and detects anomalies such as missing or duplicate frames, invalid coordinates, timestamp inconsistencies, and suspicious motion patterns.

The system supports reproducible synthetic data generation, configurable detection thresholds, evaluation against ground-truth data, and structured storage in DuckDB and Parquet. An interactive Streamlit dashboard enables users to review detected events and investigate recording trajectories.

#### ii. Usage Documentation / Example

##### Prerequisites

- Python 3.10 or newer.
- Install the project dependencies from the project root.

##### 1. Install the application

Install the command-line application:

```bash
python -m pip install -e .
```

To enable the interactive dashboard, install the optional dashboard dependencies:

```bash
python -m pip install -e ".[dashboard]"
```

##### 2. Generate synthetic recordings

Generate 30 sample drives using the default random seed:

```bash
vl-quality generate
```

The recordings are saved in `data/raw/`, and their corresponding ground-truth records are saved in `data/ground_truth/`.

Custom parameters can be specified:

```bash
vl-quality generate --count 30 --seed 42
```

##### 3. Process the recordings

Run the quality-monitoring pipeline:

```bash
vl-quality run
```

The command processes the JSON recordings, detects anomalies, evaluates the results against the ground truth, and stores the outputs.

Default output locations:

- DuckDB database: `data/quality.duckdb`
- Parquet tables: `data/processed/`
- Detection thresholds: `src/thresholds.json`

##### 4. Open the dashboard

After processing the data, launch the interactive dashboard:

```bash
streamlit run src/dashboard.py
```

The dashboard reads the DuckDB database and provides event summaries and recording trajectory visualizations.

##### Example Workflow

Generate synthetic data, process the recordings, and launch the dashboard. Review the detected events and use the available visualizations to investigate suspicious recordings.

#### iii. Known Issues

**Undetected missing frames at recording boundaries:**  
The system detects missing frames by identifying gaps between observed frame IDs. However, it cannot reliably detect missing frames at the end of a recording because the expected recording length or total number of frames is not independently known.

**Limitations of synthetic data:**  
The synthetic dataset was designed to cover a diverse range of driving scenarios and injected data-quality issues. However, it cannot represent every possible real-world situation, and real recordings may contain more complex or unexpected patterns that the current detection algorithm may fail to identify correctly.

#### iv. Coming Soon

- **Enhanced anomaly detection:** Refine detection rules and thresholds to reduce false positives and false negatives. Future improvements may include combining multiple indicators, such as speed, acceleration, timestamp consistency, and frame continuity, to make more reliable decisions about suspicious localization patterns.
- **Enhanced dashboard capabilities:** Improve recording investigation tools by adding filters for anomaly type and severity, as well as more detailed visualizations of vehicle trajectories and detected events over time. This would make it easier to investigate specific recordings and understand when and where anomalies occur.
- **Advanced recording search and scenario analysis:** Introduce the ability to search and filter recordings by characteristics such as scenario type, detected anomalies, and anomaly count. Future analysis tools could also compare anomaly patterns across different driving scenarios.