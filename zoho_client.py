from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


class ZohoApiError(RuntimeError):
    """Error raised when Zoho returns a non-successful response."""


@dataclass(frozen=True)
class ZohoConfig:
    accounts_url: str
    api_domain: str
    client_id: str
    client_secret: str
    refresh_token: str
    api_version: str = "v8"


class ZohoCRMClient:
    def __init__(self, config: ZohoConfig, timeout: int = 30) -> None:
        self.config = config
        self.timeout = timeout

    def refresh_access_token(self) -> str:
        url = f"{self.config.accounts_url.rstrip('/')}/oauth/v2/token"
        response = requests.post(
            url,
            params={
                "refresh_token": self.config.refresh_token,
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "grant_type": "refresh_token",
            },
            timeout=self.timeout,
        )
        payload = self._parse_response(response)
        token = payload.get("access_token")
        if not token:
            raise ZohoApiError(f"Zoho no devolvio access_token: {payload}")
        return token

    def get_records(
        self,
        module: str,
        fields: list[str] | None = None,
        page: int = 1,
        per_page: int = 200,
    ) -> list[dict[str, Any]]:
        access_token = self.refresh_access_token()
        url = (
            f"{self.config.api_domain.rstrip('/')}/crm/"
            f"{self.config.api_version}/{module}"
        )
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if fields:
            params["fields"] = ",".join(fields)

        response = requests.get(
            url,
            headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
            params=params,
            timeout=self.timeout,
        )
        payload = self._parse_response(response)
        return payload.get("data", [])

    @staticmethod
    def _parse_response(response: requests.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise ZohoApiError(
                f"Respuesta no JSON de Zoho ({response.status_code}): {response.text}"
            ) from exc

        if response.status_code >= 400:
            raise ZohoApiError(f"Error de Zoho ({response.status_code}): {payload}")

        return payload
