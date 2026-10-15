import json
import math
import uuid
from pathlib import Path

def load_thresholds(path: Path | None = None) -> dict[str, float]:
    path = path or Path("config/thresholds.json")
    return json.loads(path.read_text(encoding="utf-8"))

def process_drive(source, thresholds):
    """
    Validate and process a single drive recording, calculate motion metrics, and detect data quality anomalies.
    Inputs:
        source (dict): Raw drive recording containing metadata and frames.
        thresholds (dict): Configuration values used for validation and anomaly detection.
    Returns:
        dict: Processed drive summary, frame records, point records, and detected anomaly events.
    """
    drive_id = str(source.get("drive_id") or "unknown")
    rate = sampling_rate(source, thresholds)
    frames = source.get("frames")
    if not isinstance(frames, list):
        return empty_result(source, drive_id, "frames must be a list")
    frame_rows, point_rows, events = normalize_frames(frames, drive_id)
    detect_missing_frames(frame_rows, drive_id, events)
    calculate_motion(frame_rows, drive_id, rate, thresholds, events)
    summary = build_summary(source, drive_id, rate, frame_rows, events)
    return {"drive": summary, "frames": frame_rows, "points": point_rows, "events": events}

def sampling_rate(source, thresholds):
    value = source.get("sampling_rate_hz", thresholds.get("sampling_rate_hz", 16))
    try:
        rate = float(value)
        if not math.isfinite(rate) or rate <= 0:
            raise ValueError
        return rate
    except (TypeError, ValueError):
        return float(thresholds.get("sampling_rate_hz", 16))

def normalize_frames(frames, drive_id):
    frame_rows = []
    point_rows = []
    events = []
    seen_ids = set()
    seen_timestamps = set()
    previous_timestamp = None
    for index, raw_frame in enumerate(frames):
        record_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{drive_id}:{index}"))
        frame = raw_frame if isinstance(raw_frame, dict) else {}
        if not isinstance(raw_frame, dict):
            events.append(event(drive_id, record_id, None, "invalid_frame", None, "Frame record is not an object"))
        frame_id = frame.get("frame_id")
        timestamp = number(frame.get("timestamp"))
        check_frame_identity(drive_id, record_id, frame_id, timestamp, seen_ids, seen_timestamps, previous_timestamp, events)
        if timestamp is not None:
            previous_timestamp = timestamp
        points = frame.get("points")
        if not isinstance(points, list):
            points = []
        valid_points = normalize_points(points, drive_id, record_id, frame_id, timestamp, point_rows, events)
        if not valid_points:
            events.append(event(drive_id, record_id, frame_id, "invalid_frame", timestamp, "Frame has no valid 3D points"))
        center = centroid(valid_points)
        frame_rows.append({"frame_record_id": record_id, "drive_id": drive_id, "frame_id": frame_id,
                           "timestamp_s": timestamp, "point_count": len(points),
                           "position_x_m": center[0] if center else None,
                           "position_y_m": center[1] if center else None,
                           "position_z_m": center[2] if center else None, "source_index": index})
    return frame_rows, point_rows, events

def check_frame_identity(drive_id, record_id, frame_id, timestamp, seen_ids, seen_timestamps, previous_timestamp, events):
    if timestamp is not None and previous_timestamp is not None and timestamp < previous_timestamp:
        events.append(event(drive_id, record_id, frame_id, "invalid_timestamp", timestamp, "Timestamp decreases in source frame order"))
    if frame_id is None:
        events.append(event(drive_id, record_id, None, "invalid_frame", timestamp, "Missing frame_id"))
    elif frame_id in seen_ids:
        events.append(event(drive_id, record_id, frame_id, "duplicate_frame", timestamp, "frame_id already appeared in this drive"))
    else:
        seen_ids.add(frame_id)
    if timestamp is None:
        events.append(event(drive_id, record_id, frame_id, "invalid_timestamp", None, "Timestamp is missing, nonnumeric or nonfinite"))
    elif timestamp in seen_timestamps:
        events.append(event(drive_id, record_id, frame_id, "duplicate_timestamp", timestamp, "Timestamp already appeared in this drive"))
    else:
        seen_timestamps.add(timestamp)

def normalize_points(points, drive_id, record_id, frame_id, timestamp, point_rows, events):
    valid_points: list[list[float]] = []
    for point_index, point in enumerate(points):
        coords = [number(value) for value in point] if isinstance(point, (list, tuple)) else []
        if len(coords) != 3 or any(value is None for value in coords):
            coords = [None, None, None]
            events.append(event(drive_id, record_id, frame_id, "invalid_coordinate", timestamp,
                                 f"Point {point_index} must contain three finite coordinates"))
        else:
            valid_points.append(coords)
        point_rows.append({"point_record_id": f"{record_id}:{point_index}", "frame_record_id": record_id,
                           "point_index": point_index, "x_m": coords[0], "y_m": coords[1], "z_m": coords[2]})
    return valid_points

def centroid(points):
    if not points:
        return None
    return [sum(point[dimension] for point in points) / len(points) for dimension in range(3)]

def detect_missing_frames(frame_rows, drive_id, events):
    ordered = sorted((row for row in frame_rows if isinstance(row["frame_id"], int)), key=lambda row: row["frame_id"])
    for previous, current in zip(ordered, ordered[1:]):
        if current["frame_id"] > previous["frame_id"] + 1:
            for missing_id in range(previous["frame_id"] + 1, current["frame_id"]):
                events.append(event(drive_id, None, missing_id, "missing_frame", None, "Frame identifier is absent"))

def calculate_motion(frame_rows, drive_id, rate, thresholds, events):
    expected_dt = 1.0 / rate
    ordered = sorted((row for row in frame_rows if row["timestamp_s"] is not None), key=lambda row: (row["timestamp_s"], row["source_index"]))
    previous = None
    for row in ordered:
        row["distance_m"] = row["speed_mps"] = row["acceleration_mps2"] = None
        if previous is not None:
            calculate_frame_motion(previous, row, drive_id, expected_dt, thresholds, events)
        previous = row

def calculate_frame_motion(previous, current, drive_id, expected_dt, thresholds, events):
    dt = current["timestamp_s"] - previous["timestamp_s"]
    if dt <= 0:
        events.append(event(drive_id, current["frame_record_id"], current["frame_id"],
                             "invalid_timestamp", current["timestamp_s"], "Timestamp does not increase"))
    elif abs(dt - expected_dt) > float(thresholds.get("timestamp_tolerance_s", 0.005)):
        events.append(event(drive_id, current["frame_record_id"], current["frame_id"],
                             "timestamp_gap", current["timestamp_s"],
                             f"Observed dt={dt:.6g}s; expected {expected_dt:.6g}s"))
    previous_position = [previous[f"position_{axis}_m"] for axis in "xyz"]
    current_position = [current[f"position_{axis}_m"] for axis in "xyz"]
    if dt <= 0 or not all(value is not None for value in previous_position + current_position):
        return
    distance = math.dist(previous_position, current_position)
    speed = distance / dt
    current["distance_m"], current["speed_mps"] = distance, speed
    if speed > float(thresholds.get("max_speed_mps", 80)):
        events.append(event(drive_id, current["frame_record_id"], current["frame_id"],
                             "position_jump", current["timestamp_s"],
                             f"Speed {speed:.2f} m/s exceeds configured limit"))
    if previous.get("speed_mps") is not None:
        speed_change = speed - previous["speed_mps"]
        current["acceleration_mps2"] = speed_change / dt
        if abs(speed_change) > float(thresholds.get("max_speed_change_mps", 20)):
            events.append(event(drive_id, current["frame_record_id"], current["frame_id"],
                                 "speed_change", current["timestamp_s"],
                                 f"Speed changed by {speed_change:.2f} m/s"))

def build_summary(source, drive_id, rate, frame_rows, events):
    duration = max((row["timestamp_s"] for row in frame_rows if row["timestamp_s"] is not None), default=0.0)
    return {"drive_id": drive_id, "duration_s": duration, "sampling_rate_hz": rate,
            "expected_frames": int(round(duration * rate)) + (1 if frame_rows else 0),
            "scenario_type": source.get("scenario_type"), "coordinate_system": source.get("coordinate_system"),
            "frames_received": len(frame_rows), "missing_frames": len({event["frame_id"] for event in events if event["event_type"] == "missing_frame"}),
            "duplicate_frames": sum(event["event_type"] == "duplicate_frame" for event in events),
            "invalid_frames": len({event["frame_record_id"] for event in events if event["event_type"] in {"invalid_frame", "invalid_coordinate", "invalid_timestamp"} and event["frame_record_id"]}),
            "anomaly_count": len(events)}

def process_file(path, thresholds):
    try:
        source = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(source, dict):
            return empty_result({}, path.stem, "drive JSON root must be an object")
        return process_drive(source, thresholds)
    except (OSError, json.JSONDecodeError) as exc:
        return empty_result({}, path.stem, f"Unable to parse input: {exc}")

def empty_result(source, drive_id, error):
    error_event = event(drive_id, None, None, "input_error", None, error)
    return {"drive": {"drive_id": drive_id, "duration_s": 0, "sampling_rate_hz": 16,
        "expected_frames": 0, "scenario_type": source.get("scenario_type"), "coordinate_system": source.get("coordinate_system"),
        "frames_received": 0, "missing_frames": 0, "duplicate_frames": 0, "invalid_frames": 0, "anomaly_count": 1},
        "frames": [], "points": [], "events": [error_event]}

def event(drive_id, record_id, frame_id, kind, timestamp, details):
    event_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{drive_id}:{record_id}:{frame_id}:{kind}:{details}"))
    return {"event_id": event_id, "drive_id": drive_id, "frame_record_id": record_id,
            "frame_id": frame_id, "event_type": kind, "timestamp_s": timestamp, "details": details}

def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None