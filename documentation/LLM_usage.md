## LLM Usage

**Model:** GPT-6, used through Codex.

### Use Cases

The LLM was used as an iterative development assistant to support architecture planning, code organization, implementation, and documentation.

Examples of how it was used include:

- **Architecture design:** Assisted in planning the project architecture. For example, exploring suitable local database solutions that support storing and querying data locally, as well as exporting tables in Parquet format.

- **Code organization and documentation:** Assisted in improving code organization and readability. For example, splitting the data generation code into three separate Python modules, each with a clear responsibility:
  - `scenario_generation.py`
  - `fault_injection.py`
  - `dataset_generation.py`

  It also assisted in adding docstrings describing each function's purpose, input parameters, and return values.

- **Code implementation:** Assisted in implementing specific parts of the project. For example:
  - `dashboard.py`: Implementing visualizations and charts for the dashboard.
  - `data_storage.py`: Implementing the logic for loading the generated tables into DuckDB.

- **Supporting documentation:** Assisted in creating the project's supporting documentation files, including documentation of possible error codes, architecture and design, usage instructions and examples, known issues, and planned improvements for the next version.

### Main Prompt Examples

The LLM was used iteratively throughout development. Examples of prompts and tasks included:

- **Architecture design:** "Explore local database solutions that support querying data locally and exporting tables in Parquet format. Compare suitable options for this project."

- **Code refactoring:** "Split the data generation code into three separate modules: `scenario_generation.py`, `fault_injection.py`, and `dataset_generation.py`, with each module having a clear responsibility."

- **Function documentation:** "Add docstrings to the functions, explaining their purpose, input parameters, and return values."

- **Dashboard implementation:** "Help implement `dashboard.py` to display the project results through charts and visualizations."

- **Data storage implementation:** "Help implement `data_storage.py` to load the generated tables into DuckDB."

- **Supporting documentation:** "Help create the supporting documentation files covering error codes, architecture and design, usage instructions and examples, known issues, and planned improvements for the next version."

The LLM was used as an iterative development assistant, and its suggestions were reviewed and incorporated as needed to improve the project's structure, readability, and functionality.