import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from ai_provenance_report.hooks.commit_msg_hook import run_hook
from ai_provenance_report.validation import (
    parse_pr_checkbox,
    parse_pr_ai_tool,
    parse_trailers,
    validate_commit_message_text,
    validate_pr_body,
)


class TrailerValidationTests(unittest.TestCase):
    def test_parse_trailers(self) -> None:
        msg = "feat: add thing\n\nAI-Assisted: yes\nAI-Tool: Copilot\n"
        trailers = parse_trailers(msg)
        self.assertEqual(trailers["AI-Assisted"], "yes")
        self.assertEqual(trailers["AI-Tool"], "Copilot")

    def test_validate_commit_requires_ai_assisted(self) -> None:
        result = validate_commit_message_text("feat: add\n")
        self.assertFalse(result.valid)
        self.assertIn("Missing required trailer", result.errors[0])

    def test_validate_commit_allowed_tool(self) -> None:
        msg = "feat\n\nAI-Assisted: yes\nAI-Tool: Copilot\n"
        ok = validate_commit_message_text(msg, allowed_tools=["Copilot"])
        bad = validate_commit_message_text(msg, allowed_tools=["Claude"])
        self.assertTrue(ok.valid)
        self.assertFalse(bad.valid)


class PrValidationTests(unittest.TestCase):
    def test_checkbox_detected(self) -> None:
        found, checked = parse_pr_checkbox("- [x] AI-Assisted changes included")
        self.assertTrue(found)
        self.assertTrue(checked)

    def test_label_fallback(self) -> None:
        found, checked = parse_pr_checkbox("No template", {"ai-assisted"})
        self.assertTrue(found)
        self.assertTrue(checked)

    def test_checked_requires_tool(self) -> None:
        body = "- [x] AI-Assisted changes included\n"
        result = validate_pr_body(body)
        self.assertFalse(result.valid)
        self.assertIn("AI-Tool", result.errors[0])

    def test_parse_pr_ai_tool(self) -> None:
        body = "- [x] AI-Assisted changes included\nAI-Tool: Cursor\n"
        self.assertEqual(parse_pr_ai_tool(body), "Cursor")


class HookBehaviorTests(unittest.TestCase):
    def test_hook_bypasses_in_github_actions(self) -> None:
        with TemporaryDirectory() as tmpdir:
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir(parents=True)
            msg_path = git_dir / "COMMIT_EDITMSG"
            msg_path.write_text("feat: no trailers\n", encoding="utf-8")
            with patch.dict("os.environ", {"CI": "true", "GITHUB_ACTIONS": "true"}, clear=False):
                self.assertEqual(run_hook(str(msg_path)), 0)


if __name__ == "__main__":
    unittest.main()
