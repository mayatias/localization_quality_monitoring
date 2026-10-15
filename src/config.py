# recording settings
seed = 42
fps = 16
recording_count = 30
point_count = 3
driving_scenarios = ("straight", "reverse", "turn_lane_change", "highway", "urban", "mild_deviation", "evasive_maneuver")
timestamp_fault_types = ("missing", "duplicate", "non_increasing", "large_gap")

# urban driving: repeating speed profile
urban_cycle_duration_seconds = 4
urban_min_speed_mps = 0.25
urban_max_speed_mps = 4.0
urban_slow_start_fraction = 0.20
urban_slow_end_fraction = 0.15

# mild deviation: move sideways and return to the original path
mild_deviation_start_progress = 0.35
mild_deviation_end_progress = 0.65
mild_deviation_max_offset_meters = 0.5

# lane change: move sideways and continue in the new lane
lane_change_start_progress = 0.30
lane_change_end_progress = 0.55
lane_width_meters = 3.5

# evasive maneuver: quick deviation, reduced speed, and return
evasive_start_progress = 0.42
evasive_end_progress = 0.68
evasive_max_offset_meters = 2.0
evasive_cruise_speed_mps = 10.0
evasive_min_speed_mps = 5.0

# turn: straight, gradual turn, and straight again
turn_start_progress = 0.35
turn_end_progress = 0.55
turn_speed_mps = 8.0
turn_max_heading_radians = 0.5

# other driving speeds
straight_speed_mps = 10.0
reverse_forward_speed_mps = 2.0
reverse_backward_speed_mps = -1.0
highway_speed_mps = 30.0
mild_deviation_speed_mps = 7.0

# reverse driving: switch from forward to backward motion
reverse_switch_progress = 0.45
