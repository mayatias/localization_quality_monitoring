import math
from .config import (driving_scenarios, evasive_cruise_speed_mps, evasive_end_progress,
                    evasive_max_offset_meters, evasive_min_speed_mps, evasive_start_progress,
                    fps, highway_speed_mps, lane_change_end_progress,
                    lane_change_start_progress, lane_width_meters, mild_deviation_end_progress,
                    mild_deviation_max_offset_meters, mild_deviation_speed_mps,
                    mild_deviation_start_progress, point_count, reverse_backward_speed_mps,
                    reverse_forward_speed_mps, reverse_switch_progress, straight_speed_mps,
                    turn_end_progress, turn_max_heading_radians, turn_speed_mps,
                    turn_start_progress, urban_cycle_duration_seconds, urban_max_speed_mps,
                    urban_min_speed_mps, urban_slow_end_fraction, urban_slow_start_fraction)

def make_drive(drive_id, frames_num, scenario=driving_scenarios, point_count=point_count):
    # generate a synthetic driving recording with vehicle positions and timestamps
    if frames_num < 0:
        raise ValueError("the number of frames must be nonnegative")
    if point_count < 1:
        raise ValueError("point_count must be at least one")
    driving_scenario = {"turn": "turn_lane_change", "evasive": "evasive_maneuver"}.get(scenario, scenario)
    if driving_scenario not in driving_scenarios:
        raise ValueError(f"unknown scenario: {driving_scenario}")
    x = y = z = 0.0
    result = {"drive_id": drive_id, "sampling_rate_hz": fps, "coordinate_system": "local_xyz_m",
              "scenario_type": driving_scenario, "frames": []}
    for frame_id in range(frames_num):
        speed, heading = scenario_motion(driving_scenario, frame_id, frames_num)
        x += speed * math.cos(heading) / fps
        y += speed * math.sin(heading) / fps
        z += 0.015 * math.sin(frame_id / 35) / fps
        points = [[x + dx, y + dy, z] for dx, dy in point_offsets(point_count)]
        result["frames"].append({"frame_id": frame_id, "timestamp": frame_id / fps, "points": points})
    return result

def calculate_progress(frame, frame_count):
    # calculate the normalized progress of a frame within a recording
    return frame / max(frame_count - 1, 1)

def calculate_transition_progress(progress, start, end):
    # calculate progress within a specified transition interval
    return max(0.0, min(1.0, (progress - start) / (end - start)))

def smooth_transition(value):
    # smooth a transition to avoid abrupt changes at its boundaries
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)

def calculate_lateral_offset(progress, start, end, max_offset, return_to_start):
    # calculate the vehicle's lateral displacement during a maneuver
    if progress < start:
        return 0.0
    if progress > end:
        return 0.0 if return_to_start else max_offset
    transition = calculate_transition_progress(progress, start, end)
    if return_to_start:
        return max_offset * math.sin(math.pi * transition)
    return max_offset * smooth_transition(transition)

def calculate_lateral_speed(progress, frame_count, start, end, max_offset, return_to_start):
    # estimate lateral speed from the change in lateral displacement over time
    if frame_count <= 1:
        return 0.0
    progress_step = 1.0 / (frame_count - 1)
    previous_progress = max(0.0, progress - progress_step)
    next_progress = min(1.0, progress + progress_step)
    elapsed_seconds = (next_progress - previous_progress) * (frame_count - 1) / fps
    if elapsed_seconds == 0.0:
        return 0.0
    previous_offset = calculate_lateral_offset(previous_progress, start, end, max_offset, return_to_start)
    next_offset = calculate_lateral_offset(next_progress, start, end, max_offset, return_to_start)
    return (next_offset - previous_offset) / elapsed_seconds

def combine_forward_and_lateral_speed(forward_speed, lateral_speed):
    # convert forward and lateral velocity components into speed and heading
    return math.hypot(forward_speed, lateral_speed), math.atan2(lateral_speed, forward_speed)

def reverse_motion(progress):
    # calculate speed and heading for a forward-to-reverse maneuver
    if progress < reverse_switch_progress:
        return reverse_forward_speed_mps, 0.0
    return reverse_backward_speed_mps, 0.0

def turn_motion(progress):
    # calculate speed and heading during a temporary turning maneuver
    if turn_start_progress <= progress <= turn_end_progress:
        transition = calculate_transition_progress(progress, turn_start_progress, turn_end_progress)
        return turn_speed_mps, turn_max_heading_radians * math.sin(math.pi * transition)
    return turn_speed_mps, 0.0

def highway_motion():
    # calculate speed and heading for highway driving
    return highway_speed_mps, 0.0

def urban_motion(frame):
    # calculate speed and heading according to a repeating urban speed profile
    cycle_frames = max(1, round(urban_cycle_duration_seconds * fps))
    phase = (frame % cycle_frames) / cycle_frames
    if phase < urban_slow_start_fraction:
        transition = phase / urban_slow_start_fraction
        speed = urban_min_speed_mps + (urban_max_speed_mps - urban_min_speed_mps) * smooth_transition(transition)
    elif phase > 1.0 - urban_slow_end_fraction:
        transition = (1.0 - phase) / urban_slow_end_fraction
        speed = urban_min_speed_mps + (urban_max_speed_mps - urban_min_speed_mps) * smooth_transition(transition)
    else:
        speed = urban_max_speed_mps
    return speed, 0.0

def mild_deviation_motion(progress, frame_count):
    # calculate motion for a gradual lateral deviation followed by a return
    lateral_speed = calculate_lateral_speed(progress, frame_count, mild_deviation_start_progress,
        mild_deviation_end_progress, mild_deviation_max_offset_meters, return_to_start=True)
    return combine_forward_and_lateral_speed(mild_deviation_speed_mps, lateral_speed)

def lane_change_motion(progress, frame_count):
    # calculate motion for a lane change that ends in the adjacent lane
    lateral_speed = calculate_lateral_speed(progress, frame_count, lane_change_start_progress,
        lane_change_end_progress, lane_width_meters, return_to_start=False)
    return combine_forward_and_lateral_speed(straight_speed_mps, lateral_speed)

def evasive_maneuver_motion(progress, frame_count):
    # calculate motion for an evasive maneuver with lateral displacement and reduced speed
    lateral_speed = calculate_lateral_speed(progress, frame_count, evasive_start_progress,
        evasive_end_progress, evasive_max_offset_meters, return_to_start=True)
    forward_speed = evasive_min_speed_mps if evasive_start_progress <= progress <= evasive_end_progress else evasive_cruise_speed_mps
    return combine_forward_and_lateral_speed(forward_speed, lateral_speed)

def scenario_motion(scenario, frame, frame_count):
    # select the motion model for a scenario and calculate its speed and heading
    progress = calculate_progress(frame, frame_count)
    if scenario == "reverse":
        return reverse_motion(progress)
    if scenario == "turn_lane_change":
        return turn_motion(progress)
    if scenario == "highway":
        return highway_motion()
    if scenario == "urban":
        return urban_motion(frame)
    if scenario == "mild_deviation":
        return mild_deviation_motion(progress, frame_count)
    if scenario == "lane_change":
        return lane_change_motion(progress, frame_count)
    if scenario == "evasive_maneuver":
        return evasive_maneuver_motion(progress, frame_count)
    return straight_speed_mps, 0.0

def point_offsets(point_count):
    """
    Generate local coordinate offsets for the points in each frame.
    Input: point_count (int): Number of points to generate.
    Returns: list[tuple[float, float]]: Local x and y offsets for each point, in meters.
    """
    base = [(0.0, 0.0), (0.1, 0.0), (0.0, 0.1)]
    return [base[i] if i < len(base) else (0.1 * math.cos(i), 0.1 * math.sin(i)) for i in range(point_count)]