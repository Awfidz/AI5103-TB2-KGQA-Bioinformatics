"""Runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

ONTO_NS = "https://itb.ac.id/a5103/tubes_2#"
RES_NS = "https://itb.ac.id/a5103/tubes_2/resource/"

PREFIXES = {
    "": ONTO_NS,
    "res": RES_NS,
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}


def prefix_block() -> str:
    return "\n".join(f"PREFIX {p}: <{ns}>" for p, ns in PREFIXES.items())


def _default_kg_files() -> list[Path]:
    """Turtle files loaded by the local backend.

    Uses the materialised KG (kg/*.ttl) when it exists, plus the
    ontology itself so class/property labels are always available.
    """
    files = [REPO_ROOT / "ontology" / "drug_discovery.ttl"]
    kg_dir = REPO_ROOT / "kg"
    if kg_dir.is_dir():
        files += sorted(kg_dir.glob("*.ttl"))
    return files


def _env_files() -> list[Path]:
    raw = os.getenv("KG_FILES", "").strip()
    if not raw:
        return _default_kg_files()
    return [Path(p).expanduser().resolve() for p in raw.split(os.pathsep) if p.strip()]


@dataclass
class Settings:
    # "auto" tries GraphDB first and falls back to the local Turtle files.
    kg_backend: str = field(default_factory=lambda: os.getenv("KG_BACKEND", "auto").lower())
    graphdb_url: str = field(default_factory=lambda: os.getenv("GRAPHDB_URL", "http://localhost:7200").rstrip("/"))
    graphdb_repo: str = field(default_factory=lambda: os.getenv("GRAPHDB_REPO", "drug-kgqa"))
    kg_files: list[Path] = field(default_factory=_env_files)

    ollama_url: str = field(default_factory=lambda: os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen2.5:7b"))
    # A 4K context keeps the KV cache small (~0.5 GB for a 7B model) on a 4 GB GPU.
    ollama_num_ctx: int = field(default_factory=lambda: int(os.getenv("OLLAMA_NUM_CTX", "4096")))
    # How long Ollama keeps the model in memory after the last request.
    ollama_keep_alive: str = field(default_factory=lambda: os.getenv("OLLAMA_KEEP_ALIVE", "10m"))

    max_attempts: int = field(default_factory=lambda: int(os.getenv("KGQA_MAX_ATTEMPTS", "3")))
    max_rows: int = field(default_factory=lambda: int(os.getenv("KGQA_MAX_ROWS", "50")))


def get_settings() -> Settings:
    return Settings()
