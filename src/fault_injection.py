import copy
from .config import fps, timestamp_fault_types

def inject_missing_frame(recording, rng):
    """
    Remove one frame from a recording to simulate a missing-frame fault.
    Inputs:
        recording (dict): Original driving recording.
        rng (random.Random): Random number generator used to select the frame.
    Returns:
        tuple[dict, dict]: Modified recording and ground-truth event describing the fault.
    """
    result = copy_recording(recording)
    # the detector compares neighboring frame IDs, so edge removals are invisible
    index = choose_frame(result, rng, minimum=1, maximum=len(result["frames"]) - 2)
    target = result["frames"].pop(index)["frame_id"]
    return result, truth(result["drive_id"], "missing_frame", target, target, target, "Removed one frame record")

def inject_duplicate_frame_id(recording, rng):
    """
    Duplicate a frame record while keeping its original frame ID.
    Inputs:
        recording (dict): Original driving recording.
        rng (random.Random): Random number generator used to select the frame.
    Returns:
        tuple[dict, dict]: Modified recording and ground-truth event describing the fault.
    """
    result = copy_recording(recording)
    index = choose_frame(result, rng)
    frame = copy.deepcopy(result["frames"][index])
    result["frames"].insert(index + 1, frame)
    truth_val = truth(result["drive_id"], "duplicate_frame", frame["frame_id"], frame["frame_id"], frame["frame_id"],
                   "added a second record with an existing frame_id")
    truth_val["fault_subtype"] = "duplicate_frame_id"
    return result, truth_val

def inject_invalid_timestamp(recording, rng, subtype):
    """
    Inject a timestamp fault by removing, duplicating, decreasing, or shifting timestamps.
    Inputs:
        recording (dict): Original driving recording.
        rng (random.Random): Random number generator used to select the frame.
        subtype (str): Timestamp fault subtype to inject.
    Returns:
        tuple[dict, dict]: Modified recording and ground-truth event describing the fault.
    """
    if subtype not in timestamp_fault_types:
        raise ValueError(f"unsupported invalid timestamp subtype: {subtype}")
    result = copy_recording(recording)
    frames = result["frames"]
    index = choose_frame(result, rng, minimum=1)
    frame_id = frames[index]["frame_id"]
    if subtype == "missing":
        del frames[index]["timestamp"]
        event_type, description = "invalid_timestamp", "Removed the timestamp field"
        target: int | None = frame_id
    elif subtype == "duplicate":
        frames[index]["timestamp"] = frames[index - 1]["timestamp"]
        event_type, description, target = "duplicate_timestamp", "Copied the previous frame timestamp", frame_id
    elif subtype == "non_increasing":
        frames[index]["timestamp"] = frames[index - 1]["timestamp"] - 1 / fps
        event_type, description, target = "duplicate_timestamp", "Set timestamp earlier than the previous frame", frame_id
    else:
        shift = 1.0 - 1 / fps
        for later in frames[index:]:
            later["timestamp"] += shift
        event_type, description, target = "timestamp_gap", "Inserted an abnormally large timestamp gap", frame_id
    truth_valid = truth(result["drive_id"], event_type, target, frame_id, frame_id, description)
    truth_valid["fault_subtype"] = subtype
    return result, truth_valid

def inject_invalid_coordinates(recording, rng):
    """
    Replace one coordinate of a point with a missing value.
    Inputs:
        recording (dict): Original driving recording.
        rng (random.Random): Random number generator used to select the frame, point, and coordinate.
    Returns:
        tuple[dict, dict]: Modified recording and ground-truth event describing the fault.
    """
    result = copy_recording(recording)
    index = choose_frame(result, rng)
    frame = result["frames"][index]
    point = rng.randrange(len(frame["points"]))
    coordinate = rng.randrange(3)
    frame["points"][point][coordinate] = None
    target = frame["frame_id"]
    return result, truth(result["drive_id"], "invalid_coordinate", target, target, target,
                         "replaced one coordinate with a missing value")

def inject_position_jump(recording, rng):
    """
    Apply a large horizontal position offset to one frame to simulate a position jump.
    Inputs:
        recording (dict): Original driving recording.
        rng (random.Random): Random number generator used to select the frame and offset.
    Returns:
        tuple[dict, dict]: Modified recording and ground-truth event describing the fault.
    """
    result = copy_recording(recording)
    index = choose_frame(result, rng, minimum=1, maximum=len(result["frames"]) - 2)
    offset = rng.choice((-1.0, 1.0)) * rng.uniform(25.0, 45.0)
    for point in result["frames"][index]["points"]:
        point[0] += offset
    target = result["frames"][index]["frame_id"]
    return result, truth(result["drive_id"], "position_jump", target, target, target + 2,
                         "offset one frame; detector events cover the jump, return, and recovery frames")

def inject_extended_frame_gap(recording, rng):
    """
    Remove several consecutive frames to simulate an extended frame gap.
    Inputs:
        recording (dict): Original driving recording.
        rng (random.Random): Random number generator used to select the gap location and length.
    Returns:
        tuple[dict, dict]: Modified recording and ground-truth event describing the fault.
    """
    result = copy_recording(recording)
    frames = result["frames"]
    gap_length = min(rng.randint(3, 6), max(1, len(frames) - 2))
    start_index = rng.randint(1, len(frames) - gap_length - 1)
    removed = frames[start_index:start_index + gap_length]
    del frames[start_index:start_index + gap_length]
    start, end = removed[0]["frame_id"], removed[-1]["frame_id"]
    return result, truth(result["drive_id"], "missing_frame", start, start, end,
                         f"removed {len(removed)} consecutive frames") | {"fault_subtype": "extended_frame_gap"}

def choose_frame(recording, rng, minimum=0, maximum=None):
    # select a random frame index within the specified inclusive bounds
    upper = len(recording["frames"]) - 1 if maximum is None else maximum
    if upper < minimum:
        raise ValueError("recording does not contain enough frames for this fault")
    return rng.randint(minimum, upper)

def copy_recording(recording):
    # create an independent deep copy of a driving recording
    return copy.deepcopy(recording)

def truth(drive_id, kind, target, start, end, description):
    # create a ground-truth record describing an injected anomaly
    return {"injected_event_id": f"{drive_id}_{kind}_{start if start is not None else 'recording'}_{end if end is not None else ''}",
            "drive_id": drive_id, "anomaly_type": kind, "target_frame_id": target,
            "start_frame_id": start, "end_frame_id": end, "description": description}

