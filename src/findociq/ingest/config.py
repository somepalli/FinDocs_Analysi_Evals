"""Typed YAML configuration for the ingestion pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from json import dumps
from pathlib import Path
from typing import Any

import yaml

from findociq.ingest.chunker import ChunkerConfig
from findociq.ingest.docling_parser import ParserConfig
from findociq.ingest.router import RouterConfig


@dataclass(frozen=True, slots=True)
class IngestionConfig:
    router: RouterConfig
    parser: ParserConfig
    chunker: ChunkerConfig

    @classmethod
    def from_yaml(cls, path: str | Path) -> IngestionConfig:
        source = Path(path)
        payload = yaml.safe_load(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"ingestion config must be a mapping: {source}")
        cls._require_sections(payload, source)
        return cls(
            router=RouterConfig(**cls._mapping(payload["router"], "router")),
            parser=ParserConfig(**cls._mapping(payload["parser"], "parser")),
            chunker=ChunkerConfig(**cls._mapping(payload["chunker"], "chunker")),
        )

    @property
    def config_hash(self) -> str:
        serialized = dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return sha256(serialized.encode()).hexdigest()

    @staticmethod
    def _require_sections(payload: dict[str, Any], source: Path) -> None:
        expected = {"router", "parser", "chunker"}
        actual = set(payload)
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            raise ValueError(
                f"invalid ingestion config sections in {source}; missing={missing}, extra={extra}"
            )

    @staticmethod
    def _mapping(value: Any, section: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError(f"ingestion config section '{section}' must be a mapping")
        return value
