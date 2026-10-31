import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const skillsRoot = new URL('./skills/', import.meta.url);
const protocols = JSON.parse(await readFile(new URL('../skills/autoresearch/UPSTREAM.json', import.meta.url), 'utf8')).commands;
const workflows = {
  'plan-with-me': ['plan-with-me', 'Ask questions and plan together'],
  'plan-for-me': ['plan-for-me', 'Investigate, decide and save the plan'],
  'docs-sync': ['docs-sync', 'Keep documentation and the tasks/ store accurate'],
  autowork: ['autowork', 'Plan, execute, verify and commit a useful task'],
  autoresearch: ['autoresearch', 'Run bounded research or experiments'],
  engineering: ['engineering', 'Apply a focused engineering method'],
  'apk-get': ['apk-get', 'Find the app, build an ARM64 release APK and upload with s3upload'],
  'test-optimizer': ['test-optimizer', 'Reduce redundant tests while preserving real regression protection'],
  graphify: ['graphify', 'Query a local Graphify code graph before wide reading'],
  'writing-for-agents': ['writing-for-agents', 'Write and prune skills, AGENTS.md and agent docs'],
  'ask-autowork': ['ask-autowork', 'Find the skill that fits the situation'],
  grilling: ['grilling', 'Stress-test a plan or idea with rounds of questions'],
  'grill-with-docs': ['grill-with-docs', 'Grill a plan and record decisions as ADRs and terms'],
  'improve-codebase-architecture': ['improve-codebase-architecture', 'Find deepening opportunities and report them visually'],
  'bug-harvest': ['bug-harvest', 'Hunt evidence-backed bugs within scope and limits'],
  'autonomous-codebase-improver': ['autonomous-codebase-improver', 'Improve a repository through reviewed bounded slices'],
  'skill-folder-refactor': ['skill-folder-refactor', 'Split one named folder without changing behavior'],
  'unused-code': ['unused-code', 'Remove only proven unreachable code'],
  ponytail: ['ponytail', 'Choose Ponytail simplicity guidance or level'],
  'ponytail-review': ['ponytail-review', 'Review a change and connected code'],
  'ponytail-audit': ['ponytail-audit', 'Audit a repository or folder'],
  'ponytail-debt': ['ponytail-debt', 'Report deferred shortcut comments'],
  'ponytail-gain': ['ponytail-gain', 'Show upstream Ponytail benchmark results'],
  'ponytail-help': ['ponytail-help', 'Explain bundled Ponytail commands'],
  impeccable: ['impeccable', 'Improve interface design'],
  'ui-taste': ['ui-taste', 'Improve UI taste with Uizze playbooks'],
  'beautify-github-readme': ['beautify-github-readme', 'Redesign or audit a GitHub README'],
  'grill-me': ['plan-with-me', 'Plan With Me challenge mode (compatibility)', 'challenge'],
  lgtm: ['lgtm', 'Continue the last approved action'],
  blockers: ['blockers', 'Answer what blocks the queue, one picked option at a time'],
  'git-commit-push': ['git-commit-push', 'Commit and push, or pull and merge, owned changes'],
};

/** Native Pi command adapter. No subprocess, permission changes or install hooks. */
export default function register(pi) {
  const entries = Object.entries(workflows).map(([command, [skill, description, mode]]) => ({command, skill, description, mode}));
  for (const protocol of protocols) {
    entries.push({command: `autoresearch-${protocol}`, skill: 'autoresearch',
      description: `Autoresearch ${protocol}`, protocol});
  }
  for (const {command, skill, description, protocol, mode} of entries) {
    pi.registerCommand(command, {
      description,
      handler: async (args, ctx) => {
        // `/autowork blockers` and `/plan-with-me blockers` are `/blockers`.
        const [first, ...rest] = (args || '').trim().split(/\s+/);
        const routed = ['autowork', 'plan-with-me'].includes(skill) && !mode && first === 'blockers';
        const target = routed ? 'blockers' : skill;
        if (routed) args = rest.join(' ');
        const file = new URL(`${target}/SKILL.md`, skillsRoot);
        const body = await readFile(file, 'utf8');
        const planning = ['plan-for-me', 'plan-with-me'].includes(target)
          || (target === 'autoresearch' && (protocol === 'plan' || (!protocol && first === 'plan')));
        const contract = new URL('../skills/shared/RESEARCH-PLAN.md', import.meta.url);
        const boundary = planning
          ? `Planning contract. Source: ${fileURLToPath(contract)}\n`
            + `Resolve its references from that directory.\n\n${await readFile(contract, 'utf8')}\n\n`
          : '';
        const discovery = target === 'plan-for-me' && !(args || '').trim()
          ? 'Selected route: autonomous project discovery. No user objective was supplied. '
            + 'Investigate the repository first; do not ask for a goal. Follow the skill\'s '
            + 'discovery reference and save only evidence-backed work.\n\n'
          : '';
        const message = `Use this portable Autowork workflow. Source: ${fileURLToPath(file)}\n`
          + boundary
          + `Resolve the workflow references from ${fileURLToPath(new URL('./', file))}.\n\n${body}\n\n`
          + (protocol ? `Selected subcommand: ${protocol}\n\n` : '')
          + (mode ? `Selected mode: ${mode}\n\n` : '')
          + discovery
          + `User request (preserve scope and restrictions):\n${args}`;
        pi.sendUserMessage(message, ctx.isIdle() ? undefined : {deliverAs: 'followUp'});
      },
    });
  }
}
