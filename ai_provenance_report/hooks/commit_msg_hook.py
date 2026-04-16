from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

from ai_provenance_report.config import load_config
from ai_provenance_report.validation import validate_commit_message_text


def _repo_root_from_commit_msg_path(commit_msg_path: Path) -> Path:
    git_dir = commit_msg_path.parent
    return git_dir.parent


def _log_bypass(repo_root: Path, message_path: Path, env_var: str, log_file: str) -> None:
    log_path = repo_root / log_file
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        f"{dt.datetime.utcnow().isoformat()}Z "
        f"event=commit-msg-bypass env_var={env_var} "
        f"message_file={message_path}\n"
    )
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(payload)


def run_hook(message_file: str) -> int:
    message_path = Path(message_file).resolve()
    repo_root = _repo_root_from_commit_msg_path(message_path)
    config = load_config(repo_root)
    bypass = config.get("bypass", {})
    env_var = bypass.get("env_var", "AI_DECLARATION_BYPASS")
    allow_bypass = bool(bypass.get("allow", True))

    if os.getenv("CI") == "true" and os.getenv("GITHUB_ACTIONS") == "true":
        return 0

    if allow_bypass and os.getenv(env_var) == "1":
        _log_bypass(
            repo_root=repo_root,
            message_path=message_path,
            env_var=env_var,
            log_file=bypass.get("log_file", ".git/ai-declaration-bypass.log"),
        )
        print(
            f"[ai-provenance] Bypass accepted via {env_var}=1. "
            "This event has been logged."
        )
        return 0

    message = message_path.read_text(encoding="utf-8")
    result = validate_commit_message_text(
        message=message,
        allowed_tools=config.get("allowed_ai_tools", []) or None,
    )
    if result.valid:
        return 0

    print("[ai-provenance] Commit blocked.")
    for err in result.errors:
        print(f"  - {err}")
    print("Remediation:")
    print("  Add commit trailers, e.g.:")
    print("  AI-Assisted: no")
    print("  or")
    print("  AI-Assisted: yes")
    print("  AI-Tool: Copilot")
    print("  AI-Session: <uuid-optional>")
    return 1


def main() -> int:
    import sys

    if len(sys.argv) != 2:
        print("Usage: commit_msg_hook.py <commit_message_file>")
        return 1
    return run_hook(sys.argv[1])


if __name__ == "__main__":
    raise SystemExit(main())
