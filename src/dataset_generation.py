import copy
import json
import random
from pathlib import Path
from .config import driving_scenarios, point_count, recording_count, timestamp_fault_types, seed
from .fault_injection import (inject_duplicate_frame_id, inject_extended_frame_gap,
                            inject_invalid_coordinates, inject_invalid_timestamp,
                            inject_missing_frame, inject_position_jump)
from .scenario_generation import make_drive

def make_dataset(output_dir, truth_dir, count=recording_count, seed=seed):
    """
    Generate synthetic drive recordings and their corresponding ground-truth files.
    Inputs:
        output_dir (Path or str): Directory where the generated drive JSON files are saved.
        truth_dir (Path or str): Directory where the corresponding ground-truth JSON files are saved.
        count (int): Number of recordings to generate.
        seed (int): Random seed used to make the generation reproducible.
    Returns:
        list[Path]: Paths to the generated drive JSON files.
    """
    if count < 0:
        raise ValueError("count must be nonnegative")
    output_dir = Path(output_dir)
    truth_dir = Path(truth_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)
    for directory in (output_dir, truth_dir):
        for stale_file in directory.glob("drive_*.json"):
            stale_file.unlink()
    rng = random.Random(seed)
    written = []
    for index in range(count):
        drive_id = f"drive_{index + 1:03d}"
        scenario = driving_scenarios[index] if index < len(driving_scenarios) else rng.choice(driving_scenarios)
        valid = make_drive(drive_id, rng.randint(480, 960), scenario,
                           rng.choice((3, 3, 3, 4, 5)) or point_count)
        recording = copy.deepcopy(valid)
        ground_truth = []
        if index >= len(driving_scenarios):
            for fault, subtype in fault_plan(index - len(driving_scenarios), rng):
                if fault == "missing_frame":
                    recording, event = inject_missing_frame(recording, rng)
                elif fault == "duplicate_frame_id":
                    recording, event = inject_duplicate_frame_id(recording, rng)
                elif fault == "invalid_timestamp":
                    recording, event = inject_invalid_timestamp(recording, rng, subtype or "missing")
                elif fault == "invalid_coordinates":
                    recording, event = inject_invalid_coordinates(recording, rng)
                elif fault == "position_jump":
                    recording, event = inject_position_jump(recording, rng)
                else:
                    recording, event = inject_extended_frame_gap(recording, rng)
                ground_truth.append(event)
        path = output_dir / f"{drive_id}.json"
        path.write_text(json.dumps(recording, indent=2, allow_nan=False), encoding="utf-8")
        (truth_dir / f"{drive_id}.json").write_text(
            json.dumps(ground_truth, indent=2, allow_nan=False), encoding="utf-8")
        written.append(path)
    return written

def fault_plan(slot, rng):
    """
    Select predefined faults or seeded random fault combinations.
    Inputs:
        slot (int): Zero-based index used to determine the fault plan.
        rng (random.Random): Random number generator used for fault selection.
    Returns:
        list[tuple[str, str | None]]: A list of fault types and their optional
        subtypes to inject into the recording.
    """
    required = [[("missing_frame", None)], [("duplicate_frame_id", None)],
                [("invalid_timestamp", "missing")], [("invalid_timestamp", "duplicate")],
                [("invalid_timestamp", "non_increasing")], [("invalid_timestamp", "large_gap")],
                [("invalid_coordinates", None)], [("position_jump", None)],
                [("extended_frame_gap", None)]]
    if slot < len(required):
        return required[slot]
    options = ["missing_frame", "duplicate_frame_id", "invalid_coordinates", "position_jump", "extended_frame_gap"]
    first = rng.choice(options)
    second = rng.choice([fault for fault in options if fault != first])
    plan = [(first, None), (second, None)]
    if slot % 3 == 0:
        plan.append(("invalid_timestamp", rng.choice(timestamp_fault_types)))
    return plan