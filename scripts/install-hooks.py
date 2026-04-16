#!/usr/bin/env python3
"""Cross-platform installer for AI provenance git hooks."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


def _run_git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True)


def _make_executable(path: Path) -> None:
    if os.name == "nt":
        return
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    hooks_dir = repo_root / ".githooks"

    if not hooks_dir.exists():
        print(f"[ai-provenance] hooks directory missing: {hooks_dir}")
        return 1

    _run_git(["config", "core.hooksPath", str(hooks_dir)], cwd=repo_root)
    _make_executable(hooks_dir / "commit-msg")
    pre_commit = hooks_dir / "pre-commit"
    if pre_commit.exists():
        _make_executable(pre_commit)

    print("[ai-provenance] Installed hooks successfully.")
    print(f"[ai-provenance] core.hooksPath={hooks_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
