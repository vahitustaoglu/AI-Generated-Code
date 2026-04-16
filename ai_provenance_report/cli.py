from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import click

from ai_provenance_report.validation import parse_trailers


@dataclass
class Report:
    range: str
    total_commits: int
    ai_assisted_commits: int
    missing_declaration_commits: int
    ai_assisted_line_share_percent: float | None


def _git(args: list[str], cwd: Path) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )
    return proc.stdout.strip()


def _commit_shas(cwd: Path, revision_range: str) -> list[str]:
    output = _git(["rev-list", revision_range], cwd=cwd)
    return [line for line in output.splitlines() if line]


def _commit_message(cwd: Path, sha: str) -> str:
    return _git(["show", "--no-patch", "--format=%B", sha], cwd=cwd)


def _diff_lines_for_commit(cwd: Path, sha: str) -> int:
    output = _git(["show", "--numstat", "--format=", sha], cwd=cwd)
    total = 0
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        added, deleted = parts[0], parts[1]
        if added.isdigit():
            total += int(added)
        if deleted.isdigit():
            total += int(deleted)
    return total


def generate_report(cwd: Path, revision_range: str, estimate_line_share: bool) -> Report:
    shas = _commit_shas(cwd, revision_range)
    total = len(shas)
    ai_yes_commits: list[str] = []
    missing = 0

    for sha in shas:
        trailers = parse_trailers(_commit_message(cwd, sha))
        assisted = trailers.get("AI-Assisted")
        if assisted == "yes":
            ai_yes_commits.append(sha)
        if assisted not in {"yes", "no"}:
            missing += 1

    line_share = None
    if estimate_line_share and total > 0:
        total_lines = sum(_diff_lines_for_commit(cwd, sha) for sha in shas)
        ai_lines = sum(_diff_lines_for_commit(cwd, sha) for sha in ai_yes_commits)
        line_share = (ai_lines / total_lines * 100.0) if total_lines > 0 else 0.0

    return Report(
        range=revision_range,
        total_commits=total,
        ai_assisted_commits=len(ai_yes_commits),
        missing_declaration_commits=missing,
        ai_assisted_line_share_percent=line_share,
    )


def to_markdown(report: Report) -> str:
    lines = [
        "# AI Provenance Report",
        "",
        f"- Range: `{report.range}`",
        f"- Total commits: **{report.total_commits}**",
        f"- Commits with `AI-Assisted: yes`: **{report.ai_assisted_commits}**",
        f"- Commits missing declaration: **{report.missing_declaration_commits}**",
    ]
    if report.ai_assisted_line_share_percent is not None:
        lines.append(
            f"- Estimated AI-assisted line share: **{report.ai_assisted_line_share_percent:.2f}%**"
        )
    return "\n".join(lines)


@click.command(name="ai-provenance-report")
@click.option("--range", "revision_range", default="HEAD", show_default=True)
@click.option("--estimate-line-share/--no-estimate-line-share", default=False)
@click.option("--json-out", type=click.Path(path_type=Path), default=None)
@click.option("--md-out", type=click.Path(path_type=Path), default=None)
def main(
    revision_range: str,
    estimate_line_share: bool,
    json_out: Path | None,
    md_out: Path | None,
) -> None:
    cwd = Path(".").resolve()
    report = generate_report(cwd, revision_range, estimate_line_share)

    click.echo(to_markdown(report))
    if json_out:
        json_out.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    if md_out:
        md_out.write_text(to_markdown(report) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
