"""Configuration helpers."""
from __future__ import annotations

import os
from functools import cache
from pathlib import Path

import yaml


def project_root() -> Path:
    env = os.environ.get("CLIMARISK_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2]


@cache
def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_yaml(name: str) -> dict:
    """Load ``config/<name>``; returns a fresh copy so callers may mutate it."""
    import copy

    return copy.deepcopy(_load(str(project_root() / "config" / name)))
