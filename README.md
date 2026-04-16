# AI Provenance MVP (Vendor-Agnostic)

This repository contains a **Declaration & Provenance** MVP to track AI-assisted changes without trying to detect AI-generated text.

## Architecture

- **Developer declaration**: commit trailers enforce explicit declaration:
  - `AI-Assisted: yes|no` (required)
  - `AI-Tool: <text>` (optional but recommended; required in PR body when AI is declared)
  - `AI-Session: <uuid>` (optional)
- **Local enforcement**:
  - Required `commit-msg` hook blocks undeclared commits
  - Optional `pre-commit` hook for DX signaling
  - Explicit bypass only via env var (`AI_DECLARATION_BYPASS=1`) and logged to `.git/ai-declaration-bypass.log`
- **CI/PR enforcement**:
  - GitHub Action validates all commits in PR for required trailer
  - PR body must include checkbox `- [ ] AI-Assisted changes included` (or fallback label `ai-assisted`)
  - If checked/label used, PR body must include `AI-Tool: <value>`
- **Configurable policy**:
  - `.ai-provenance.yml` controls strict/warn mode, allow-list for tools, bypass policy, merge commit exemption
- **Reporting**:
  - `ai-provenance-report` CLI scans git history and exports JSON/Markdown summary
  - Optional rough line-share heuristic from diffstats for `AI-Assisted: yes` commits

## File Tree

```text
.
├── .ai-provenance.yml
├── .github/workflows/ai-provenance.yml
├── .githooks/
│   ├── commit-msg
│   └── pre-commit
├── ai-provenance-report
├── ai_provenance_report/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── validation.py
│   ├── ci/validate_pr.py
│   └── hooks/commit_msg_hook.py
├── scripts/install-hooks.py
└── tests/test_validation.py
```

## Setup

Requirements:
- Python **3.11+**
- Dependencies: `click`, `PyYAML`

```bash
python -m pip install click PyYAML
python /absolute/path/to/repo/scripts/install-hooks.py
```

## Commit Format Example

```text
feat: add endpoint

AI-Assisted: yes
AI-Tool: Copilot
AI-Session: 550e8400-e29b-41d4-a716-446655440000
```

If no AI was used:

```text
fix: null check

AI-Assisted: no
```

## Bypass Policy

Allowed only when explicitly enabled in config:

```bash
AI_DECLARATION_BYPASS=1 git commit -m "hotfix"
```

Bypass events are logged in `.git/ai-declaration-bypass.log`.

## PR Template Requirements

PR body must contain:

```text
- [ ] AI-Assisted changes included
AI-Tool:
```

If checkbox is checked (or label `ai-assisted` is used), `AI-Tool:` must be non-empty.

## CI Behavior

Workflow: `.github/workflows/ai-provenance.yml`

Fail conditions:
1. Any PR commit missing `AI-Assisted: yes|no`
2. PR body missing required checkbox section (unless fallback label present)
3. AI-assisted PR without `AI-Tool` in PR body

## Reporting CLI

Run report on a range:

```bash
./ai-provenance-report --range HEAD~20..HEAD --estimate-line-share \
  --json-out /tmp/ai-report.json \
  --md-out /tmp/ai-report.md
```

Equivalent module execution:

```bash
python -m ai_provenance_report.cli --range HEAD~20..HEAD
```

Sample output:

```markdown
# AI Provenance Report

- Range: `HEAD~20..HEAD`
- Total commits: **20**
- Commits with `AI-Assisted: yes`: **7**
- Commits missing declaration: **1**
- Estimated AI-assisted line share: **38.42%**
```

## Tests

```bash
python -m unittest discover -s tests -q
```
