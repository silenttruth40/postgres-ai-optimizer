from __future__ import annotations

import os

import httpx

DEFAULT_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


class APIError(RuntimeError):
    pass


class OptimizerClient:
    def __init__(self, base_url: str | None = None, timeout: float = 180.0) -> None:
        self.base_url = (base_url or DEFAULT_BASE).rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, json: dict | None = None) -> dict | list:
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(method, url, json=json)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            raise APIError(f"{exc.response.status_code}: {detail}") from exc
        except httpx.HTTPError as exc:
            raise APIError(f"API unavailable at {url}: {exc}") from exc

    def health(self) -> dict:
        return self._request("GET", "/health")

    def queries(self) -> list:
        return self._request("GET", "/queries")

    def analyze(self, query_id: str, sql: str | None = None) -> dict:
        payload = {"query_id": query_id}
        if sql:
            payload["sql"] = sql
        return self._request("POST", "/analyze", payload)

    def recommend(self, query_id: str, sql: str | None = None) -> dict:
        payload = {"query_id": query_id}
        if sql:
            payload["sql"] = sql
        return self._request("POST", "/recommend", payload)

    def benchmark(self, query_id: str, candidate_id: str | None = None, sql: str | None = None) -> dict:
        payload = {"query_id": query_id}
        if candidate_id:
            payload["candidate_id"] = candidate_id
        if sql:
            payload["sql"] = sql
        return self._request("POST", "/benchmark", payload)

    def results(self, query_id: str) -> dict:
        return self._request("GET", f"/results/{query_id}")

    def demo(self, query_id: str = "Q001") -> dict:
        return self._request("POST", "/demo/run", {"query_id": query_id})

    def privacy_demo(self) -> dict:
        return self._request("GET", "/privacy/demo")

