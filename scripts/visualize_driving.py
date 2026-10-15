import json
from pathlib import Path
import matplotlib.pyplot as plt
data_dir = Path("data/raw")
# scenarios we want to inspect
scenarios_to_plot = ["straight", "turn_lane_change", "lane_change", "reverse", "evasive_maneuver"]
json_files = sorted(data_dir.glob("drive_*.json"))
if not json_files:
    raise FileNotFoundError(f"no JSON files found in {data_dir.resolve()}")
plotted_scenarios = set()
for file_path in json_files:
    with file_path.open(encoding="utf-8") as f:
        drive = json.load(f)
    scenario = drive["scenario_type"]
    # plot only the first recording for each selected scenario
    if scenario not in scenarios_to_plot or scenario in plotted_scenarios:
        continue
    frames = drive["frames"]
    if not frames or not frames[0].get("points"):
        print(f"skipping empty recording: {file_path.name}")
        continue
    x = [frame["points"][0][0] for frame in frames]
    y = [frame["points"][0][1] for frame in frames]
    plt.figure(figsize=(8, 6))
    plt.plot(x, y, linewidth=1.5)
    plt.scatter(x[0], y[0], color="green", label="Start")
    plt.scatter(x[-1], y[-1], color="red", label="End")
    plt.title(f"{drive['drive_id']} - {scenario}")
    plt.xlabel("X position (m)")
    plt.ylabel("Y position (m)")
    plt.axis("equal")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()
    plotted_scenarios.add(scenario)

print("scenarios plotted:", sorted(plotted_scenarios))
print("scenarios not found:", sorted(set(scenarios_to_plot) - plotted_scenarios))