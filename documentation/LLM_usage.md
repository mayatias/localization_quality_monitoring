## LLM Usage

**Model:** GPT-6 (Luna), used through Codex.

### Use Cases

The LLM was used to assist with the following tasks:

- **Architecture design:** Exploring suitable local database solutions that support storing and querying data locally, as well as exporting tables in Parquet format.
- **Code organization and documentation:** Refactoring the data generation code into three separate Python modules to improve organization and readability:
  - `scenario_generation.py`
  - `fault_injection.py`
  - `dataset_generation.py`

  The LLM also assisted in adding docstrings describing each function's purpose, inputs, and outputs.
- **Code implementation:** Assisting with the implementation of specific parts of the project, including:
  - `dashboard.py`: Generating visualizations and charts for the dashboard.
  - `data_storage.py`: Implementing the logic for loading the generated tables into DuckDB.
- **README creation:** Writing the project's README, including its structure and usage instructions.

### Main Prompts and Approach

The LLM was used iteratively throughout development. The main prompts and tasks included:

- **Architecture design:** "Explore local database solutions that support querying data locally and exporting tables in Parquet format. Compare suitable options for this project."
- **Code refactoring:** "Split the data generation code into three separate modules: `scenario_generation.py`, `fault_injection.py`, and `dataset_generation.py`, with each module having a clear responsibility."
- **Function documentation:** "Add docstrings to the functions, explaining their purpose, input parameters, and return values."
- **Dashboard implementation:** "Help implement `dashboard.py` to display the project results through charts and visualizations."
- **Data storage implementation:** "Help implement `data_storage.py` to load the generated tables into DuckDB."
- **README creation:** "Write a README describing the project, its architecture, and how to run and use it."

The LLM was used as an iterative development assistant for architecture planning, code organization, implementation, and documentation. Its suggestions were incorporated as needed to improve the project's structure, readability, and functionality.