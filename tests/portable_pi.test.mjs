import assert from 'node:assert/strict';
import test from 'node:test';
import register from '../adapters/pi.mjs';

test('Pi registers workflows and all 13 research commands; routes literal arguments', async () => {
  const commands = new Map();
  const messages = [];
  register({registerCommand: (name, handler) => commands.set(name, handler),
    sendUserMessage: (...args) => messages.push(args)});
  assert.equal(commands.size, 24);
  assert.equal(commands.has('autogoal'), false);
  const raw = 'read-only\n$(literal); --no-push';
  await commands.get('plan_with_me').handler(raw, {isIdle: () => true});
  assert.match(messages[0][0], /# Plan With Me/);
  assert.equal(messages[0][0].endsWith(raw), true);
  assert.equal(messages[0][1], undefined);
  await commands.get('autoresearch_debug').handler(raw, {isIdle: () => false});
  assert.match(messages[1][0], /Selected subcommand: debug/);
  assert.deepEqual(messages[1][1], {deliverAs: 'followUp'});
  for (const [name, handler] of commands) {
    await handler.handler('questions only', {isIdle: () => true});
    assert.match(messages.at(-1)[0], /host contract/);
  }
});

test('npm package excludes local bytecode and keeps portable support files', async () => {
  const {execFileSync} = await import('node:child_process');
  const {fileURLToPath} = await import('node:url');
  const root = fileURLToPath(new URL('../', import.meta.url));
  const packed = JSON.parse(execFileSync('npm', ['pack', '--dry-run', '--json'], {cwd: root, encoding: 'utf8'}))[0];
  const paths = new Set(packed.files.map(f => f.path));
  assert.equal([...paths].some(p => p.includes('__pycache__') || p.endsWith('.pyc')), false);
  for (const path of ['adapters/pi.mjs', 'adapters/skills/COMMON.md',
    'skills/docs-sync/scripts/goals.py', 'skills/autoresearch/upstream/plan.md', 'skills/impeccable/LICENSE']) {
    assert.equal(paths.has(path), true, path);
  }
});
