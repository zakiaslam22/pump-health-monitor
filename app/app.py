import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Let the app import from src/
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from db import get_engine
from load_data import load_raw

st.set_page_config(page_title="Pump Health Monitor", layout="wide", menu_items={
        "About": "Pump Health Monitor: a mini process data system built on public pump "
                 "sensor data (Kaggle), structured like an industrial data historian. "
                 "Built by Zaki Aslam."
    })


@st.cache_resource
def engine():
    return get_engine()


@st.cache_data
def query(sql):
    return pd.read_sql(sql, engine())

#only loaded once in the beginning and then saved so it doesnt need to repeatedly fetcht he data over again (caching)
@st.cache_data
def raw_data():
    return load_raw()

# vrect is a method in plotly that draws a rectange over a specified period of time
def shade_outages(fig, events, label=True):
    """Shade each outage period in red on a Plotly time chart."""
    for _, e in events.iterrows():
        fig.add_vrect(
            x0=e["start_time"],
            x1=e["end_time"],
            fillcolor="red",
            opacity=0.2,
            line_width=0,
            annotation_text=f"#{e['event_id']}" if label else None,
            annotation_position="top left",
        )
    return fig


# Sensors offered in the explorer (all unflagged, under 1% missing)
SENSOR_OPTIONS = {
    "Motor speed (PUMP01.SPD.04)": "sensor_04",
    "Pump casing vibration (PUMP01.VIB.18)": "sensor_18",
    "Pump discharge flow (PUMP01.FLOW.35)": "sensor_35",
    "Pump inlet pressure (PUMP01.PRESS.48)": "sensor_48",
    "Pump thrust bearing temp (PUMP01.TEMP.40)": "sensor_40",
}

st.title("Pump Health Monitor")
st.caption(
    "A mini process data system built on public pump sensor data (Kaggle, 1-minute readings, "
    "April to August 2018). Designed to be structured like an industrial data historian with: tags, events and "
    "runtime metrics stored in PostgreSQL!"
)

tab_runtime, tab_quality, tab_results = st.tabs(["Runtime & downtime", "Data quality", "Results"])

# ---------------- Runtime & downtime ----------------
with tab_runtime:
    summary = query("SELECT * FROM runtime_summary").iloc[0]
    mtbf = query("SELECT * FROM mtbf_summary").iloc[0]
    events = query("SELECT * FROM events ORDER BY event_id")
    gaps = query("SELECT event_id, hours_since_last_failure FROM time_between_failures")

    # Key findings box (the st.info creates the blue box)
    longest = events.loc[events["duration_hours"].idxmax()]
    st.info(
        f"**Key findings:** the pump ran normally **{summary['uptime_pct']}%** of the time, with "
        f"**{int(summary['failures'])} failures**. Most outages were under a day, but failure "
        f"#{longest['event_id']} lasted **{longest['duration_hours'] / 24:.1f} days** "
        f"({longest['start_time']:%b %d} to {longest['end_time']:%b %d}), right after the longest "
        f"stretch of good running (about 34 days)."
    )

    # Headline numbers
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Uptime", f"{summary['uptime_pct']}%")
    c2.metric("Failures", int(summary["failures"]))
    c3.metric("Total downtime", f"{summary['total_downtime_hours']} h")
    c4.metric("MTBF", f"{mtbf['mtbf_days']} days")

    # Timeline of all 5 months Using the motor speed sensor as it clearly shows the diff between the outages and when it's working. 
    st.subheader("Five months at a glance")
    df = raw_data()
    hourly = df.set_index("timestamp")["sensor_04"].resample("1h").mean()
    fig = go.Figure(go.Scatter(x=hourly.index, y=hourly.values, mode="lines", line=dict(width=1)))
    shade_outages(fig, events)
    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis_title="Motor speed (hourly avg)",
        showlegend=False,
    )
    st.plotly_chart(fig)
    st.caption("Red bands = the 7 outages (pump not NORMAL). Motor speed drops to near zero during each one.")

    # Sensor explorer around one failure
    st.subheader("Zoom in on a failure")
    col_a, col_b = st.columns(2)
    choice = col_a.selectbox("Failure", events["event_id"], format_func=lambda i: f"#{i}")
    sensor_label = col_b.selectbox("Sensor", list(SENSOR_OPTIONS.keys()))
    sensor_col = SENSOR_OPTIONS[sensor_label]

    ev = events.set_index("event_id").loc[choice]
    window = df[
        (df["timestamp"] >= ev["start_time"] - pd.Timedelta(hours=48))
        & (df["timestamp"] <= ev["end_time"] + pd.Timedelta(hours=24))
    ]
    fig2 = go.Figure(go.Scatter(x=window["timestamp"], y=window[sensor_col], mode="lines", line=dict(width=1)))
    fig2.add_vrect(
        x0=ev["start_time"],
        x1=ev["end_time"],
        fillcolor="red",
        opacity=0.2,
        line_width=0,
        annotation_text="Outage",
        annotation_position="top left",
    )
    fig2.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10), yaxis_title=sensor_label)
    st.plotly_chart(fig2)
    st.caption(
        f"From 48 hours before the failure to 24 hours after recovery. Failure started "
        f"{ev['start_time']}, back to normal {ev['end_time']}. Sensor descriptions are IBM's best guess."
    )

    # Failures table
    st.subheader("All failures")
    st.dataframe(events.merge(gaps, on="event_id"), hide_index=True)

# ---------------- Data quality ----------------
with tab_quality:
    tags = query("SELECT * FROM tags ORDER BY missing_pct DESC")

    st.info(
        "**Key findings:** two kinds of missing data. (1) Individual sensors with gaps: one completely "
        "dead, one missing 35%, and a few missing 2 to 7%. (2) Short **collection outages** where every "
        "sensor went blank at once while the pump was running normally, which points to a data "
        "collection problem rather than sensor faults."
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Sensors in raw data", 52)
    c2.metric("Dropped (100% missing)", 1)
    c3.metric("Flagged (over 1% missing)", int((tags["quality_note"] != "OK").sum()))

    st.subheader("Missing data by sensor (%)")
    st.bar_chart(tags.set_index("tag_name")["missing_pct"])

    st.subheader("Flagged sensors")
    st.dataframe(tags[tags["quality_note"] != "OK"], hide_index=True)

    st.subheader("Collection outages: many sensors blank in the same minute")
    outages = pd.DataFrame([
        {"type": "Full blackout (all 52 sensors)", "start": "2018-04-27 17:48", "end": "2018-04-27 17:55", "minutes": 8, "pump status": "NORMAL"},
        {"type": "Full blackout (all 52 sensors)", "start": "2018-07-11 09:12", "end": "2018-07-11 09:14", "minutes": 3, "pump status": "NORMAL"},
        {"type": "Partial (15 to 29 sensors)", "start": "2018-05-31 23:52", "end": "2018-05-31 23:59", "minutes": 8, "pump status": "NORMAL"},
        {"type": "Partial (15 to 29 sensors)", "start": "2018-08-31 18:48", "end": "2018-08-31 18:50", "minutes": 3, "pump status": "NORMAL"},
    ])
    st.dataframe(outages, hide_index=True)
    st.markdown(
        "A few smaller partial dropouts also happened during recovery periods (April 18, July 3 to 4) "
        "and as scattered single minutes. Causes would need confirming with operations or the PI team."
    )

# ---------------- Honest results ----------------
with tab_results:
    st.markdown("""
### What I found
- The pump was running normally **93.4%** of the time, with **7 failures** and about **241 hours** of downtime.
- Most outages were under a day, but **one lasted almost 6 days** (June 28 to July 4), right after the longest stretch of good running (about 34 days).
- **Two kinds of missing data:** individual sensors with gaps (one completely dead, one missing 35%), and short **collection outages** where every sensor went blank at once while the pump was running.

### Limitations
- **Public dataset with anonymized sensors.** Sensor descriptions are IBM's best guess, and units are unknown.
- **One pump, 5 months, 7 failures.** Too few events to make strong claims.
- **1-minute data.** Anything shorter than a minute is invisible.
- **No maintenance records,** so I can't see *why* the pump failed or what was repaired.

### What real PI data and maintenance records would add
- Proper tag names, units and an Asset Framework hierarchy.
- Work orders linked to each outage, to separate failure types and repair times.
- Many similar pumps to compare against, and years of history.

### Next steps
- Load the full sensor history as a long-format `readings` table with quality labels, like a PI archive.
- Early-warning detection: rolling robust z-scores, and how many hours before each failure a warning appears.
- Flatline and out-of-range checks for stuck or maxed-out sensors.
- A small API modelled on the PI Web API.
""")