"""Bounded, synchronous projection of Pi 1.4 JSON/RPC session events.

Only message_end (assistant/toolResult) and compaction_end.result are usage
surfaces. Streaming snapshots, turn_end and agent_end are never accounting
inputs. Missing optional tool/compaction usage is unknown, not zero. Coverage
is conservative: interrupted work, unknown events and unreported summarization
retry attempts prevent a complete total. No catalog prices are used.

One instance covers one prompt through agent_settled, not a whole RPC session.
The caller owns framing and transport errors. No raw events, arguments, tool
output or thinking are retained. Outcome text/error are private; only progress()
is suitable for status publication. Overflow poisons the projection so stale
success cannot be returned. Identified tool/result replays are deduplicated;
Pi gives compaction events no replay ID, so transport replay is not supported.
"""
import math
import time


class ProjectionOverflow(ValueError):
    """Critical projection state would exceed its bound; fail the run closed."""


def _number(value):
    # Avoid converting arbitrarily large JSON integers to float.
    if type(value) not in (int, float) or not 0 <= value <= 1e300:
        return None
    return value if math.isfinite(value) else None


def _mapping(value):
    return value if isinstance(value, dict) else {}


class EventProjection:
    """Project decoded events; durations are seconds on the supplied clock.

    startup_seconds: construction to first agent_start; first_tool_seconds:
    construction to first tool start; tool_seconds: sum of known completed
    execution durations (overlap is counted, not wall time), or None until one
    is known. Observed start/end elapsed time is the fallback for durationMs.
    Fixed bounds: 4096 tool IDs and response IDs each, 1024 UTF-8 bytes per ID,
    256 bytes per tool name, 4096 bytes per error. Unknown types use one counter,
    never a dictionary of attacker-controlled names.
    """

    _MAX_ITEMS = 4096
    _IGNORED = frozenset(('session', 'turn_end', 'queue_update', 'entry_appended',
                          'session_info_changed', 'thinking_level_changed',
                          'bash_execution_update', 'extension_error', 'response',
                          'extension_ui_request'))

    def __init__(self, clock=time.monotonic, max_text_bytes=262144):
        if type(max_text_bytes) is not int or max_text_bytes < 0:
            raise ValueError('max_text_bytes must be a nonnegative integer')
        self._clock = clock
        self._created = clock()
        self._max_text_bytes = max_text_bytes
        self._overflow = False
        self._phase = 'starting'
        self._started = self._settled = self._aborted = False
        self._last_event_at = self._last_tool_at = None
        self._startup = self._first_tool = self._tool_seconds = None
        self._tools = {}
        self._responses = set()
        self._tool_count = 0
        self._assistant_open = self._compaction_open = False
        self._text = ''
        self._stop = self._error = self._retry_error = self._compaction_error = None
        self._retries = self._compactions = self._unreported_retries = 0
        self._unknown = self._malformed = 0
        self._surfaces = dict(assistant=0, tool=0, compaction=0)
        self._reported = self._missing = self._subscription = 0
        self._sums = dict(totalTokens=0, input=0, output=0, cost=0)
        self._known = dict.fromkeys(self._sums, 0)

    def _fail(self):
        self._overflow = True
        raise ProjectionOverflow('Pi event projection exceeded a critical state bound')

    def _check(self):
        if self._overflow:
            self._fail()

    def _increment(self, value, amount=1):
        result = value + amount
        if result > 2 ** 63 - 1:
            self._fail()
        return result

    def _string(self, value, bound):
        if not isinstance(value, str):
            return None
        # The character check avoids allocating an encoding of huge input.
        if len(value) > bound or len(value.encode('utf-8', errors='surrogatepass')) > bound:
            self._fail()
        return value

    def _tool(self, raw):
        identity = self._string(raw.get('toolCallId'), 1024)
        if not identity:
            self._malformed = self._increment(self._malformed)
            return None
        if identity not in self._tools:
            if len(self._tools) >= self._MAX_ITEMS:
                self._fail()
            self._tools[identity] = dict(name=None, start=None, ended=False,
                                         execution=False, usage=False, nested=False)
        return self._tools[identity]

    def _add_usage(self, surface, raw):
        self._surfaces[surface] = self._increment(self._surfaces[surface])
        u = _mapping(raw)
        if u:
            self._reported = self._increment(self._reported)
        else:
            self._missing = self._increment(self._missing)
        self._subscription += u.get('billing') == 'subscription'
        for field in self._sums:
            if field == 'cost':
                value = (_number(_mapping(u.get('cost')).get('total'))
                         if u.get('cost_source') == 'provider_reported'
                         and u.get('billing') != 'subscription' else None)
            else:
                value = _number(u.get(field))
            if value is not None:
                total = self._sums[field] + value
                if _number(total) is None:
                    self._fail()
                self._sums[field] = total
                self._known[field] = self._increment(self._known[field])

    def _message_end(self, raw):
        message = _mapping(raw.get('message'))
        role = message.get('role')
        if role == 'assistant':
            identity = self._string(message.get('responseId'), 1024)
            if identity:
                if identity in self._responses:
                    return
                if len(self._responses) >= self._MAX_ITEMS:
                    self._fail()
                self._responses.add(identity)
            self._assistant_open = False
            self._add_usage('assistant', message.get('usage'))
            self._stop = self._string(message.get('stopReason'), 256)
            self._error = self._string(message.get('errorMessage'), 4096)
            self._retry_error = self._compaction_error = None
            pieces, size = [], 0
            content = message.get('content')
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict) or block.get('type') != 'text':
                        continue
                    text = self._string(block.get('text'), self._max_text_bytes)
                    if text is None:
                        continue
                    size += len(text.encode('utf-8', errors='surrogatepass')) + bool(pieces)
                    if size > self._max_text_bytes:
                        self._fail()
                    pieces.append(text)
            self._text = '\n'.join(pieces)
        elif role == 'toolResult':
            tool = self._tool(message)
            if tool is not None:
                if tool['usage']:
                    return
                tool['usage'] = True
            self._add_usage('tool', message.get('usage'))
        elif not isinstance(role, str):
            self._malformed = self._increment(self._malformed)

    def consume(self, raw: dict):
        """Consume immediately, retaining only bounded scalar/accounting state."""
        self._check()
        now = self._clock()
        self._last_event_at = now
        raw = _mapping(raw)
        kind = raw.get('type')
        if not isinstance(kind, str):
            self._unknown = self._increment(self._unknown)
            return
        if kind == 'agent_settled':
            self._settled = True
            self._aborted = raw.get('aborted') is True
            self._phase = 'settled'
        elif kind == 'agent_start':
            if not self._started:
                self._startup = max(0, now - self._created)
            self._started = True
            self._phase = 'model'
        elif kind == 'agent_end':
            self._phase = 'continuing'
        elif kind == 'turn_start':
            self._phase = 'model'
        elif kind == 'message_start':
            if _mapping(raw.get('message')).get('role') == 'assistant':
                self._assistant_open = True
                self._phase = 'model'
        elif kind == 'message_update':
            self._assistant_open = True
            self._phase = 'model'
        elif kind == 'message_end':
            self._message_end(raw)
        elif kind in ('tool_execution_start', 'tool_execution_update', 'tool_execution_end'):
            self._last_tool_at = now
            tool = self._tool(raw)
            if tool is None:
                return
            if not tool['execution']:
                tool['execution'] = True
                self._tool_count = self._increment(self._tool_count)
            tool['nested'] = tool['nested'] or bool(raw.get('parentToolCallId'))
            name = self._string(raw.get('toolName'), 256)
            if name is not None:
                tool['name'] = name
            if kind == 'tool_execution_start' and tool['start'] is None and not tool['ended']:
                tool['start'] = now
                if self._first_tool is None:
                    self._first_tool = max(0, now - self._created)
            if kind == 'tool_execution_end' and not tool['ended']:
                tool['ended'] = True
                duration = _number(raw.get('durationMs'))
                duration = (duration / 1000 if duration is not None else
                            max(0, now - tool['start']) if tool['start'] is not None else None)
                if duration is not None:
                    total = (self._tool_seconds or 0) + duration
                    if _number(total) is None:
                        self._fail()
                    self._tool_seconds = total
            self._phase = 'tool' if any(t['execution'] and not t['ended']
                                        for t in self._tools.values()) else 'model'
        elif kind == 'compaction_start':
            self._compactions = self._increment(self._compactions)
            self._compaction_open = True
            self._phase = 'compacting'
        elif kind == 'compaction_end':
            if not self._compaction_open:
                self._compactions = self._increment(self._compactions)
            self._compaction_open = False
            self._add_usage('compaction', _mapping(raw.get('result')).get('usage'))
            self._compaction_error = self._string(raw.get('errorMessage'), 4096)
            if raw.get('willRetry') is True:
                self._retries = self._increment(self._retries)
            self._phase = 'continuing'
        elif kind in ('auto_retry_start', 'summarization_retry_scheduled'):
            self._retries = self._increment(self._retries)
            if kind == 'summarization_retry_scheduled':
                self._unreported_retries = self._increment(self._unreported_retries)
            self._phase = 'retrying'
        elif kind == 'auto_retry_end':
            if raw.get('success') is False:
                self._retry_error = self._string(raw.get('finalError'), 4096)
            self._phase = 'continuing'
        elif kind == 'summarization_retry_attempt_start':
            self._phase = 'compacting' if raw.get('source') == 'compaction' else 'summarizing'
        elif kind == 'summarization_retry_finished':
            self._phase = 'compacting' if self._compaction_open else 'continuing'
        elif kind not in self._IGNORED:
            self._unknown = self._increment(self._unknown)

    def progress(self) -> dict:
        """Privacy-safe status: no arguments, messages, errors, IDs or results."""
        active = [t for t in self._tools.values() if t['execution'] and not t['ended']]
        return dict(phase='overflow' if self._overflow else self._phase,
                    last_event_at=self._last_event_at, last_tool_at=self._last_tool_at,
                    current_tool=active[-1]['name'] if active else None,
                    tool_count=self._tool_count, active_tool_count=len(active),
                    started=self._started, settled=self._settled,
                    retries=self._retries, compactions=self._compactions)

    def outcome(self) -> dict:
        """Private run-compatible result with explicit conservative usage coverage."""
        self._check()
        count = sum(self._surfaces.values())
        pending = int(self._assistant_open) + int(self._compaction_open)
        pending += sum(t['execution'] and not t['nested'] and not t['usage']
                       for t in self._tools.values())
        covered = bool(count and self._settled and not (
            pending or self._unknown or self._malformed or self._unreported_retries))
        complete = {field: covered and self._known[field] == count for field in self._sums}
        coverage = dict(surfaces=dict(self._surfaces), reported=self._reported,
                        missing=self._missing, pending=pending,
                        unreported_retries=self._unreported_retries,
                        unknown_events=self._unknown, malformed_events=self._malformed,
                        complete=all(complete.values()), tokens_complete=complete['totalTokens'],
                        input_tokens_complete=complete['input'], output_tokens_complete=complete['output'],
                        cost_complete=complete['cost'])
        return dict(settled=self._settled, aborted=self._aborted, stop=self._stop,
                    error=self._error or self._retry_error or self._compaction_error,
                    retries=self._retries, compactions=self._compactions,
                    tokens=self._sums['totalTokens'] if complete['totalTokens'] else None,
                    input_tokens=self._sums['input'] if complete['input'] else None,
                    output_tokens=self._sums['output'] if complete['output'] else None,
                    cost=self._sums['cost'] if complete['cost'] else None,
                    measured_cost_usd=self._sums['cost'],
                    cost_source='provider_reported' if self._known['cost'] else 'missing',
                    billing=('subscription' if count and self._subscription == count else
                             'mixed' if self._subscription else None),
                    text=self._text, usage_coverage=coverage, unknown_events=self._unknown,
                    startup_seconds=self._startup, first_tool_seconds=self._first_tool,
                    tool_seconds=self._tool_seconds)
