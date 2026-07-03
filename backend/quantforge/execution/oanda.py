from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True, slots=True)
class OandaExecutionClient:
    api_url: str
    account_id: str
    api_token: str

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def create_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            f"{self.api_url}/accounts/{self.account_id}/orders",
            json={"order": payload},
            headers=self._headers(),
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

