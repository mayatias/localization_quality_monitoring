import json
from pathlib import Path

def evaluate(results, truth_dir):
    """
    Evaluate detected anomalies by comparing them with ground-truth events.
    Inputs:
        results (list[dict]): Processed drive results containing detected events.
        truth_dir (Path): Directory containing ground-truth JSON files.
    Returns:
        dict: Evaluation metrics, including true positives, false positives,
              false negatives, precision, recall, F1 score, and matching details.
    """
    truth = []
    for path in sorted(truth_dir.glob("*.json")):
        try:
            items = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(items, list): truth.extend(items)
        except (OSError, json.JSONDecodeError):
            continue
    detected = [event for result in results for event in result["events"]]
    matched_detection_indexes: set[int] = set()
    tp = 0
    for target in truth:
        start = target.get("start_frame_id")
        end = target.get("end_frame_id")
        target_id = target.get("target_frame_id")
        if start is None:
            start = target_id
        if end is None:
            end = target_id
        matched = []
        for di, event in enumerate(detected):
            if (di not in matched_detection_indexes and target.get("drive_id") == event.get("drive_id")
                    and event_matches_fault(target, event, start, end, target_id)):
                matched.append(di)
        if matched:
            tp += 1
            matched_detection_indexes.update(matched)
    fp = len(detected) - len(matched_detection_indexes)
    fn = len(truth) - tp
    return {"ground_truth_count": len(truth), "detected_event_count": len(detected), "true_positives": tp,
        "false_positives": fp, "false_negatives": fn,
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn) if tp + fn else 0.0,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
        "matched_detection_count": len(matched_detection_indexes),
        "matching": "drive_id + anomaly_type/event_type + target frame or inclusive affected frame range; one fault counts once"}

def event_matches_fault(target, event, start, end, target_id):
    """
    Determine whether a detected event matches an injected fault.
    Matching rules account for the fault type, target frame, affected frame range, and related detection side effects.
    Inputs:
        target (dict): Ground-truth record describing the injected fault.
        event (dict): Detected anomaly event.
        start (int or float or None): First frame in the affected range.
        end (int or float or None): Last frame in the affected range.
        target_id (int or None): Specific target frame identifier.
    Returns:
        bool: True if the detected event matches the ground-truth fault; otherwise, False.
    """
    frame_id = event.get("frame_id")
    event_type = event.get("event_type")
    fault_type = target.get("anomaly_type")
    in_range = (isinstance(frame_id, (int, float)) and isinstance(start, (int, float))
                and isinstance(end, (int, float)) and start <= frame_id <= end)
    if fault_type == "position_jump":
        return in_range and event_type in {"position_jump", "speed_change"}
    if fault_type == "missing_frame":
        return ((in_range and event_type == "missing_frame")
                or (event_type == "timestamp_gap" and isinstance(end, (int, float)) and frame_id == end + 1))
    if fault_type == "invalid_timestamp" and target.get("fault_subtype") == "missing":
        return ((event_type == "invalid_timestamp" and frame_id == target_id)
                or (event_type == "timestamp_gap" and isinstance(end, (int, float)) and frame_id == end + 1))
    if fault_type == "duplicate_timestamp" and target.get("fault_subtype") == "non_increasing":
        return ((event_type in {"duplicate_timestamp", "invalid_timestamp"} and frame_id == target_id)
                or (event_type == "timestamp_gap" and isinstance(end, (int, float)) and frame_id == end + 1))
    if fault_type == "duplicate_frame":
        return frame_id == target_id and event_type in {"duplicate_frame", "duplicate_timestamp", "invalid_timestamp"}
    if fault_type == "duplicate_timestamp":
        return ((frame_id == target_id and event_type in {"duplicate_timestamp", "invalid_timestamp"})
                or (event_type == "timestamp_gap" and isinstance(end, (int, float)) and frame_id == end + 1))
    return event_type == fault_type and (frame_id == target_id or in_range)