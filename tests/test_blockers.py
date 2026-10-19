"""`/blockers`: only unresolved owner decisions become questions; runners stay untouched.

The instruction checks are contracts only; they do not prove a model follows them.
The routing checks run the Hermes command handlers offline.
"""
from pathlib import Path
import re
import unittest

import test_plugin as fixture

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/blockers/SKILL.md'


def text(path):
    return re.sub(r'\s+', ' ', path.read_text())


class BlockersContract(unittest.TestCase):
    def setUp(self):
        self.ref = text(SKILL)

    def test_filters_routine_work_before_asking_for_missing_owner_decisions(self):
        for phrase in ('Filter before asking', 'existing authorization', 'integration-only',
                       'Do not announce a plan or ask whether to begin', 'first genuine question in the same turn',
                       'Hermes `clarify`', 'Claude Code `AskUserQuestion`', 'Codex `request_user_input`',
                       'Two to four choices', 'The recommended choice comes first', '`skip`', '`stop`'):
            self.assertIn(phrase, self.ref)

    def test_every_entry_point_is_the_same_command(self):
        self.assertIn('`/autowork blockers` and `/plan_with_me blockers` are the same command', self.ref)
        for path, phrase in ((ROOT / 'skills/autowork/SKILL.md', '/autowork blockers [repo|name]'),
                             (ROOT / 'adapters/skills/autowork/SKILL.md', '/autowork blockers [repo|name]'),
                             (ROOT / 'skills/plan-with-me/SKILL.md', '/plan_with_me blockers [repo|name]'),
                             (ROOT / 'adapters/skills/plan-with-me/SKILL.md', '/plan_with_me blockers [repo|name]'),
                             (ROOT / 'skills/plan-with-me/references/special-cases.md', '/plan_with_me blockers [repo|')):
            with self.subTest(path=str(path.relative_to(ROOT))):
                body = text(path)
                self.assertIn(phrase, body)
                self.assertIn('blockers/SKILL.md', body)
        self.assertIn('blockers/SKILL.md', text(ROOT / 'adapters/skills/blockers/SKILL.md'))
        self.assertIn("blockers: ['blockers',", (ROOT / 'adapters/pi.mjs').read_text())

    def test_replanning_uses_plan_with_me_per_task(self):
        for phrase in ("plan that one task with [Plan With Me](../plan-with-me/SKILL.md)'s planning craft",
                       'Then go to the next blocker'):
            self.assertIn(phrase, self.ref)

    def test_easiest_first_from_deterministic_effort(self):
        for phrase in ('one question at a time', 'easiest first', 'Order only the questions that survive filtering',
                       '| quick |', '| decision |', '| input |', '| investigate |',
                       'a larger `unblocks` count comes first, then the oldest'):
            self.assertIn(phrase, self.ref)

    def test_reads_the_runner_block_or_the_engine_without_a_model(self):
        for phrase in ('<!-- pi-autowork:questions:start -->', '<!-- pi-autowork:questions:end -->',
                       '--parallel-status --json', 'without a model call',
                       'no runner or schedule invokes it, so an idle queue still costs no tokens'):
            self.assertIn(phrase, self.ref)

    def test_answers_are_planning_not_runner_management(self):
        for phrase in ('never starts, stops, restarts or reconfigures a runner',
                       'never launches a competing execution or repair session', 'never kills a session',
                       'never pushes', "Edit that task's TODO.md entry", "never edit inside the runner's marked block",
                       'route separately requested publication through Git Commit Push', '--set-aside TASK` belong to the runner'):
            self.assertIn(phrase, self.ref)

    def test_held_tasks_are_inspected_even_when_question_block_exists(self):
        for phrase in ('Always inspect both', 'held tasks and owner questions',
                       'an empty questions block does not mean no held work',
                       'latest attempt', 'actual writer/session activity'):
            self.assertIn(phrase, self.ref)
        self.assertNotIn("- Without that block, the engine's view:", self.ref)

    def test_technical_holds_require_recovery_and_observed_outcomes(self):
        for phrase in ('Execute authorized local recovery', 'not merely another Next action',
                       'same task, candidate and cumulative budgets',
                       'saved answer is not a removed hold', 'missing terminal evidence stays unqualified',
                       'do not edit a live worker', 'read-only requests execute nothing'):
            self.assertIn(phrase, self.ref)
        self.assertNotIn('never launches an execution or repair session', self.ref)


    def test_portable_adapter_requires_repair_without_relaxing_guards(self):
        adapter = text(ROOT / 'adapters/skills/blockers/SKILL.md')
        for phrase in ('held tasks and owner questions', 'bounded authorized local recovery',
                       'verify the exact outcome', 'exclusive ownership', 'preserve explicit pauses',
                       'read-only requests neither execute nor write', 'never pushes'):
            self.assertIn(phrase, adapter)
        self.assertNotIn('It changes plans, not runners', adapter)


class BlockersRouting(unittest.TestCase):
    """india: `/autowork blockers` reached the Autowork skill, which launched a repair session."""
    setUp = fixture.PluginTests.setUp

    def register(self):
        self.plugin.SKILLS_DIR = ROOT / 'skills'
        self.plugin.register(self.ctx)

    def test_blockers_spellings_load_the_blockers_skill_with_the_target(self):
        self.register()
        for command, raw in (('blockers', 'india'), ('autowork', 'blockers india'), ('autowork', 'Blockers  india'),
                             ('plan_with_me', 'blockers india'), ('plan-with-me', 'blockers india')):
            with self.subTest(command=command, raw=raw):
                self.ctx.commands[command](raw)
                prompt, _ = self.ctx.messages[-1]
                self.assertIn('skill_view(name="autowork:blockers")', prompt)
                self.assertTrue(prompt.endswith('User arguments:\nindia'), prompt)

    def test_other_arguments_keep_their_skill(self):
        self.register()
        self.ctx.commands['autowork']('fix the blockers page')
        self.assertIn('autowork:autowork', self.ctx.messages[-1][0])
        self.ctx.commands['plan_with_me']('blockers-free roadmap')
        self.assertIn('autowork:plan-with-me', self.ctx.messages[-1][0])


if __name__ == '__main__':
    unittest.main()
