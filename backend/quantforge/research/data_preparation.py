import pandas as pd


class DataPreparationEngine:
    """Prepares market data for reproducible experiments and research runs."""

    def prepare(self, candles: pd.DataFrame) -> pd.DataFrame:
        frame = candles.copy()
        if "time" in frame:
            frame["time"] = pd.to_datetime(frame["time"], utc=True)
            frame = frame.drop_duplicates(subset=["time"]).sort_values("time")
        return frame.reset_index(drop=True)
