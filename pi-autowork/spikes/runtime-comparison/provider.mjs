// Test-only Pi extension: deterministic provider and tools, never installed.
import { appendFileSync, existsSync, writeFileSync } from 'node:fs';
import { setTimeout as delay } from 'node:timers/promises';
import { join } from 'node:path';
import { fixtureFrom, model, parameters, stream, tool } from './fixture.mjs';

export default function(pi) {
  pi.registerProvider('offline', { apiKey: 'fixture-not-a-secret', api: model.api,
    models: [model], streamSimple: stream });
  for (const safe of [true, false]) pi.registerTool({
    name: safe ? 'fixture_safe' : 'fixture_unsafe', label: 'fixture',
    description: 'Offline comparison fixture only', parameters,
    async execute(_id, args, signal, _update, ctx) {
      return { content: [{ type: 'text', text: await tool(args, ctx.cwd, signal) }], details: {} };
    },
  });
  let continued = false;
  for (const type of ['agent_end', 'agent_settled']) pi.on(type, (_event, ctx) => {
    appendFileSync(join(ctx.cwd, '.fixture-events'), type + '\n');
  });
  pi.on('agent_before_settle', async (_event, ctx) => {
    if (!continued && fixtureFrom(ctx.sessionManager.buildSessionContext().messages).op === 'settle') {
      continued = true;
      writeFileSync(join(ctx.cwd, '.fixture-before-settle'), 'waiting');
      while (!existsSync(join(ctx.cwd, '.fixture-settle-release'))) await delay(20, undefined, { signal: ctx.signal });
      return { continue: true, entries: [{ type: 'custom_message', customType: 'fixture-continuation',
        content: 'FIXTURE_JSON:' + JSON.stringify(fixtureFrom(ctx.sessionManager.buildSessionContext().messages)),
        display: false }] };
    }
  });
}
