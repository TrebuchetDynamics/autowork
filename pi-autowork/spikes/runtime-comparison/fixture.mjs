// Deterministic model/tool double shared by ALL three real execution backends.
// No network, credentials, model-quality or external-effect guarantees.
import { appendFileSync, existsSync, writeFileSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';

export const parameters = { type: 'object', properties: { op: { type: 'string' },
  file: { type: 'string' }, value: { type: 'string' } }, required: ['op'], additionalProperties: false };
export const model = { id: 'fixture', modelId: 'fixture', provider: 'offline', api: 'offline-fixture',
  name: 'Offline fixture', baseUrl: 'http://invalid.invalid', reasoning: false,
  input: ['text'], contextWindow: 128000, maxTokens: 4096,
  cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 } };
const usage = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0,
  cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } };
export function fixtureFrom(messages) {
  const user = messages.findLast(m => m.role === 'user');
  const text = typeof user?.content === 'string' ? user.content
    : (user?.content ?? []).filter(p => p.type === 'text').map(p => p.text).join('\n');
  return JSON.parse(text.slice(text.indexOf('FIXTURE_JSON:') + 'FIXTURE_JSON:'.length).trim());
}
export function stream(_model, { messages }, options = {}) {
  const fixture = fixtureFrom(messages);
  const lastUser = messages.findLastIndex(m => m.role === 'user');
  const results = messages.slice(lastUser + 1).filter(m => m.role === 'toolResult');
  const content = results.length
    ? [{ type: 'text', text: JSON.stringify(results.map(r => ({ isError: r.isError, content: r.content }))) }]
    : [{ type: 'toolCall', id: 'fixture-call', name: fixture.safe ? 'fixture_safe' : 'fixture_unsafe',
         arguments: { op: fixture.op, ...(fixture.file ? { file: fixture.file } : {}),
           ...(fixture.value !== undefined ? { value: fixture.value } : {}) } }];
  const message = { role: 'assistant', api: model.api, provider: model.provider, model: model.id,
    timestamp: Date.now(), usage, stopReason: results.length ? 'stop' : 'toolUse', content };
  return {
    async *[Symbol.asyncIterator]() {
      if (options.signal?.aborted) {
        message.stopReason = 'aborted'; message.errorMessage = 'fixture cancelled';
        yield { type: 'error', reason: 'aborted', error: message }; return;
      }
      yield { type: 'start', partial: message };
      yield { type: 'done', reason: message.stopReason, message };
    },
    async result() { return message; },
  };
}
export async function tool(args, cwd, signal) {
  appendFileSync(join(cwd, '.fixture-calls'), args.op + '\n');
  writeFileSync(join(cwd, '.fixture-started'), String(process.pid));
  if (args.op === 'stubborn') {
    const child = spawn(process.execPath, ['-e', `const fs = require('fs');
      process.on('SIGTERM', () => {});
      fs.writeFileSync('.fixture-child', String(process.pid)); setInterval(() => {}, 1000);`],
      { cwd, stdio: 'ignore', detached: true });
    child.unref();
  }
  if (['wait', 'stubborn', 'replay'].includes(args.op)) {
    while (!existsSync(join(cwd, '.fixture-release'))) await delay(20, undefined, { signal });
  }
  if (args.file) writeFileSync(join(cwd, args.file), args.value);
  return 'fixture finished';
}
