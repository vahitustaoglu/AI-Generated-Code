from __future__ import annotations

import subprocess
from pathlib import Path

from ai_provenance_report.config import load_config
from ai_provenance_report.validation import validate_commit_message_text, validate_pr_body


def _git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def _iter_pr_commits(repo_root: Path, base_ref: str, head_ref: str) -> list[tuple[str, str]]:
    commits = _git(["rev-list", f"{base_ref}..{head_ref}"], cwd=repo_root).splitlines()
    out: list[tuple[str, str]] = []
    for sha in commits:
        if not sha:
            continue
        parents = _git(["show", "--no-patch", "--format=%P", sha], cwd=repo_root).split()
        if len(parents) > 1:
            continue
        message = _git(["show", "--no-patch", "--format=%B", sha], cwd=repo_root)
        out.append((sha, message))
    return out


def _load_pr_data(event_path: Path | None, pr_json_path: Path | None) -> tuple[str, set[str]]:
    import json

    if pr_json_path is not None:
        pr_payload = json.loads(pr_json_path.read_text(encoding="utf-8"))
        body = pr_payload.get("body") or ""
        labels = {label.get("name", "") for label in pr_payload.get("labels", [])}
        return body, labels

    if event_path is None:
        return "", set()

    event = json.loads(event_path.read_text(encoding="utf-8"))
    pr = event.get("pull_request", {})
    body = pr.get("body") or ""
    labels = {label.get("name", "") for label in pr.get("labels", [])}
    return body, labels


def validate_pr_event(
    repo_root: Path,
    event_path: Path | None,
    pr_json_path: Path | None,
    base_ref: str,
    head_ref: str,
) -> int:
    config = load_config(repo_root)
    pr_body, labels = _load_pr_data(event_path=event_path, pr_json_path=pr_json_path)

    pr_result = validate_pr_body(pr_body, label_names=labels)
    commit_errors: list[str] = []

    for sha, message in _iter_pr_commits(repo_root, base_ref=base_ref, head_ref=head_ref):
        result = validate_commit_message_text(
            message=message,
            allowed_tools=config.get("allowed_ai_tools", []) or None,
        )
        if not result.valid:
            commit_errors.append(f"{sha[:12]}: {'; '.join(result.errors)}")

    has_errors = bool(pr_result.errors or commit_errors)
    if has_errors:
        print("AI provenance policy check failed.")
        if pr_result.errors:
            print("PR body issues:")
            for err in pr_result.errors:
                print(f"  - {err}")
        if commit_errors:
            print("Commit trailer issues:")
            for err in commit_errors:
                print(f"  - {err}")
        print("Remediation:")
        print("1) Ensure each commit has 'AI-Assisted: yes|no' trailer.")
        print("2) Include PR checkbox '- [ ] AI-Assisted changes included'.")
        print("3) If checked or label 'ai-assisted' is used, add 'AI-Tool: <value>' in PR body.")
        return 1

    if pr_result.warnings:
        for warning in pr_result.warnings:
            print(f"warning: {warning}")

    print("AI provenance policy check passed.")
    return 0


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate AI provenance policy in PR CI.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--event-path", required=False, default=None)
    parser.add_argument("--pr-json-path", required=False, default=None)
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--head-ref", required=True)
    args = parser.parse_args()

    return validate_pr_event(
        repo_root=Path(args.repo_root).resolve(),
        event_path=Path(args.event_path).resolve() if args.event_path else None,
        pr_json_path=Path(args.pr_json_path).resolve() if args.pr_json_path else None,
        base_ref=args.base_ref,
        head_ref=args.head_ref,
    )


if __name__ == "__main__":
    raise SystemExit(main())
