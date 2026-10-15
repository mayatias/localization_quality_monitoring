from pathlib import Path
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

def main():
    db_path = Path("data/quality.duckdb")
    st.set_page_config(page_title="VL Quality Monitor", layout="wide")
    st.title("Vehicle Location Quality Monitor")
    st.caption("Vehicle location data quality and anomaly investigation")
    if not db_path.exists():
        st.info("the warehouse does not exist yet, run the data generation and processing pipeline first")
        return
    # read the main tables from DuckDB
    try:
        with duckdb.connect(str(db_path), read_only=True) as conn:
            table_names = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
            required_tables = {"drives", "frames", "events"}
            missing_tables = required_tables - table_names
            if missing_tables:
                st.warning("the warehouse is missing these tables: " + ", ".join(sorted(missing_tables)))
                return

            drives = conn.execute(
                """
                SELECT *
                FROM drives
                ORDER BY drive_id
                """
            ).df()
            events = conn.execute(
                """
                SELECT *
                FROM events
                ORDER BY drive_id, timestamp_s
                """
            ).df()
    except Exception as exc:
        st.error(f"unable to read the DuckDB warehouse: {exc}")
        return
    col1, col2, col3 = st.columns(3)
    col1.metric("drives checked", len(drives))
    drives_with_events = (int((drives["anomaly_count"] > 0).sum()) if not drives.empty and "anomaly_count" in drives.columns else 0)
    col2.metric("Drives with events", drives_with_events)
    col3.metric("Events", len(events))
    # event distribution
    if not events.empty:
        st.subheader("Events by type")
        event_counts = (events.groupby("event_type").size().reset_index(name="count").sort_values("count", ascending=False))
        fig_events = px.bar(event_counts, x="event_type", y="count", color="event_type", title="Detected events by type",
                            labels={"event_type": "Event type", "count": "Number of events"})
        st.plotly_chart(fig_events, use_container_width=True)
    else:
        st.info("no events were found in the warehouse")
    # select a recording to investigate.
    if drives.empty:
        st.info("no recordings are available")
        return
    st.subheader("Investigate a recording")
    selected_drive = st.selectbox("select a drive:", drives["drive_id"].tolist())
    drive_details = drives.loc[drives["drive_id"] == selected_drive].iloc[0]
    drive_events = events.loc[events["drive_id"] == selected_drive].copy()
    # load frames for the selected recording
    try:
        with duckdb.connect(str(db_path), read_only=True) as conn:
            frames = conn.execute(
                """
                SELECT *
                FROM frames
                WHERE drive_id = ?
                ORDER BY timestamp_s, source_index
                """,
                [selected_drive],
            ).df()
    except Exception as exc:
        st.error(f"unable to load frame data: {exc}")
        return
    # recording summary
    st.markdown("### Recording summary")
    st.json(drive_details.to_dict())
    # events table
    st.markdown("### Detected events")
    if drive_events.empty:
        st.success("no events were detected for this recording")
    else:
        st.dataframe(drive_events, use_container_width=True, hide_index=True)
    if frames.empty:
        st.warning("no frame data is available for this recording")
        return
    # prepare the trajectory data
    coordinate_columns = ["position_x_m", "position_y_m", "position_z_m"]
    if not all(column in frames.columns for column in coordinate_columns):
        st.warning("the frame table does not contain all three position coordinates")
        return
    # only frames with complete 3D coordinates can be plotted in 3D
    trajectory = frames.dropna(subset=coordinate_columns).copy()
    if trajectory.empty:
        st.warning("no frames have complete 3D position coordinates")
        return
    # match events to frames using frame_record_id
    # events without a corresponding valid-position frame will remain visible in the events table but cannot be plotted in 3D
    if (not drive_events.empty and "frame_record_id" in drive_events.columns and "frame_record_id" in trajectory.columns):
        event_points = trajectory.merge(drive_events, on=["frame_record_id", "drive_id"], how="inner", suffixes=("_frame", "_event"))
    else:
        event_points = pd.DataFrame()
    # 3D trajectory
    st.subheader("3D Vehicle Trajectory")
    if "timestamp_s" in trajectory.columns:
        time_values = trajectory["timestamp_s"].fillna(-1)
    else:
        time_values = pd.Series(range(len(trajectory)), index=trajectory.index)
    # include speed in hover information when available
    hover_columns = ["frame_id", "timestamp_s"]
    if "speed_mps" in trajectory.columns:
        hover_columns.append("speed_mps")
    fig_3d = go.Figure()
    fig_3d.add_trace(go.Scatter3d(x=trajectory["position_x_m"], y=trajectory["position_y_m"],
                                  z=trajectory["position_z_m"], mode="lines+markers", name="Trajectory",
                                  line=dict(color=time_values, colorscale="Viridis", width=5, colorbar=dict(title="Time (s)")),
                                  marker=dict(size=2, color=time_values, colorscale="Viridis", showscale=False),
                                  customdata=trajectory[hover_columns].to_numpy(),
                                  hovertemplate=("X: %{x:.2f} m<br>" "Y: %{y:.2f} m<br>" "Z: %{z:.2f} m<br>" 
                                                 "Frame: %{customdata[0]}<br>" "Time: %{customdata[1]:.3f} s" +
                                                 ("<br>Speed: %{customdata[2]:.2f} m/s" if "speed_mps" in trajectory.columns else "")
                                                 + "<extra></extra>")))
    # add red markers for events that match valid 3D frame positions
    if not event_points.empty:
        event_frame_column = ("frame_id_event" if "frame_id_event" in event_points.columns else "frame_id")
        event_time_column = ("timestamp_s_event" if "timestamp_s_event" in event_points.columns else "timestamp_s")
        event_points["hover_details"] = ("Event: " + event_points["event_type"].astype(str)
                                         + "<br>Frame: " + event_points[event_frame_column].astype(str)
                                         + "<br>Time: " + event_points[event_time_column].astype(str)
                                         + "<br>Details: " + event_points["details"].astype(str))
        fig_3d.add_trace(go.Scatter3d(x=event_points["position_x_m"], y=event_points["position_y_m"],
                                      z=event_points["position_z_m"], mode="markers", name="Detected events",
                                      marker=dict(color="red", size=7, symbol="diamond",
                                                  line=dict(color="white", width=1)),
                                      text=event_points["hover_details"], hovertemplate="%{text}<extra></extra>"))
    fig_3d.update_layout(scene=dict(xaxis_title="X position (m)", yaxis_title="Y position (m)",
                                    zaxis_title="Z position (m)", aspectmode="data"),
                         legend=dict(orientation="h"), margin=dict(l=0, r=0, t=30, b=0), height=650)
    st.plotly_chart(fig_3d, use_container_width=True)
    if not drive_events.empty and event_points.empty:
        st.info("This recording has detected events, but none could be matched " 
                "to frames with valid 3D coordinates. The events remain visible " 
                "in the table above.")
    # 2D position over time
    if "timestamp_s" in frames.columns:
        position_columns = [column for column in coordinate_columns if column in frames.columns]
        position_data = frames.dropna(subset=["timestamp_s"]).copy()
        if not position_data.empty and position_columns:
            st.subheader("Position over time")
            fig_position = px.line(position_data, x="timestamp_s", y=position_columns, title="Vehicle position over time",
                                   labels={"timestamp_s": "time (s)", "value": "position (m)", "variable": "coordinate"})
            st.plotly_chart(fig_position, use_container_width=True)
    # 2D speed over time, with event timestamps marked in red
    if ("speed_mps" in frames.columns and "timestamp_s" in frames.columns):
        speed_data = frames.dropna(subset=["timestamp_s", "speed_mps"]).copy()
        if not speed_data.empty:
            st.subheader("Speed over time")
            fig_speed = px.line(speed_data, x="timestamp_s", y="speed_mps", title="Vehicle speed",
                                labels={"timestamp_s": "time (s)", "speed_mps": "speed (m/s)"})
            if (not drive_events.empty and "timestamp_s" in drive_events.columns):
                timed_events = drive_events.dropna(subset=["timestamp_s"])
                for _, event in timed_events.iterrows():
                    fig_speed.add_vline(x=float(event["timestamp_s"]), line_color="red",
                                        line_dash="dash", opacity=0.5)
            st.plotly_chart(fig_speed, use_container_width=True)

if __name__ == "__main__":
    main()