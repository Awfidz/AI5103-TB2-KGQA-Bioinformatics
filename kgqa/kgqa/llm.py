"""Client for a local Ollama server using its HTTP API."""

from __future__ import annotations

import requests

from .config import Settings, get_settings


class LLMError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, settings: Settings | None = None, model: str | None = None):
        s = settings or get_settings()
        self.base_url = s.ollama_url
        self.model = model or s.ollama_model
        self.num_ctx = s.ollama_num_ctx
        self.keep_alive = s.ollama_keep_alive

    def available_models(self) -> list[str]:
        """Names of models already pulled into Ollama (empty if the server is down)."""
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            r.raise_for_status()
        except requests.RequestException:
            return []
        return sorted(m["name"] for m in r.json().get("models", []))

    def is_up(self) -> bool:
        try:
            return requests.get(f"{self.base_url}/api/version", timeout=3).ok
        except requests.RequestException:
            return False

    def chat(self, messages: list[dict], temperature: float = 0.0, max_tokens: int = 700) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": temperature,
                "num_ctx": self.num_ctx,
                "num_predict": max_tokens,
            },
        }
        try:
            r = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=600)
        except requests.ConnectionError as exc:
            raise LLMError(
                f"Cannot reach Ollama at {self.base_url}. Is it running? (start the Ollama app or run `ollama serve`)"
            ) from exc
        except requests.RequestException as exc:
            raise LLMError(f"Ollama request failed: {exc}") from exc
        if r.status_code == 404:
            raise LLMError(f"Model '{self.model}' is not installed. Run: ollama pull {self.model}")
        if not r.ok:
            raise LLMError(f"Ollama error {r.status_code}: {r.text[:300]}")
        return r.json().get("message", {}).get("content", "")
