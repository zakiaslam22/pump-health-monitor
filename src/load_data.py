from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "sensor.csv"


def load_raw():
    """Load the raw pump sensor CSV and do basic cleaning."""
    df = pd.read_csv(RAW_PATH)
    df = df.drop(columns="Unnamed: 0")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


if __name__ == "__main__":
    df = load_raw()
    print(df.shape)
    print(df["timestamp"].dtype)
    print(df["timestamp"].min(), "to", df["timestamp"].max())
