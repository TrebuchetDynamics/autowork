import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const skillsRoot = new URL('./skills/', import.meta.url);
const protocols = JSON.parse(await readFile(new URL('../skills/autoresearch/UPSTREAM.json', import.meta.url), 'utf8')).commands;
const workflows = {
  plan_with_me: ['plan-with-me', 'Ask questions and plan together'],
  plan_for_me: ['plan-for-me', 'Investigate, decide and save the plan'],
  docs_sync: ['docs-sync', 'Keep documentation and TODO tasks accurate'],
  cron_autowork: ['cron-autowork', 'Create or update an Autowork schedule'],
  autowork: ['autowork', 'Plan, execute, verify and commit a useful task'],
  autoresearch: ['autoresearch', 'Run bounded research or experiments'],
  engineering: ['engineering', 'Apply a focused engineering method'],
  impeccable: ['impeccable', 'Improve interface design'],
  ui_taste: ['ui-taste', 'Improve UI taste with Uizze playbooks'],
  beautify_github_readme: ['beautify-github-readme', 'Redesign or audit a GitHub README'],
  grill_me: ['plan-with-me', 'Plan With Me challenge mode (compatibility)', 'challenge'],
  lgtm: ['lgtm', 'Continue the last approved action'],
  git_commit_push: ['git-commit-push', 'Commit and push, or pull and merge, owned changes'],
};

/** Native Pi command adapter. No subprocess, permission changes or install hooks. */
export default function register(pi) {
  const entries = Object.entries(workflows).map(([command, [skill, description, mode]]) => ({command, skill, description, mode}));
  for (const protocol of protocols) {
    entries.push({command: `autoresearch_${protocol}`, skill: 'autoresearch',
      description: `Autoresearch ${protocol}`, protocol});
  }
  for (const {command, skill, description, protocol, mode} of entries) {
    pi.registerCommand(command, {
      description,
      handler: async (args, ctx) => {
        const file = new URL(`${skill}/SKILL.md`, skillsRoot);
        const body = await readFile(file, 'utf8');
        const message = `Use this portable Autowork workflow. Source: ${fileURLToPath(file)}\n`
          + `Resolve its relative references from that directory.\n\n${body}\n\n`
          + (protocol ? `Selected subcommand: ${protocol}\n\n` : '')
          + (mode ? `Selected mode: ${mode}\n\n` : '')
          + `User request (preserve scope and restrictions):\n${args}`;
        pi.sendUserMessage(message, ctx.isIdle() ? undefined : {deliverAs: 'followUp'});
      },
    });
  }
}
