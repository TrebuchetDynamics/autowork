"""Offline bundle portability checks; these do not launch a native/model worker."""
from pathlib import Path
import json
import posixpath
import re
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def vendored_reference(source, target):
    """Resolve a link inside a pinned upstream file through its UPSTREAM.json entry.

    Vendored bytes are never edited, so a relocation (`SKILL.md` stored as
    `PROTOCOL.md`) is recorded in the skill's UPSTREAM.json instead. Resolve the
    link against the original upstream path and then to its recorded location.
    """
    for folder in source.parents:
        if not folder.is_relative_to(ROOT):
            break
        manifest = folder / 'UPSTREAM.json'
        if not manifest.is_file():
            continue
        files = json.loads(manifest.read_text()).get('files')
        if not isinstance(files, dict):
            continue
        recorded = {entry['path']: original for original, entry in files.items()
                    if isinstance(entry, dict) and isinstance(entry.get('path'), str)}
        original = recorded.get(source.relative_to(folder).as_posix())
        if original is not None:
            wanted = posixpath.normpath(posixpath.join(posixpath.dirname(original), target))
            relocated = files.get(wanted)
            if isinstance(relocated, dict) and isinstance(relocated.get('path'), str):
                return folder / relocated['path']
            return None
    return None


def link_check_result(root):
    result = unittest.TestResult()
    with patch(f'{__name__}.ROOT', root):
        WorkflowContractTests('test_active_bundled_markdown_links_resolve').run(result)
    return result


class WorkflowContractTests(unittest.TestCase):
    def test_active_bundled_markdown_links_resolve(self):
        for source in (ROOT / 'skills').rglob('*.md'):
            # Vendored upstream provenance retains its original relative links.
            if 'accepted-plan-support' in source.parts:
                continue
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', source.read_text()):
                if '://' in target or target.startswith('#'):
                    continue
                # Ponytail's UPSTREAM.json pins this report as attribution;
                # docs/dependencies.md#bundled-ponytail excludes benchmark execution.
                # Only its original harness link is upstream-only, not active content.
                if (source == ROOT / 'skills/ponytail/upstream/benchmarks/results/2026-10-07-agentic.md'
                        and target == '../agentic/README.md'):
                    continue
                with self.subTest(source=source, target=target):
                    resolved = source.parent / target.split('#')[0]
                    relocated = vendored_reference(source, target.split('#')[0])
                    if relocated is not None:
                        resolved = relocated
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

    def test_only_pinned_ponytail_benchmark_harness_link_is_provenance(self):
        report = 'ponytail/upstream/benchmarks/results/2026-10-07-agentic.md'
        harness = '../agentic/README.md'
        cases = [
            (report, harness, True),
            (report, 'missing.md', False),
            ('ponytail/upstream/benchmarks/results/other.md', harness, False),
            ('ponytail/SKILL.md', harness, False),
            ('ponytail-gain/SKILL.md', harness, False),
            ('ponytail/upstream/skills/ponytail/PROTOCOL.md', harness, False),
            ('ponytail/upstream/references/method.md', harness, False),
            ('shared/PONYTAIL.md', harness, False),
        ]
        for source, target, passes in cases:
            with self.subTest(source=source, target=target):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    document = root / 'skills' / source
                    document.parent.mkdir(parents=True)
                    document.write_text(f'[reference]({target})\n')
                    result = link_check_result(root)
                    self.assertEqual(result.errors, [])
                    self.assertEqual(len(result.failures), 0 if passes else 1, result.failures)

    def test_relocated_vendored_link_resolves_through_upstream_manifest(self):
        manifest = {'files': {
            'skills/demo/SKILL.md': {'path': 'upstream/PROTOCOL.md'},
            'skills/demo/MECHANICS.md': {'path': 'upstream/MECHANICS.md'},
        }}
        for target, passes in [('SKILL.md', True), ('ABSENT.md', False)]:
            with self.subTest(target=target):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    (root / 'skills/demo/upstream').mkdir(parents=True)
                    (root / 'skills/demo/UPSTREAM.json').write_text(json.dumps(manifest))
                    (root / 'skills/demo/upstream/PROTOCOL.md').write_text('pinned\n')
                    (root / 'skills/demo/upstream/MECHANICS.md').write_text(
                        f'[reference]({target})\n')
                    result = link_check_result(root)
                    self.assertEqual(result.errors, [])
                    self.assertEqual(len(result.failures), 0 if passes else 1, result.failures)

    def test_active_docs_do_not_assume_shared_skills_install(self):
        for folder in ('autowork', 'docs-sync', 'git-commit-push'):
            for source in (ROOT / 'skills' / folder).rglob('*.md'):
                with self.subTest(source=source):
                    self.assertNotIn('~/.hermes/shared-skills/', source.read_text())


if __name__ == '__main__':
    unittest.main()
