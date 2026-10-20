"""Structural policy regression; not a model-behavior or fleet-progress test."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def full_text():
    # Core plus references: phrases may live in either since the v0.22 split.
    return '\n'.join([ROOT.joinpath('SKILL.md').read_text()] + [p.read_text() for p in sorted(ROOT.glob('references/*.md'))])

class PickerPolicyTests(unittest.TestCase):
    def test_exhaustion_requires_new_bounded_evidence_not_scope_expansion(self):
        text=full_text()
        for phrase in ['two consecutive no-selection receipts','DIFFERENT authorized component','not discovery completeness','keep exploration read-only and resource-disjoint','Do not repeat this exploration','Checked scope exhausted','not an enforced runtime guarantee']:
            self.assertIn(phrase,text)
    def test_no_early_exit_and_terminal_results_continue(self):
        text=full_text()
        # Patch versions are metadata, not continuation policy.
        for phrase in ["Ask, don't block", 'otherwise run the docs-sync fallback', 'goals.py next', 'never fingerprint-exit', 'Resume the saved continuation before discovery', 'A completed slice is not itself a stop condition under continuation authority', 'default and explicit caller stops still apply', 'Disable change-only fingerprint monitors', 'CONTINUE selection', 'work_search', 'not a runtime guarantee']:
            self.assertIn(phrase, text)
        for obsolete in ['Step 0 — fast exit', 'return `[SILENT]` immediately', 'Step 0 fast exit bounds']:
            self.assertNotIn(obsolete, text)

    def test_preserves_authority_and_no_busywork(self):
        text=full_text()
        for phrase in ['No exhaustive scan, broad suite, fabricated task','financial/live/scope gates stay','not product acceptance','exactly `[SILENT]`','unknown usage is not zero','push, deploy, publish, spend money, place trades','actual process identity','Never push']:
            self.assertIn(phrase,text)

    def test_usable_backlog_takes_short_path_and_worker_owns_whole_outcome(self):
        core = ROOT.joinpath('SKILL.md').read_text()
        handoff = ROOT.joinpath('references/handoff.md').read_text()
        discovery = ROOT.joinpath('references/discovery.md').read_text()
        # This bundle ships no legacy cron prompt; verify its supported picker entry.
        for text in (core,):
            self.assertIn('Reconcile once', text)
            self.assertIn('discovery only when no usable task remains', text)
            self.assertIn('current agent session', text)
            self.assertNotIn('or\n   the profile has no `docs-sync` cron job', text)
        self.assertIn('Do not run a docs-sync prepass for a usable backlog task', core)
        self.assertIn('Historical native-card reference', handoff)
        self.assertIn('Historical cards are not leases', core)
        self.assertIn('Only when no usable backlog task remains', discovery)

    def test_history_reads_require_verified_profile_identity(self):
        text = ROOT.joinpath('references/state-and-recovery.md').read_text()
        for phrase in ['repository basename is not a profile ID',
                       'confirm the exact profile directory exists',
                       'never guess an alias, create a profile',
                       'missing continuity, not an abandoned owner',
                       'SQLite `mode=ro`',
                       'reopen only when the profile inventory or an explicit identity mapping changes']:
            self.assertIn(phrase, text)

    def test_core_stays_lean_and_points_to_every_reference(self):
        core = ROOT.joinpath('SKILL.md').read_text()
        self.assertLess(len(core.encode()), 16000, 'core SKILL.md must stay lean; move detail to references/')
        for ref in sorted(ROOT.glob('references/*.md')):
            self.assertIn(f'references/{ref.name}', core)

if __name__=='__main__':unittest.main()
