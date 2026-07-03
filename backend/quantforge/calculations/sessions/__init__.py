import pandas as pd


def session_flags(candles: pd.DataFrame, time_column: str = "time") -> pd.DataFrame:
    timestamps = pd.to_datetime(candles[time_column], utc=True)
    hour = timestamps.dt.hour
    asian = (hour >= 0) & (hour < 8)
    london = (hour >= 7) & (hour < 16)
    new_york = (hour >= 12) & (hour < 21)
    weekend = timestamps.dt.weekday >= 5
    overlap = london & new_york
    session = pd.Series("off_session", index=candles.index, dtype="object")
    session.loc[asian] = "Asian"
    session.loc[london] = "London"
    session.loc[new_york] = "New York"
    session.loc[overlap] = "London/New York"
    return pd.DataFrame(
        {
            "asian_session": asian,
            "london_session": london,
            "new_york_session": new_york,
            "session_overlap": overlap,
            "weekend": weekend,
            "holiday": False,
            "session_open": hour.isin([0, 7, 12]),
            "session_close": hour.isin([8, 16, 21]),
            "session": session,
        }
    )
