import assert from 'node:assert/strict';
import test from 'node:test';
import register from '../adapters/pi.mjs';

test('Pi registers workflows and all 13 research commands; routes literal arguments', async () => {
  const commands = new Map();
  const messages = [];
  register({registerCommand: (name, handler) => commands.set(name, handler),
    sendUserMessage: (...args) => messages.push(args)});
  assert.equal(commands.size, 26);
  assert.equal(commands.has('autogoal'), false);
  assert.equal(commands.has('cron_autowork'), true);
  const raw = 'read-only\n$(literal); --no-push';
  await commands.get('ui_taste').handler(raw, {isIdle: () => true});
  assert.match(messages.at(-1)[0], /UI Taste/);
  assert.equal(messages.at(-1)[0].endsWith(raw), true);
  messages.length = 0;
  await commands.get('plan_with_me').handler(raw, {isIdle: () => true});
  assert.match(messages[0][0], /# Plan With Me/);
  assert.equal(messages[0][0].endsWith(raw), true);
  assert.equal(messages[0][1], undefined);
  await commands.get('autoresearch_debug').handler(raw, {isIdle: () => false});
  assert.match(messages[1][0], /Selected subcommand: debug/);
  assert.deepEqual(messages[1][1], {deliverAs: 'followUp'});
  await commands.get('grill_me').handler(raw, {isIdle: () => false});
  assert.match(messages.at(-1)[0], /# Plan With Me/);
  assert.match(messages.at(-1)[0], /Selected mode: challenge/);
  assert.equal(messages.at(-1)[0].endsWith(raw), true);
  assert.deepEqual(messages.at(-1)[1], {deliverAs: 'followUp'});
  const {readFile} = await import('node:fs/promises');
  const selectors = JSON.parse(await readFile(new URL('../skills/autoresearch/UPSTREAM.json', import.meta.url))).commands;
  assert.equal(selectors.length, 13);
  for (const selector of selectors) {
    await commands.get(`autoresearch_${selector}`).handler(raw, {isIdle: () => false});
    assert.match(messages.at(-1)[0], new RegExp(`Selected subcommand: ${selector}`));
    assert.equal(messages.at(-1)[0].endsWith(raw), true);
    assert.deepEqual(messages.at(-1)[1], {deliverAs: 'followUp'});
    await readFile(new URL(`../skills/autoresearch/upstream/${selector}.md`, import.meta.url));
  }
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
  assert.equal(paths.has('adapters/skills/grill-me/SKILL.md'), false);
  assert.equal(paths.has('adapters/skills/grill-me/PROTOCOL.md'), true);
  assert.equal([...paths].some(p => p.includes('__pycache__') || p.endsWith('.pyc')), false);
  for (const path of ['adapters/pi.mjs', 'adapters/skills/COMMON.md',
    'skills/docs-sync/scripts/goals.py', 'skills/autoresearch/upstream/plan.md', 'skills/impeccable/LICENSE']) {
    assert.equal(paths.has(path), true, path);
  }
});

test('installed archive resolves portable references and commands without checkout files', async () => {
  const {execFileSync} = await import('node:child_process');
  const {mkdtemp, readdir, readFile, rm, stat} = await import('node:fs/promises');
  const {tmpdir} = await import('node:os');
  const {join} = await import('node:path');
  const {fileURLToPath, pathToFileURL} = await import('node:url');
  const scratch = await mkdtemp(join(tmpdir(), 'portable-package-'));
  try {
    const root = fileURLToPath(new URL('../', import.meta.url));
    const archive = JSON.parse(execFileSync('npm', ['pack', '--json', '--pack-destination', scratch],
      {cwd: root, encoding: 'utf8'}))[0];
    execFileSync('tar', ['-xzf', join(scratch, archive.filename), '-C', scratch]);
    const installed = join(scratch, 'package');
    let skillCount = 0;
    const walk = async (dir) => {
      for (const entry of await readdir(dir, {withFileTypes: true})) {
        const path = join(dir, entry.name);
        if (entry.isDirectory()) await walk(path);
        else if (entry.name.endsWith('.md')) {
          if (entry.name === 'SKILL.md') skillCount++;
          const text = await readFile(path, 'utf8');
          for (const match of text.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)) {
            if (!match[1].includes('://') && !match[1].startsWith('#')) {
              await stat(fileURLToPath(new URL(match[1].split('#')[0], pathToFileURL(path))));
            }
          }
        }
      }
    };
    await walk(join(installed, 'adapters/skills'));
    assert.equal(skillCount, 12);
    const commands = new Map();
    const messages = [];
    const {default: installedRegister} = await import(pathToFileURL(join(installed, 'adapters/pi.mjs')));
    installedRegister({registerCommand: (name, handler) => commands.set(name, handler),
      sendUserMessage: (...args) => messages.push(args)});
    assert.equal(commands.size, 26);
    for (const [name, handler] of commands) {
      await handler.handler('read-only; $(literal)\nno push', {isIdle: () => false});
      assert.equal(messages.at(-1)[0].endsWith('read-only; $(literal)\nno push'), true, name);
      assert.deepEqual(messages.at(-1)[1], {deliverAs: 'followUp'});
    }
    for (const selector of JSON.parse(await readFile(join(installed, 'skills/autoresearch/UPSTREAM.json'))).commands) {
      await readFile(join(installed, `skills/autoresearch/upstream/${selector}.md`));
    }
  } finally {
    await rm(scratch, {recursive: true, force: true});
  }
});
