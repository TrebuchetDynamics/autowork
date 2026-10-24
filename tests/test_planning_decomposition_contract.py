"""Planning instruction guards, not model-adherence or worker-speed evidence.

Runtime scheduling remains covered by test_parallel_plan{,_hot}.py; these cases
protect the planner-facing contract rather than duplicate those runtime cases.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CRAFT = ' '.join((ROOT / 'skills/shared/PLANNING-CRAFT.md').read_text().split())
MAINTAINER = (ROOT / 'Src/pi_autowork/maintainer.py').read_text()


class PlanningDecompositionContractTests(unittest.TestCase):
    def test_bounded_large_file_fix_needs_no_extraction_task(self):
        for rule in ('A bounded fix may stay in a large or hot file',
                     'cohesion, observed conflict cost and testability',
                     'not a line-count or task-count threshold'):
            with self.subTest(rule=rule):
                self.assertIn(rule, CRAFT)
        self.assertNotIn('gets a first task that extracts', CRAFT)
        self.assertNotIn('longer than about 1500 lines', CRAFT)

    def test_cold_and_test_overlap_rank_without_fake_dependencies(self):
        for rule in ('Cold files, directories, globs and test modules only rank',
                     'three or more unfinished tasks',
                     'not merely a shared path or a preferred sequence',
                     'overlapping tests or cold files do not require extraction or dependency edges'):
            with self.subTest(rule=rule):
                self.assertIn(rule, CRAFT)
        self.assertNotIn('Tasks that can run together have disjoint writes', CRAFT)
        self.assertNotIn('a file that unlanded work also names waits', CRAFT)

    def test_real_conflicts_and_protected_paths_still_coordinate(self):
        for rule in ('same hot literal production file wait until the unlanded work lands',
                     'Shared named resources serialize their users',
                     'protected-path tasks serialize with each other, not ordinary tasks',
                     'New manifests, lockfiles, schema/migration and CI files need explicit protected paths',
                     'Never use them for caution',
                     'A shared registry', 'changes in one task'):
            with self.subTest(rule=rule):
                self.assertIn(rule, CRAFT)
        for rule in ('Preserve existing Dependencies unless prerequisite evidence justifies changing them',
                     'including held/noncandidate contracts and live slots awaiting integration',
                     'cold files, directories, globs and test modules only rank',
                     'A hot-to-cold change removes only the file gate',
                     'not genuine prerequisites or resource/protected-path admission',
                     'A held peer alone reserves no files',
                     'Shared named resources and protected-path coordination still apply',
                     'has a live worker (even if held), or whose commit waits to land'):
            with self.subTest(maintainer_rule=rule):
                self.assertIn(rule, MAINTAINER)

    def test_public_seam_budget_keeps_required_checks_and_review(self):
        worker = (ROOT / 'Src/pi_autowork/engine/parallel_dispatch.py').read_text()
        budget = 'at most one focused test per behavior'
        self.assertIn(budget, worker)
        self.assertIn(budget, CRAFT)
        for rule in ('Prefer extending an existing public test seam',
                     'A new focused file or class is optional',
                     'No tests merely for docs, config or renames',
                     'instruction-contract guard tests the instruction behavior itself',
                     'Reuse existing negative guards',
                     'Preserve every task-required check and independent review',
                     'affected landing check on the merged candidate',
                     'Main retains its separate full check',
                     'An affected-only pass is not a full-main pass'):
            with self.subTest(rule=rule):
                self.assertIn(rule, CRAFT)
        self.assertNotIn("Put each task's tests in a new focused test file or class", CRAFT)
        self.assertNotIn('the full check run on the merged tree', CRAFT)


if __name__ == '__main__':
    unittest.main()
