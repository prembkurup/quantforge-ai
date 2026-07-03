from pathlib import Path

import pandas as pd


class FeatureStore:
    """Stores reusable feature vectors for research reproducibility."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write(self, feature_set_key: str, frame: pd.DataFrame) -> Path:
        path = self.root / f"{feature_set_key}.parquet"
        frame.to_parquet(path)
        return path

    def read(self, feature_set_key: str) -> pd.DataFrame:
        return pd.read_parquet(self.root / f"{feature_set_key}.parquet")

