import json

table_names = ("drives", "frames", "points", "events")

table_columns_names = {"drives": ("drive_id", "duration_s", "sampling_rate_hz", "expected_frames", "scenario_type", "coordinate_system",
                            "frames_received", "missing_frames", "duplicate_frames", "invalid_frames", "anomaly_count"),
                 "frames": ("frame_record_id", "drive_id", "frame_id", "timestamp_s", "point_count", "position_x_m", "position_y_m",
                            "position_z_m", "source_index", "distance_m", "speed_mps", "acceleration_mps2"),
                 "points": ("point_record_id", "frame_record_id", "point_index", "x_m", "y_m", "z_m"),
                 "events": ("event_id", "drive_id", "frame_record_id", "frame_id", "event_type", "timestamp_s", "details")}

table_column_definitions = {
    "drives": """
        drive_id VARCHAR,
        duration_s DOUBLE,
        sampling_rate_hz DOUBLE,
        expected_frames BIGINT,
        scenario_type VARCHAR,
        coordinate_system VARCHAR,
        frames_received BIGINT,
        missing_frames BIGINT,
        duplicate_frames BIGINT,
        invalid_frames BIGINT,
        anomaly_count BIGINT
    """,
    "frames": """
        frame_record_id VARCHAR,
        drive_id VARCHAR,
        frame_id BIGINT,
        timestamp_s DOUBLE,
        point_count BIGINT,
        position_x_m DOUBLE,
        position_y_m DOUBLE,
        position_z_m DOUBLE,
        source_index BIGINT,
        distance_m DOUBLE,
        speed_mps DOUBLE,
        acceleration_mps2 DOUBLE
    """,
    "points": """
        point_record_id VARCHAR,
        frame_record_id VARCHAR,
        point_index BIGINT,
        x_m DOUBLE,
        y_m DOUBLE,
        z_m DOUBLE
    """,
    "events": """
        event_id VARCHAR,
        drive_id VARCHAR,
        frame_record_id VARCHAR,
        frame_id BIGINT,
        event_type VARCHAR,
        timestamp_s DOUBLE,
        details VARCHAR
    """
}

def write_results(results, output_dir, db_path):
    """
    Write processed results to DuckDB tables and export them as Parquet files.
    Inputs:
        results (list[dict]): Processed drive results containing summaries, frame records, point records, and detected events.
        output_dir (Path): Directory where the Parquet files are saved.
        db_path (Path): Path to the DuckDB database file.
    Returns:
        None: Creates or replaces database tables and writes Parquet files.
    """
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError("DuckDB is required. Install the project dependencies with `pip install -e .`.") from exc
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_paths = {name: output_dir / f"{name}.parquet" for name in table_names}
    for path in parquet_paths.values():
        path.unlink(missing_ok=True)
    (output_dir / "PARQUET_OPTIONAL_DEPENDENCY.txt").unlink(missing_ok=True)
    rows = {"drives": [result["drive"] for result in results],
            "frames": [row for result in results for row in result["frames"]],
            "points": [row for result in results for row in result["points"]],
            "events": [row for result in results for row in result["events"]]}
    with duckdb.connect(str(db_path)) as conn:
        for name in table_names:
            conn.execute(f"DROP TABLE IF EXISTS {name}")
        for name in table_names:
            conn.execute(f"CREATE TABLE {name} ({table_column_definitions[name]})")
            records = rows[name]
            if records:
                columns = table_columns_names[name]
                normalized = [{column: database_value(record.get(column)) for column in columns} for record in records]
                staging_path = output_dir / f".{name}.staging.json"
                staging_literal = str(staging_path).replace("'", "''")
                try:
                    staging_path.write_text(json.dumps(normalized, allow_nan=False), encoding="utf-8")
                    conn.execute(f"INSERT INTO {name} SELECT {', '.join(columns)} FROM read_json_auto('{staging_literal}')")
                finally:
                    staging_path.unlink(missing_ok=True)
            parquet_path = str(parquet_paths[name]).replace("'", "''")
            conn.execute(f"COPY {name} TO '{parquet_path}' (FORMAT PARQUET)")

def database_value(value):
    """
    Convert a value into a format suitable for database storage.
    Inputs:
        value (Any): Value to convert.
    Returns:
        Any: Dictionaries, lists, and tuples converted to JSON strings; booleans converted to integers; other values returned unchanged.
    """
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value)
    if isinstance(value, bool):
        return int(value)
    return value