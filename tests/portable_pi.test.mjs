import assert from 'node:assert/strict';
import test from 'node:test';
import register from '../adapters/pi.mjs';

test('Pi registers workflows and all 13 research commands; routes literal arguments', async () => {
  const commands = new Map();
  const messages = [];
  register({registerCommand: (name, handler) => commands.set(name, handler),
    sendUserMessage: (...args) => messages.push(args)});
  assert.equal(commands.size, 40);
  assert.equal(commands.has('apk-get'), true);
  assert.equal(commands.has('autogoal'), false);
  for (const name of commands.keys()) assert.match(name, /^[a-z0-9]+(?:-[a-z0-9]+)*$/, name);
  assert.equal(commands.has('cron-autowork'), true);
  const {readFile} = await import('node:fs/promises');
  const {fileURLToPath} = await import('node:url');
  const assertWorkflow = async (skill) => {
    const source = new URL(`../adapters/skills/${skill}/SKILL.md`, import.meta.url);
    const message = messages.at(-1)[0];
    assert.equal(message.includes(`Source: ${fileURLToPath(source)}\n`), true, skill);
    assert.equal(message.includes(await readFile(source, 'utf8')), true, skill);
    assert.equal(message.includes('(../COMMON.md)'), true, skill);
  };
  const raw = 'read-only\n$(literal); --no-push';
  await commands.get('ui-taste').handler(raw, {isIdle: () => true});
  await assertWorkflow('ui-taste');
  assert.equal(messages.at(-1)[0].endsWith(raw), true);
  messages.length = 0;
  await commands.get('plan-with-me').handler(raw, {isIdle: () => true});
  await assertWorkflow('plan-with-me');
  assert.equal(messages[0][0].endsWith(raw), true);
  assert.equal(messages[0][1], undefined);
  messages.length = 0;
  await commands.get('plan-for-me').handler('', {isIdle: () => true});
  assert.match(messages[0][0], /Selected route: autonomous project discovery/);
  assert.match(messages[0][0], /Do not ask for a goal/);
  await commands.get('plan-for-me').handler('implement offline support', {isIdle: () => true});
  assert.equal(messages[1][0].includes('Selected route: autonomous project discovery'), false);
  assert.equal(messages[1][0].endsWith('implement offline support'), true);
  messages.length = 0;
  await commands.get('autoresearch-debug').handler(raw, {isIdle: () => false});
  assert.match(messages[0][0], /Selected subcommand: debug/);
  assert.deepEqual(messages[0][1], {deliverAs: 'followUp'});
  // The actual shared boundary is loaded, not just command registration/skill metadata.
  const boundary = await readFile(new URL('../skills/shared/RESEARCH-PLAN.md', import.meta.url), 'utf8');
  for (const name of ['plan-with-me', 'plan-for-me', 'grill-me', 'autoresearch-plan']) {
    await commands.get(name).handler(raw, {isIdle: () => true});
    assert.equal(messages.at(-1)[0].includes(boundary), true, name);
    assert.equal(messages.at(-1)[0].endsWith(raw), true, name);
  }
  await commands.get('autoresearch').handler(`plan ${raw}`, {isIdle: () => true});
  assert.equal(messages.at(-1)[0].includes(boundary), true);
  assert.equal(messages.at(-1)[0].endsWith(`plan ${raw}`), true);
  await commands.get('grill-me').handler(raw, {isIdle: () => false});
  await assertWorkflow('plan-with-me');
  assert.match(messages.at(-1)[0], /Selected mode: challenge/);
  assert.equal(messages.at(-1)[0].endsWith(raw), true);
  assert.deepEqual(messages.at(-1)[1], {deliverAs: 'followUp'});
  const selectors = JSON.parse(await readFile(new URL('../skills/autoresearch/UPSTREAM.json', import.meta.url))).commands;
  assert.equal(selectors.length, 13);
  for (const selector of selectors) {
    await commands.get(`autoresearch-${selector}`).handler(raw, {isIdle: () => false});
    assert.match(messages.at(-1)[0], new RegExp(`Selected subcommand: ${selector}`));
    assert.equal(messages.at(-1)[0].endsWith(raw), true);
    assert.deepEqual(messages.at(-1)[1], {deliverAs: 'followUp'});
    await readFile(new URL(`../skills/autoresearch/upstream/${selector}.md`, import.meta.url));
  }
  for (const [name, skill] of Object.entries({
    'plan-with-me': 'plan-with-me', 'plan-for-me': 'plan-for-me', 'docs-sync': 'docs-sync',
    'cron-autowork': 'cron-autowork', autowork: 'autowork', autoresearch: 'autoresearch',
    engineering: 'engineering', impeccable: 'impeccable', 'ui-taste': 'ui-taste',
    'beautify-github-readme': 'beautify-github-readme', 'grill-me': 'plan-with-me',
    lgtm: 'lgtm', blockers: 'blockers', 'git-commit-push': 'git-commit-push',
    ponytail: 'ponytail', 'ponytail-review': 'ponytail-review', 'ponytail-audit': 'ponytail-audit',
    'ponytail-debt': 'ponytail-debt', 'ponytail-gain': 'ponytail-gain', 'ponytail-help': 'ponytail-help',
    'bug-harvest': 'bug-harvest', 'autonomous-codebase-improver': 'autonomous-codebase-improver',
    'skill-folder-refactor': 'skill-folder-refactor', 'unused-code': 'unused-code',
    'test-optimizer': 'test-optimizer', 'apk-get': 'apk-get', graphify: 'graphify',
    ...Object.fromEntries(selectors.map(selector => [`autoresearch-${selector}`, 'autoresearch'])),
  })) {
    await commands.get(name).handler('questions only', {isIdle: () => true});
    await assertWorkflow(skill);
  }
});

test('APK Get accepts a bare invocation without requiring an app path', async () => {
  const commands = new Map();
  const messages = [];
  register({registerCommand: (name, handler) => commands.set(name, handler),
    sendUserMessage: message => messages.push(message)});
  await commands.get('apk-get').handler('', {isIdle: () => true});
  assert.equal(messages.length, 1);
  assert.equal(messages[0].endsWith('User request (preserve scope and restrictions):\n'), true);
  const {readFile} = await import('node:fs/promises');
  const adapter = await readFile(new URL('../adapters/skills/apk-get/SKILL.md', import.meta.url), 'utf8');
  assert.equal(messages[0].includes(adapter), true);
});

test('npm package excludes local bytecode and keeps portable support files', async () => {
  const {execFileSync} = await import('node:child_process');
  const {fileURLToPath} = await import('node:url');
  const root = fileURLToPath(new URL('../', import.meta.url));
  const packed = JSON.parse(execFileSync('npm', ['pack', '--ignore-scripts', '--offline', '--dry-run', '--json'], {cwd: root, encoding: 'utf8'}))[0];
  const paths = new Set(packed.files.map(f => f.path));
  assert.equal(paths.has('adapters/skills/grill-me/SKILL.md'), false);
  assert.equal(paths.has('adapters/skills/grill-me/PROTOCOL.md'), true);
  assert.equal([...paths].some(p => p.includes('__pycache__') || p.endsWith('.pyc')), false);
  assert.equal([...paths].some(p => p.startsWith('Src/autowork_runtime/')), false);
  for (const path of ['adapters/pi.mjs', 'adapters/skills/COMMON.md',
    'skills/docs-sync/scripts/docs.py', 'skills/autoresearch/upstream/plan.md', 'skills/impeccable/LICENSE',
    'skills/test-optimizer/SKILL.md', 'skills/engineering/local/test-suite-optimization/PROTOCOL.md',
    'skills/apk-get/SKILL.md', 'skills/apk-get/BUILD.md', 'skills/apk-get/scripts/verify_apk.py',
    'skills/shared/COMMUNICATION.md',
    'autowork_bootstrap.py', 'Src/autowork_bootstrap.py', 'Src/pi_autowork/__init__.py']) {
    assert.equal(paths.has(path), true, path);
  }
});

test('installed archive resolves portable references and commands without checkout files', async () => {
  const {execFileSync} = await import('node:child_process');
  const {cp, mkdir, mkdtemp, readdir, readFile, rm, stat, writeFile} = await import('node:fs/promises');
  const {tmpdir} = await import('node:os');
  const {join} = await import('node:path');
  const {fileURLToPath, pathToFileURL} = await import('node:url');
  const scratch = await mkdtemp(join(tmpdir(), 'portable-package-'));
  try {
    const root = fileURLToPath(new URL('../', import.meta.url));
    // A private release fixture, not an install: include the declared resources and
    // sentinel future owners without redirecting any production public entry.
    const source = join(scratch, 'source');
    await mkdir(source);
    const manifest = JSON.parse(await readFile(join(root, 'package.json'), 'utf8'));
    for (const entry of ['package.json', ...manifest.files.filter(p => !p.startsWith('!'))]) {
      const target = join(source, entry);
      await mkdir(join(target, '..'), {recursive: true});
      // npm's include list may retain optional paths absent in this release.
      try { await cp(join(root, entry), target, {recursive: true}); }
      catch (error) { if (error.code !== 'ENOENT') throw error; }
    }
    await mkdir(join(source, 'Src/autowork_runtime'), {recursive: true});
    await writeFile(join(source, 'Src/autowork_runtime/private.py'), 'raise RuntimeError("native payload")\n');
    await writeFile(join(source, 'Src/pi_autowork/fixture_reader.py'),
      'def _compat_main(argv): return len(argv)\n');
    const archive = JSON.parse(execFileSync('npm', ['pack', '--ignore-scripts', '--offline', '--json', '--pack-destination', scratch],
      {cwd: source, encoding: 'utf8'}))[0];
    assert.equal(archive.files.some(f => f.path.startsWith('Src/autowork_runtime/')), false);
    execFileSync('tar', ['-xzf', join(scratch, archive.filename), '-C', scratch]);
    const installed = join(scratch, 'package');
    const pythonEnv = {...process.env, PYTHONDONTWRITEBYTECODE: '1', PYTHONPATH: installed};
    const probe = code => execFileSync('python3', ['-B', '-c', code],
      {cwd: installed, env: pythonEnv, encoding: 'utf8'});
    probe('from pathlib import Path\nimport autowork_bootstrap as b\nassert b.run(Path.cwd(), "pi_autowork.fixture_reader", ["read"]) == 1\n');
    const help = execFileSync('python3', ['pi-autowork/pi_autowork/command.py', '--help'],
      {cwd: installed, env: pythonEnv, encoding: 'utf8'});
    assert.match(help, /tasks/);
    const readOnly = JSON.parse(execFileSync('python3', ['pi-autowork/pi_autowork/command.py', 'capabilities'],
      {cwd: installed, env: pythonEnv, encoding: 'utf8'}));
    assert.equal(readOnly.release, null);
    assert.equal(readOnly.commands.includes('tasks'), true);
    // Reading an archive is not immutable runner qualification: pinning still
    // needs a committed Git toolset. A fixture never manufactures that evidence.
    probe('import sys\nfrom pathlib import Path\nsys.path.insert(0, "pi-autowork")\nfrom pi_autowork import release\ntry:\n release.prepare(Path("pin-state"), Path.cwd())\nexcept RuntimeError as e:\n assert "committed toolset release" in str(e), str(e)\nelse:\n raise AssertionError("archive accepted as committed runner")\n');
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
    assert.equal(skillCount, 27);
    // Execute the packaged CommonJS helper under Autowork's ESM package boundary.
    const mapScript = join(installed, 'skills/ponytail/upstream/scripts/ponytail-map.cjs');
    const map = execFileSync('node', [mapScript, installed], {encoding: 'utf8'});
    assert.match(map, /Codebase map/);
    for (const skill of ['ponytail', 'bug-harvest', 'autonomous-codebase-improver',
      'skill-folder-refactor', 'unused-code']) {
      const pin = JSON.parse(await readFile(join(installed, `skills/${skill}/UPSTREAM.json`)));
      for (const resource of Object.values(pin.files)) {
        await stat(join(installed, `skills/${skill}`, resource.path));
      }
    }
    const commands = new Map();
    const messages = [];
    const {default: installedRegister} = await import(pathToFileURL(join(installed, 'adapters/pi.mjs')));
    installedRegister({registerCommand: (name, handler) => commands.set(name, handler),
      sendUserMessage: (...args) => messages.push(args)});
    assert.equal(commands.size, 40);
    assert.equal(commands.has('apk-get'), true);
    for (const [name, handler] of commands) {
      assert.match(name, /^[a-z0-9]+(?:-[a-z0-9]+)*$/, name);
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
