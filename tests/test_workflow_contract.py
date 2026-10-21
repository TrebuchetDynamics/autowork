"""Offline bundle portability checks; these do not launch a native/model worker."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WorkflowContractTests(unittest.TestCase):
    def test_active_bundled_markdown_links_resolve(self):
        for source in (ROOT / 'skills').rglob('*.md'):
            # Vendored upstream provenance retains its original relative links.
            if 'accepted-plan-support' in source.parts:
                continue
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', source.read_text()):
                if '://' in target or target.startswith('#'):
                    continue
                with self.subTest(source=source, target=target):
                    resolved = source.parent / target.split('#')[0]
                    vendor = ROOT / 'skills/engineering/upstream'
                    if source.is_relative_to(vendor):
                        if resolved.name == 'SKILL.md':
                            resolved = resolved.with_name('PROTOCOL.md')
                        relative = resolved.resolve().relative_to(vendor.resolve())
                        # Upstream contributor docs link to excluded host/eval files.
                        # Executable protocols and shared references get no exemption.
                        if source.name != 'PROTOCOL.md' and 'references' not in source.parts:
                            if relative.parts[0] == 'evals' or str(relative) == 'AGENTS.md':
                                continue
                    self.assertTrue(resolved.exists())

    def test_active_docs_do_not_assume_shared_skills_install(self):
        for folder in ('autowork', 'docs-sync', 'git-commit-push'):
            for source in (ROOT / 'skills' / folder).rglob('*.md'):
                with self.subTest(source=source):
                    self.assertNotIn('~/.hermes/shared-skills/', source.read_text())


if __name__ == '__main__':
    unittest.main()
