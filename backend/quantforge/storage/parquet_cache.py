from pathlib import Path

import pandas as pd


class ParquetResearchCache:
    """Regenerable research cache backed by Parquet files."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write_frame(self, key: str, frame: pd.DataFrame) -> Path:
        path = self.root / f"{key}.parquet"
        frame.to_parquet(path)
        return path

    def read_frame(self, key: str) -> pd.DataFrame:
        return pd.read_parquet(self.root / f"{key}.parquet")

