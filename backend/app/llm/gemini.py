"""Gemini client returning schema-constrained JSON.

Responses are constrained by responseSchema rather than parsed out of prose: the
agents' output is consumed by code, and a free-text answer that drifts one run in
twenty is a bug you meet in production rather than in a test.
"""

import asyncio
import json
import logging
from typing import Any

import httpx


logger = logging.getLogger(__name__)

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# Free-tier keys answer 429 on the pro models and 503 when flash is busy; both pass.
RETRY_STATUSES = {429, 500, 503, 504}


class LlmError(RuntimeError):
    pass


class GeminiClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: float = 120.0,
        max_attempts: int = 4,
        backoff_seconds: float = 2.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds

    async def generate_json(
        self, prompt: str, schema: dict[str, Any], temperature: float = 0.3
    ) -> dict[str, Any]:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": schema,
                "temperature": temperature,
            },
        }
        body = await self._post(payload)
        try:
            text = body["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise LlmError(f"unexpected response shape from {self.model}") from exc
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LlmError(f"{self.model} returned malformed JSON despite a schema") from exc

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = ENDPOINT.format(model=self.model)
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}
        last: str = "no attempt made"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(1, self.max_attempts + 1):
                try:
                    response = await client.post(url, json=payload, headers=headers)
                except httpx.RequestError as exc:
                    last = f"{type(exc).__name__}: {exc}"
                else:
                    if response.status_code == 200:
                        return response.json()
                    last = f"HTTP {response.status_code}: {response.text[:200]}"
                    if response.status_code not in RETRY_STATUSES:
                        raise LlmError(f"{self.model} refused the request ({last})")

                if attempt < self.max_attempts:
                    delay = self.backoff_seconds * 2 ** (attempt - 1)
                    logger.warning(
                        "llm call failed, retrying",
                        extra={"model": self.model, "attempt": attempt, "delay_seconds": delay},
                    )
                    await asyncio.sleep(delay)

        raise LlmError(f"{self.model} did not answer after {self.max_attempts} attempts ({last})")
