"""Offline project-status regressions; no native execution or timing claims."""

from pathlib import Path
import re
import unittest
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATH = ROOT / "docs/project.md"
PROJECT_TEXT = PROJECT_PATH.read_text(encoding="utf-8")


def section(text, heading, level=2):
    marker = "#" * level + " " + heading + "\n"
    body = text.split(marker, 1)[1]
    return re.split(r"^#{1," + str(level) + r"} ", body, maxsplit=1, flags=re.M)[0]


def anchors(text):
    """GitHub-style anchors for this document's plain Markdown headings."""
    result = set()
    counts = {}
    for heading in re.findall(r"^#{1,6} (.+)$", text, re.M):
        slug = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        result.add(slug if not count else f"{slug}-{count}")
    return result


class ProjectStatusTests(unittest.TestCase):
    def test_reviewed_delivery_is_current_not_pending(self):
        status = section(PROJECT_TEXT, "Planned work and verification")
        startup = section(PROJECT_TEXT, "Faster ready-task startup")
        self.assertRegex(status, r"TOOLSET-002[\s\S]*?reviewed and integrated locally")
        self.assertRegex(startup, r"TOOLSET-012 is independently reviewed and integrated\s+locally")
        self.assertNotIn("candidate still requires independent review and integration", PROJECT_TEXT)
        authority = section(PROJECT_TEXT, "Autonomous execution authority")
        self.assertIn("operating-policy question without another user permission round", authority)
        self.assertIn("caller scope and saved stop/batch limits control", authority)
        # The queue reset (2026-10-20) removed their goals from goals.json; the archive keeps them.
        archive = (ROOT / "TODO.archive.md").read_text()
        for task in ("TOOLSET-002", "TOOLSET-008", "TOOLSET-012"):
            with self.subTest(task=task):
                self.assertIn(task, archive)

    def test_task_context_metrics_and_ids_remain_historical(self):
        context = section(PROJECT_TEXT, "Task context simplification", 3)
        self.assertIn("five then-pending IDs", context)
        for task in ("TOOLSET-003", "TOOLSET-011", "TOOLSET-012", "TOOLSET-013", "TOOLSET-008"):
            self.assertIn(task, context)
        for measurement in ("1,524", "1,082", "29.0%"):
            self.assertIn(measurement, context)
        self.assertIn("At that point", context)
        self.assertIn("not a proven runtime speedup", context)
        self.assertIn("completed TOOLSET-008/012 bodies now reside", context)
        self.assertIn("At requirement capture (`f617808`)", PROJECT_TEXT)

    def test_live_qualification_stays_open_and_separate(self):
        # TOOLSET-003/011 were deleted with the rest of the queue on 2026-10-20, never closed as
        # passed; the project contract still says the qualification is pending.
        self.assertIn("Measured native qualification remains pending", PROJECT_TEXT)
        self.assertIn("externally enforced spending/descendant limits", PROJECT_TEXT)
        self.assertIn("not actual model startup or universal latency", PROJECT_TEXT)
        self.assertIn("Offline helper tests do not establish", PROJECT_TEXT)

    def test_project_local_links_and_fragments_exist(self):
        links = re.findall(r"\]\(([^)]+)\)", PROJECT_TEXT)
        self.assertTrue(links, "Link extraction must not silently match zero links")
        for link in links:
            if "://" in link or link.startswith("mailto:"):
                continue
            path, _, fragment = unquote(link).partition("#")
            target = (PROJECT_PATH.parent / path).resolve() if path else PROJECT_PATH
            with self.subTest(link=link):
                exists = target.is_dir() if path.endswith("/") else target.is_file()
                self.assertTrue(exists, f"Missing local link: {link}")
                if fragment:
                    self.assertIn(fragment, anchors(target.read_text(encoding="utf-8")))

    def test_completed_continuation_link_targets_archive(self):
        authority = section(PROJECT_TEXT, "Autonomous execution authority")
        self.assertIn("[TOOLSET-008](../TODO.archive.md#toolset-008--make-autowork-continuation-authority-consistent)", authority)
        self.assertNotIn("../TODO.md#toolset-008", PROJECT_TEXT)


if __name__ == "__main__":
    unittest.main()
