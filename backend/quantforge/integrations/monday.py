from typing import Any

import requests

from quantforge.config.settings import get_settings


class MondayApiError(RuntimeError):
    """Raised when Monday.com returns an API or transport error."""


class MondayClient:
    """Small Monday.com GraphQL client for project planning automation."""

    def __init__(self, api_token: str, api_url: str = "https://api.monday.com/v2") -> None:
        self._api_token = api_token
        self._api_url = api_url

    def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        response = requests.post(
            self._api_url,
            headers={
                "Authorization": self._api_token,
                "Content-Type": "application/json",
            },
            json={"query": query, "variables": variables or {}},
            timeout=30,
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise MondayApiError(f"Monday API returned non-JSON response: {response.text}") from exc

        if not response.ok:
            raise MondayApiError(f"Monday API HTTP {response.status_code}: {payload}")
        if payload.get("errors"):
            raise MondayApiError(f"Monday API errors: {payload['errors']}")
        return payload["data"]

    def me(self) -> dict[str, Any]:
        data = self.execute(
            """
            query {
              me {
                id
                name
                email
              }
            }
            """
        )
        return data["me"]

    def boards(self, limit: int = 25) -> list[dict[str, Any]]:
        data = self.execute(
            """
            query ($limit: Int!) {
              boards(limit: $limit) {
                id
                name
                state
                board_kind
              }
            }
            """,
            {"limit": limit},
        )
        return data["boards"]


def get_monday_client() -> MondayClient:
    settings = get_settings()
    if not settings.monday_api_token:
        raise RuntimeError("QUANTFORGE_MONDAY_API_TOKEN is not configured.")
    return MondayClient(settings.monday_api_token, settings.monday_api_url)
