from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG: dict[str, Any] = {
    "enforcement_mode": "strict",
    "allowed_ai_tools": [],
    "bypass": {
        "env_var": "AI_DECLARATION_BYPASS",
        "allow": True,
        "log_file": ".git/ai-declaration-bypass.log",
    },
    "exempt_merge_commits": True,
}


def load_config(repo_root: Path) -> dict[str, Any]:
    config_path = repo_root / ".ai-provenance.yml"
    if not config_path.exists():
        return DEFAULT_CONFIG.copy()
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    merged = DEFAULT_CONFIG.copy()
    merged.update(data)
    bypass = DEFAULT_CONFIG["bypass"].copy()
    bypass.update(merged.get("bypass", {}))
    merged["bypass"] = bypass
    return merged
