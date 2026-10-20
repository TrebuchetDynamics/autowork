// Disposable upstream adapter process. Imports only explicitly supplied cache paths.
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { model, parameters, stream, tool } from './fixture.mjs';

const request = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const load = relative => import(pathToFileURL(join(request.config.modules, relative)).href);
const prompt = 'FIXTURE_JSON:' + JSON.stringify(request.fixture);
let result;
if (request.backend === 'agwab') {
  const api = await import(pathToFileURL(join(request.config.agwab, 'api.mjs')).href);
  const cancel = new AbortController();
  process.on('SIGTERM', () => cancel.abort());
  const envelope = await api.runSubagent({ backend: 'headless', task: prompt,
    cwd: request.cwd, workspace: 'shared', worktree: false, sandbox: false,
    noExtensions: true, extensions: [join(import.meta.dirname, 'provider.mjs')], skills: [],
    tools: ['fixture_safe', 'fixture_unsafe'], model: 'offline/fixture',
    sessionId: request.requestId, runsDir: join(request.cwd, '.runtime-agwab'),
    timeoutMs: 45000, signal: cancel.signal });
  result = { status: envelope.status, envelope };
} else {
  const { BACKGROUND_CONTEXT: ctx } = await load('@earendil-works/chord/dist/context/index.js');
  const { Harness, createRegistry, defineExtension, defineTool } = await load('@earendil-works/pi-durable/dist/index.js');
  const { openNodeJsonlStorage } = await load('@earendil-works/pi-durable/dist/storage/jsonl/node.js');
  const registry = createRegistry();
  registry.install(defineExtension({ name: 'comparison-fixture', tools: [true, false].map(safe => defineTool({
    name: safe ? 'fixture_safe' : 'fixture_unsafe', description: 'Offline fixture', parameters,
    replay: safe ? 'safe' : 'unsafe',
    async execute(args, _api, context) {
      return { output: [{ type: 'text', text: await tool(args, request.cwd, context.abortSignal) }] };
    },
  })) }));
  const models = { getModel: (provider, id) => provider === 'offline' && id === 'fixture' ? model : undefined,
    streamSimple: stream };
  const storage = await openNodeJsonlStorage(request.storage, ctx, { fsync: true });
  const harness = await Harness.open(storage, { models, registry,
    settings: { retry: { enabled: false }, compaction: { enabled: false } } }, ctx);
  try {
    const inspection = await harness.inspect(ctx);
    const root = await harness.root(ctx, { agent: { model: { provider: 'offline', modelId: 'fixture' },
      cwd: request.cwd } });
    if (request.resume) harness.resume();
    const submission = await root.submit({ type: 'input', content: prompt, requestId: request.requestId }, ctx);
    const duplicate = await root.submit({ type: 'input', content: prompt, requestId: request.requestId }, ctx);
    const settled = await submission.wait(ctx);
    // Read only committed context: no raw provider callback is exposed to Toolset.
    const context = await root.context(ctx);
    result = { status: settled.status === 'done' ? 'completed' : 'failed', settled,
      duplicate: submission.id === duplicate.id, inspection, messages: context.messages,
      entries: context.entries };
  } finally { await harness.close(ctx); }
}
writeFileSync(join(request.directory, 'bridge-result.json'), JSON.stringify(result));
