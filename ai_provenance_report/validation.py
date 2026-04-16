from __future__ import annotations

import re
from dataclasses import dataclass, field


TRAILER_PATTERN = re.compile(r"^(?P<key>[A-Za-z0-9-]+):\s*(?P<value>.*)$")
REQUIRED_TRAILER = "AI-Assisted"


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_trailers(message: str) -> dict[str, str]:
    trailers: dict[str, str] = {}
    for line in message.splitlines():
        match = TRAILER_PATTERN.match(line.strip())
        if match:
            trailers[match.group("key")] = match.group("value").strip()
    return trailers


def validate_commit_message_text(
    message: str,
    allowed_tools: list[str] | None = None,
) -> ValidationResult:
    trailers = parse_trailers(message)
    errors: list[str] = []
    warnings: list[str] = []

    ai_assisted = trailers.get(REQUIRED_TRAILER)
    if ai_assisted is None:
        errors.append("Missing required trailer: AI-Assisted: yes|no")
    elif ai_assisted not in {"yes", "no"}:
        errors.append("AI-Assisted must be either 'yes' or 'no'.")

    ai_tool = trailers.get("AI-Tool", "")
    if ai_assisted == "yes" and not ai_tool:
        warnings.append("AI-Tool is recommended when AI-Assisted: yes.")

    if allowed_tools and ai_tool and ai_tool not in allowed_tools:
        errors.append(
            f"AI-Tool '{ai_tool}' is not allowed. Allowed values: {', '.join(allowed_tools)}"
        )

    return ValidationResult(valid=not errors, errors=errors, warnings=warnings)


def parse_pr_checkbox(pr_body: str, label_names: set[str] | None = None) -> tuple[bool, bool]:
    label_names = label_names or set()
    if "ai-assisted" in {label.lower() for label in label_names}:
        return True, True

    checked = False
    found = False
    for line in pr_body.splitlines():
        normalized = line.strip().lower()
        if "ai-assisted changes included" in normalized and normalized.startswith("- ["):
            found = True
            if normalized.startswith("- [x]"):
                checked = True
            break
    return found, checked


def parse_pr_ai_tool(pr_body: str) -> str:
    for line in pr_body.splitlines():
        if line.lower().startswith("ai-tool:"):
            return line.split(":", 1)[1].strip()
    return ""


def validate_pr_body(pr_body: str, label_names: set[str] | None = None) -> ValidationResult:
    found, checked = parse_pr_checkbox(pr_body, label_names=label_names)
    errors: list[str] = []
    warnings: list[str] = []

    if not found and "ai-assisted" not in {label.lower() for label in (label_names or set())}:
        errors.append(
            "PR body must include checkbox line: - [ ] AI-Assisted changes included"
            "(or add label 'ai-assisted')."
        )
    if checked:
        ai_tool = parse_pr_ai_tool(pr_body)
        if not ai_tool:
            errors.append("PR marked as AI-assisted requires 'AI-Tool: <value>' in PR body.")
    elif found:
        warnings.append("PR indicates no AI assistance (checkbox unchecked).")

    return ValidationResult(valid=not errors, errors=errors, warnings=warnings)
