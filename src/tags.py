import pandas as pd

from db import get_engine
from load_data import PROJECT_ROOT, load_raw

LABELS_PATH = PROJECT_ROOT / "reference" / "ibm_sensor_labels.csv"


def quality_note(pct):
    """Turn a missing percentage into a short quality note."""
    if pct > 1:
        return f"Flagged: {pct}% missing"
    return "OK"


def build_tags(df):
    """Build the tags table (one row per sensor) from the cleaned data."""
    sensor_cols = [c for c in df.columns if c.startswith("sensor")]
    missing_pct = df[sensor_cols].isna().mean() * 100

    
    tags = pd.read_csv(LABELS_PATH)

    
    tags["tag_name"] = "PUMP01." + tags["tag_code"] + "." + tags["sensor_column"].str[-2:]
    tags["units"] = "unknown"
    tags["missing_pct"] = tags["sensor_column"].map(missing_pct).round(2)
    tags["quality_note"] = tags["missing_pct"].apply(quality_note)

    return tags[["tag_name", "sensor_column", "description", "units", "missing_pct", "quality_note"]]


if __name__ == "__main__":
    df = load_raw()
    tags = build_tags(df)
    print(tags.shape)

    engine = get_engine()
    tags.to_sql("tags", con=engine, if_exists="replace", index=False)
    print("Saved tags table to PostgreSQL.")