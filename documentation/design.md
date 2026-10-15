### Architecture and Design

The system is organized into modular components coordinated by a command-line entry point (`main.py`).

- **Dataset Generation:** Generates reproducible synthetic vehicle-drive recordings and corresponding ground-truth data.
- **Data Processing Pipeline:** Loads raw JSON recordings, validates frame and point data, detects missing frames and data-quality anomalies, and calculates motion metrics such as distance, speed, and acceleration. Detection thresholds are configurable.
- **Data Storage:** Stores processed drive summaries, frame records, point records, and detected events in DuckDB tables and exports the tables to Parquet files.
- **Evaluation:** Evaluates processing results against the generated ground-truth data and includes the evaluation summary in the command-line output.
- **Dashboard:** Provides an interactive interface for reviewing detected events and visualizing recording trajectories.

The processing pipeline separates data validation and anomaly detection from data persistence. This modular design supports independent configuration, processing, storage, and evaluation of vehicle-location data.