from pathlib import Path
from typing import Any

import pandas as pd


class FeatureStore:
    """Parquet-backed store for reusable feature vectors."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def write_frame(self, key: str, frame: pd.DataFrame) -> Path:
        path = self.root / f"{key}.parquet"
        frame.to_parquet(path, index=False)
        return path

    def read_frame(self, key: str) -> pd.DataFrame:
        return pd.read_parquet(self.root / f"{key}.parquet")

    def write_json_ready_vector(self, key: str, vector: dict[str, Any]) -> Path:
        frame = pd.DataFrame([vector])
        return self.write_frame(key, frame)
