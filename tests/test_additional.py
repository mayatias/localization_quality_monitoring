import json
import unittest
from pathlib import Path
from vl_quality.data_storage import write_results
from vl_quality.evaluation import evaluate
from vl_quality.pipeline import process_drive, process_file
from vl_quality.scenario_generation import make_drive

THRESHOLDS = {"sampling_rate_hz": 16, "max_speed_mps": 80, "max_speed_change_mps": 20,
              "timestamp_tolerance_s": 0.005}
EXPECTED_COLUMNS = {"drives": ("drive_id", "duration_s", "sampling_rate_hz", "expected_frames",
                               "scenario_type", "coordinate_system", "frames_received",
                               "missing_frames", "duplicate_frames", "invalid_frames", "anomaly_count"),
                    "frames": ("frame_record_id", "drive_id", "frame_id", "timestamp_s", "point_count",
                               "position_x_m", "position_y_m", "position_z_m", "source_index",
                               "distance_m", "speed_mps", "acceleration_mps2"),
                    "points": ("point_record_id", "frame_record_id", "point_index", "x_m", "y_m", "z_m"),
                    "events": ("event_id", "drive_id", "frame_record_id", "frame_id", "event_type", "timestamp_s", "details")}

class AdditionalPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = (Path(__file__).resolve().parents[1] / ".test_tmp_additional")
        self.tmp.mkdir(parents=True, exist_ok=True)
    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
    def test_evaluation_metrics(self):
        truth_dir = self.tmp / "metrics_truth"
        truth_dir.mkdir()
        truth = [{"drive_id": "drive_1", "anomaly_type": "missing_frame", "target_frame_id": 2},
                 {"drive_id": "drive_1", "anomaly_type": "position_jump", "target_frame_id": 8}]
        (truth_dir / "drive_1.json").write_text(json.dumps(truth), encoding="utf-8")
        results = [{"events": [{"drive_id": "drive_1", "event_type": "missing_frame", "frame_id": 2},
                               {"drive_id": "drive_1", "event_type": "invalid_coordinate", "frame_id": 4}]}]
        metrics = evaluate(results, truth_dir)
        self.assertEqual(metrics["ground_truth_count"], 2)
        self.assertEqual(metrics["detected_event_count"], 2)
        self.assertEqual(metrics["true_positives"], 1)
        self.assertEqual(metrics["false_positives"], 1)
        self.assertEqual(metrics["false_negatives"], 1)
        self.assertAlmostEqual(metrics["precision"], 0.5)
        self.assertAlmostEqual(metrics["recall"], 0.5)
        self.assertAlmostEqual(metrics["f1"], 0.5)

    def test_duckdb_schema_matches_expected_columns(self):
        import duckdb
        result = process_drive(make_drive("schema_drive", 4, "straight"), THRESHOLDS)
        output_dir = self.tmp / "parquet"
        db_path = self.tmp / "schema.duckdb"
        write_results([result], output_dir, db_path)
        with duckdb.connect(str(db_path), read_only=True) as conn:
            for table_name, expected_columns in EXPECTED_COLUMNS.items():
                with self.subTest(table=table_name):
                    rows = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
                    actual_columns = tuple(row[1] for row in rows)
                    self.assertEqual(actual_columns, expected_columns)

    def test_process_file_rejects_non_object_json_root(self):
        path = self.tmp / "list_root.json"
        path.write_text(json.dumps([{"frames": []}]), encoding="utf-8")
        result = process_file(path, THRESHOLDS)
        self.assertEqual(result["drive"]["drive_id"], path.stem)
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["event_type"], "input_error")
        self.assertIn("root must be an object", result["events"][0]["details"])
        self.assertEqual(result["frames"], [])
        self.assertEqual(result["points"], [])

    def test_process_file_reports_missing_input_file(self):
        path = self.tmp / "does_not_exist.json"
        result = process_file(path, THRESHOLDS)
        self.assertEqual(result["drive"]["drive_id"], path.stem)
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["event_type"], "input_error")
        self.assertIn("Unable to parse input", result["events"][0]["details"])

    def test_empty_frames_list_is_processed_without_crashing(self):
        path = self.tmp / "empty_drive.json"
        path.write_text(json.dumps({"drive_id": "empty_drive", "sampling_rate_hz": 16,
                                    "scenario_type": "straight", "coordinate_system": "local_xyz_m",
                                    "frames": []}), encoding="utf-8")
        result = process_file(path, THRESHOLDS)
        self.assertEqual(result["drive"]["drive_id"], "empty_drive")
        self.assertEqual(result["drive"]["frames_received"], 0)
        self.assertEqual(result["drive"]["anomaly_count"], 0)
        self.assertEqual(result["frames"], [])
        self.assertEqual(result["points"], [])
        self.assertEqual(result["events"], [])

    def test_process_file_reports_wrong_frames_type(self):
        path = self.tmp / "wrong_frames_type.json"
        path.write_text(json.dumps({"drive_id": "wrong_type", "frames": "not a list"}), encoding="utf-8")
        result = process_file(path, THRESHOLDS)
        self.assertEqual(result["drive"]["drive_id"], "wrong_type")
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["event_type"], "input_error")
        self.assertIn("frames must be a list", result["events"][0]["details"])

if __name__ == "__main__":
    unittest.main()