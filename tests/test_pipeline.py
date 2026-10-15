import json
import random
import unittest
from pathlib import Path
from vl_quality.config import seed, driving_scenarios, timestamp_fault_types, recording_count
from vl_quality.dataset_generation import make_dataset
from vl_quality.fault_injection import inject_duplicate_frame_id, inject_extended_frame_gap, inject_invalid_coordinates, inject_invalid_timestamp, inject_missing_frame, inject_position_jump
from vl_quality.scenario_generation import make_drive
from vl_quality.pipeline import process_drive, process_file
from vl_quality.data_storage import write_results
from vl_quality.evaluation import evaluate

THRESHOLDS = {"sampling_rate_hz": 16, "max_speed_mps": 80, "max_speed_change_mps": 20, "timestamp_tolerance_s": 0.005}

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(__file__).resolve().parents[1] / ".test_tmp"
        self.tmp.mkdir(exist_ok=True)
    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
    def test_generator_is_reproducible_and_schema_valid(self):
        self.assertEqual(make_drive("x", 8, "straight"), make_drive("x", 8, "straight"))
        drive = make_drive("x", 8, "straight")
        self.assertEqual(len(drive["frames"]), 8)
        self.assertEqual(drive["frames"][1]["timestamp"], 1 / 16)
        self.assertEqual(len(drive["frames"][0]["points"]), 3)
    def test_all_scenarios_are_valid_and_continuous(self):
        for scenario in driving_scenarios:
            with self.subTest(scenario=scenario):
                drive = make_drive("scenario", 160, scenario)
                self.assertEqual(drive["scenario_type"], scenario)
                self.assertEqual(drive["sampling_rate_hz"], 16)
                self.assertEqual(drive["coordinate_system"], "local_xyz_m")
                for index, frame in enumerate(drive["frames"]):
                    self.assertEqual(frame["frame_id"], index)
                    self.assertAlmostEqual(frame["timestamp"], index * 0.0625)
                    self.assertEqual(len(frame["points"]), 3)
                    self.assertTrue(all(len(point) == 3 for point in frame["points"]))
                    self.assertTrue(all(value is not None for point in frame["points"] for value in point))

    def test_all_fault_helpers_describe_their_changes(self):
        clean = make_drive("faults", 160, "straight")
        helpers = [(inject_missing_frame, ()), (inject_duplicate_frame_id, ()),
                   (inject_invalid_coordinates, ()), (inject_position_jump, ()),
                   (inject_extended_frame_gap, ())]
        rng = random.Random(10)
        for helper, args in helpers:
            changed, truth = helper(clean, rng, *args)
            self.assertEqual(clean["frames"], make_drive("faults", 160, "straight")["frames"])
            self.assertEqual(truth["drive_id"], "faults")
            self.assertTrue(truth["description"])
            self.assertIn("anomaly_type", truth)
            self.assertNotEqual(len(changed["frames"]), 0)
            if helper is inject_missing_frame:
                self.assertNotIn(truth["target_frame_id"], [f["frame_id"] for f in changed["frames"]])
            elif helper is inject_duplicate_frame_id:
                self.assertEqual([f["frame_id"] for f in changed["frames"]].count(truth["target_frame_id"]), 2)
            elif helper is inject_invalid_coordinates:
                target_frame = next(f for f in changed["frames"] if f["frame_id"] == truth["target_frame_id"])
                self.assertTrue(any(value is None for point in target_frame["points"] for value in point))
            elif helper is inject_position_jump:
                self.assertNotEqual(changed["frames"][truth["target_frame_id"]]["points"], clean["frames"][truth["target_frame_id"]]["points"])
                next_index = truth["target_frame_id"] + 1
                self.assertEqual(changed["frames"][next_index]["points"], clean["frames"][next_index]["points"])
            elif helper is inject_extended_frame_gap:
                present = {f["frame_id"] for f in changed["frames"]}
                self.assertTrue(all(frame_id not in present for frame_id in range(truth["start_frame_id"], truth["end_frame_id"] + 1)))
        for subtype in timestamp_fault_types:
            changed, truth = inject_invalid_timestamp(clean, rng, subtype)
            self.assertEqual(truth["fault_subtype"], subtype)
            self.assertEqual(truth["drive_id"], "faults")
            self.assertEqual(len(changed["frames"]), len(clean["frames"]))
            frame_index = truth["target_frame_id"]
            if subtype == "missing":
                self.assertNotIn("timestamp", changed["frames"][frame_index])
            elif subtype == "duplicate":
                self.assertEqual(changed["frames"][frame_index]["timestamp"], changed["frames"][frame_index - 1]["timestamp"])
            elif subtype == "non_increasing":
                self.assertLess(changed["frames"][frame_index]["timestamp"], changed["frames"][frame_index - 1]["timestamp"])
            else:
                self.assertGreater(changed["frames"][frame_index]["timestamp"] - changed["frames"][frame_index - 1]["timestamp"], 0.5)

    def test_dataset_default_coverage_reproducibility_and_seed_variation(self):
        first, truth_first = self.tmp / "first", self.tmp / "truth_first"
        second, truth_second = self.tmp / "second", self.tmp / "truth_second"
        other, truth_other = self.tmp / "other", self.tmp / "truth_other"
        paths = make_dataset(first, truth_first)
        self.assertEqual(len(paths), 30)
        make_dataset(second, truth_second)
        make_dataset(other, truth_other, count=30, seed=43)
        self.assertEqual([p.read_bytes() for p in paths], [(second / p.name).read_bytes() for p in paths])
        self.assertEqual([p.read_bytes() for p in sorted(truth_first.glob("*.json"))],
                         [(truth_second / p.name).read_bytes() for p in sorted(truth_first.glob("*.json"))])
        self.assertNotEqual(paths[0].read_bytes(), (other / paths[0].name).read_bytes())
        records = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
        self.assertEqual({record["scenario_type"] for record in records[:7]}, set(driving_scenarios))
        ground_truth = [item for path in sorted(truth_first.glob("*.json")) for item in json.loads(path.read_text(encoding="utf-8"))]
        subtypes = {item.get("fault_subtype") for item in ground_truth}
        self.assertTrue({"missing", "duplicate", "non_increasing", "large_gap", "duplicate_frame_id",
                         "extended_frame_gap"}.issubset(subtypes))
        self.assertEqual(len({record["drive_id"] for record in records}), 30)
        for record in records:
            self.assertTrue(all(isinstance(f.get("points"), list) and f["points"] for f in record["frames"]))
        processed = [process_drive(record, THRESHOLDS) for record in records]
        metrics = evaluate(processed, truth_first)
        self.assertEqual(metrics["ground_truth_count"], len(ground_truth))
        self.assertGreater(metrics["true_positives"], 0)
        self.assertEqual(metrics["false_negatives"], 0, metrics)
        self.assertEqual(recording_count, 30)
        self.assertEqual(seed, 42)
        make_dataset(first, truth_first, count=2, seed=42)
        self.assertEqual({p.name for p in first.glob("drive_*.json")}, {"drive_001.json", "drive_002.json"})
        self.assertEqual({p.name for p in truth_first.glob("drive_*.json")}, {"drive_001.json", "drive_002.json"})

    def test_injected_faults_match_pipeline_events_and_evaluation(self):
        clean = make_drive("fault-check", 160, "straight")
        rng = random.Random(123)
        cases = [lambda: inject_missing_frame(clean, rng),
                 lambda: inject_duplicate_frame_id(clean, rng),
                 lambda: inject_invalid_coordinates(clean, rng),
                 lambda: inject_position_jump(clean, rng),
                 lambda: inject_extended_frame_gap(clean, rng),
                 *(lambda subtype=subtype: inject_invalid_timestamp(clean, rng, subtype)
                   for subtype in timestamp_fault_types)]
        truth_dir = self.tmp / "fault_truth"
        truth_dir.mkdir()
        for index, make_case in enumerate(cases):
            with self.subTest(fault=index):
                recording, truth = make_case()
                (truth_dir / "fault.json").write_text(json.dumps([truth]), encoding="utf-8")
                result = process_drive(recording, THRESHOLDS)
                metrics = evaluate([result], truth_dir)
                self.assertEqual(metrics["true_positives"], 1, (truth, result["events"]))
                self.assertEqual(metrics["false_negatives"], 0, (truth, result["events"]))
                self.assertEqual(metrics["false_positives"], 0, (truth, result["events"]))
                (truth_dir / "fault.json").unlink()

    def test_small_dataset_gracefully_prioritizes_clean_scenarios(self):
        paths = make_dataset(self.tmp / "small", self.tmp / "small_truth", count=3)
        self.assertEqual(len(paths), 3)
        self.assertTrue(all(json.loads((self.tmp / "small_truth" / p.name).read_text()) == [] for p in paths))

    def test_detects_missing_duplicate_and_jump(self):
        drive = make_drive("x", 20, "straight")
        drive["frames"].pop(5)
        frame = dict(drive["frames"][8])
        frame["points"] = [p[:] for p in frame["points"]]
        drive["frames"].insert(9, frame)
        for point in drive["frames"][12]["points"]:
            point[0] += 45
        result = process_drive(drive, THRESHOLDS)
        types = {e["event_type"] for e in result["events"]}
        self.assertIn("missing_frame", types)
        self.assertIn("duplicate_frame", types)
        self.assertIn("position_jump", types)
        self.assertEqual(result["drive"]["frames_received"], 20)

    def test_invalid_and_duplicate_timestamps_and_points(self):
        drive = make_drive("x", 3, "straight")
        drive["frames"][1]["timestamp"] = drive["frames"][0]["timestamp"]
        drive["frames"][2]["points"] = [[1, None, 2]]
        types = [e["event_type"] for e in process_drive(drive, THRESHOLDS)["events"]]
        self.assertIn("duplicate_timestamp", types)
        self.assertIn("invalid_coordinate", types)
        self.assertIn("invalid_frame", types)

    def test_parse_failure_is_reported(self):
        path = self.tmp / "bad.json"
        path.write_text("{broken", encoding="utf-8")
        result = process_file(path, THRESHOLDS)
        self.assertEqual(result["events"][0]["event_type"], "input_error")

    def test_duckdb_parquet_and_evaluation(self):
        root = self.tmp
        drive = make_drive("x", 4, "straight")
        drive["frames"].pop(2)
        result = process_drive(drive, THRESHOLDS)
        (root / "truth").mkdir()
        (root / "truth" / "x.json").write_text(json.dumps([{"drive_id": "x",
                                                            "anomaly_type": "missing_frame",
                                                            "target_frame_id": 2}]),
                                               encoding="utf-8")
        output = root / "out"
        output.mkdir()
        (output / "events.parquet").write_bytes(b"stale parquet")
        database = root / "quality.duckdb"
        write_results([result], output, database)
        metrics = evaluate([result], root / "truth")
        self.assertEqual(metrics["true_positives"], 1)
        import duckdb
        with duckdb.connect(str(database), read_only=True) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM drives").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM events " "WHERE event_type='missing_frame'").fetchone()[0], 1)
            self.assertEqual(len(conn.execute("SELECT * FROM drives ORDER BY drive_id").fetchall()), 1)
            self.assertEqual(len(conn.execute("SELECT * FROM events " "ORDER BY drive_id, timestamp_s").fetchall()), 2)
            self.assertEqual(len(conn.execute("SELECT * FROM frames WHERE drive_id=? " 
                                              "ORDER BY timestamp_s, source_index",
                                              ["x"]).fetchall()), 3)
            self.assertEqual({row[0] for row in conn.execute("SHOW TABLES").fetchall()}, {"drives", "frames", "points", "events"})
            for table in ("drives", "frames", "points", "events"):
                parquet = output / f"{table}.parquet"
                self.assertTrue(parquet.exists())
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM read_parquet(?)",
                                              [str(parquet)]).fetchone()[0],
                                 conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

if __name__ == "__main__":
    unittest.main()