"""Local OpenAI-compatible Gemma generation client.

This module intentionally talks only to a local OpenAI-compatible endpoint.
It does not import or call proprietary model APIs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import yaml


@dataclass(frozen=True, slots=True)
class GenerationConfig:
    base_url: str
    model_id: str
    revision: str
    backend: Literal["ollama", "vllm"] = "vllm"
    temperature: float = 0.0
    seed: int = 17
    max_tokens: int = 1024
    timeout_seconds: int = 120

    @classmethod
    def from_yaml(cls, path: str | Path) -> GenerationConfig:
        source = Path(path)
        payload = yaml.safe_load(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"generation config must be a mapping: {source}")
        return cls(**payload)

    def __post_init__(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("generation base_url must be a local HTTP endpoint")
        if not self.model_id or not self.revision:
            raise ValueError("model_id and revision are required")
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        if self.max_tokens <= 0 or self.timeout_seconds <= 0:
            raise ValueError("max_tokens and timeout_seconds must be positive")


class GenerationClient(Protocol):
    def complete(self, prompt: str) -> str: ...


class LocalGemmaClient:
    """Minimal deterministic client for a local OpenAI-compatible runtime."""

    def __init__(self, config: GenerationConfig) -> None:
        self.config = config
        self._revision_validated = False

    def complete(self, prompt: str) -> str:
        if not prompt.strip():
            raise ValueError("generation prompt must not be blank")
        self._validate_revision()
        endpoint = self.config.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.config.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature,
            "seed": self.config.seed,
            "max_tokens": self.config.max_tokens,
            "response_format": {"type": "json_object"},
        }
        request = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:  # noqa: S310
                result = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as error:
            raise RuntimeError(f"local Gemma generation failed: {error}") from error
        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("local Gemma response did not contain message content") from error
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("local Gemma returned empty message content")
        return content

    def _validate_revision(self) -> None:
        if self._revision_validated or self.config.backend != "ollama":
            return
        parsed = urlparse(self.config.base_url)
        endpoint = f"{parsed.scheme}://{parsed.netloc}/api/tags"
        try:
            with urlopen(endpoint, timeout=self.config.timeout_seconds) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as error:
            raise RuntimeError(f"local Ollama revision check failed: {error}") from error
        models = payload.get("models", []) if isinstance(payload, dict) else []
        match = next(
            (
                item
                for item in models
                if isinstance(item, dict)
                and item.get("name") in {self.config.model_id, f"{self.config.model_id}:latest"}
            ),
            None,
        )
        if match is None:
            raise RuntimeError(f"local Ollama model is not installed: {self.config.model_id}")
        if match.get("digest") != self.config.revision:
            raise RuntimeError(
                f"local Ollama model revision mismatch for {self.config.model_id}: "
                f"expected {self.config.revision}, got {match.get('digest')}"
            )
        self._revision_validated = True


# Backwards-compatible import for callers created during the initial Phase 4 work.
VllmGemmaClient = LocalGemmaClient
