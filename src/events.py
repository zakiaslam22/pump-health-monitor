import pandas as pd

from db import get_engine
from load_data import load_raw


def build_events(df):
    """Build the events table: one row per failure (pump down until back to NORMAL)."""
    is_down = df["machine_status"] != "NORMAL"
    was_down = is_down.shift(1, fill_value=False)

    # Outage starts: down now, but not down a minute ago (is_dpown==True)
    starts = df.loc[is_down & (was_down == False), "timestamp"].reset_index(drop=True)

    # Outage ends: not down now, but down a minute ago (first minute back to NORMAL) (is_down=False and was_down=True a min before)
    ends = df.loc[(is_down == False) & was_down, "timestamp"].reset_index(drop=True)

    events = pd.DataFrame({"start_time": starts, "end_time": ends})
    events["duration_hours"] = ((events["end_time"] - events["start_time"]).dt.total_seconds() / 3600).round(2)
    events.insert(0, "event_id", range(1, len(events) + 1))
    events.insert(1, "event_type", "Failure")
    return events


if __name__ == "__main__":
    df = load_raw()
    events = build_events(df)
    print(events)

    engine = get_engine()
    events.to_sql("events", con=engine, if_exists="replace", index=False)
    print("Saved events table to PostgreSQL.")