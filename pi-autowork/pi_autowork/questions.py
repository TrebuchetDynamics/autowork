"""The owner's questions, kept by the runner in the repository's BLOCKERS.md.

Owner direction (2026-10-16): the owner only plans and answers; questions live in the
repository, never in a chat. Each cycle the runner turns what holds its queue into a
fixed set of questions, without a model: held tasks no attempt can finish, claims that
will not be adopted, TODO entries the engine will not run, outside conditions and
dependency cycles. They live under BLOCKERS.md's `## Active`, between

    <!-- pi-autowork:questions:start -->
    <!-- pi-autowork:questions:end -->

and nothing outside those markers changes. `/blockers` reads this block to
resolve them with the owner, easiest first; an answered question leaves the block when
its cause is gone (Git history keeps it).
"""
from datetime import datetime, timezone
import re

START = '<!-- pi-autowork:questions:start -->'
END = '<!-- pi-autowork:questions:end -->'
EFFORT_ORDER = ('quick', 'decision', 'input', 'investigate')
INPUT_CAUSES = ('blocker', 'scope_request', 'scope')


def _title(todo, task, goals):
    try:
        bodies = goals.task_bodies(todo).get(task) or []
    except (ValueError, AttributeError):
        bodies = []
    if not bodies:
        return ''
    first = bodies[0][0].splitlines()[0]
    first = re.sub(r'^[-*]\s+\[[ xX]\]\s+', '', first).strip().strip('*')
    return re.sub(r'^(?:`?' + re.escape(task) + r'`?)?\s*[—–:-]\s*', '', first).strip(' *')


def exhausted(row):
    """A held task the runner will not retry: a person must answer."""
    return row.get('state') == 'held' and (int(row.get('attempt') or 0) >= 2 or row.get('cause') in INPUT_CAUSES)


def build(snapshot, todo, goals):
    """Questions from an engine status snapshot, without a model: dicts sorted easiest first."""
    rows = {r.get('task'): r for r in snapshot.get('tasks') or [] if r.get('task')}
    roots = {r['id']: r for r in snapshot.get('roots') or []}
    found = {}

    def add(qid, kind, effort, needs, answer, task_line, unblocks):
        found[qid] = dict(id=qid, type='USER_INPUT' if effort == 'input' else 'USER_DECISION', effort=effort,
                          unblocks=unblocks, task=task_line, needs=' '.join(str(needs).split()), answer=answer,
                          kind=kind)

    for task, row in rows.items():
        if not exhausted(row):
            continue
        title = _title(todo, task, goals)
        line = f'{task} — {title}' if title else task
        blocks = (roots.get(task) or {}).get('blocks', 0)
        if row.get('cause') in INPUT_CAUSES:
            add(task, 'held', 'input', row.get('reason') or 'the worker stopped and asked for input', (
                f"Answer in {task}'s TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, "
                "or add a dated `Owner decision:` line. The runner reruns it when the entry changes."), line, blocks)
        else:
            add(task, 'held', 'investigate', row.get('reason') or 'held with no attempt left', (
                f"Read the evidence (the worker's report and validation log under .git/autowork-execution/"
                f"slot-data/{task}/), then rescope or split {task} in its TODO.md entry. The runner reruns it "
                "when the entry changes."), line, blocks)
    for qid, root in roots.items():
        kind, blocks = root.get('kind'), root.get('blocks', 0)
        if qid in found:
            continue
        title = _title(todo, qid, goals)
        line = f'{qid} — {title}' if title else qid
        if kind == 'claim':
            add(qid, kind, 'quick', f'{qid} is marked in_progress by another session and will not be adopted '
                f'automatically; {blocks} waiting task(s) depend on it.', (
                    f"If no one is working on {qid}, set `Status: open` in its TODO.md entry (the runner then "
                    "runs it); otherwise note who holds it and when it will be done."), line, blocks)
        elif kind == 'cycle':
            add(qid, kind, 'quick', f'{qid} is part of a dependency cycle.', (
                f"Cut one dependency in the cycle: edit the `Dependencies:` line of {qid} or of the task it "
                "waits on."), line, blocks)
        elif kind == 'contract':
            row = rows.get(qid) or {}
            add(qid, kind, 'decision', row.get('reason') or 'its TODO entry is not runnable as written', (
                f"Fix {qid}'s TODO.md entry as the reason says (for example add the missing Scope, Acceptance "
                "or Checks field), or move it out of Now/Next."), line, blocks)
        elif kind == 'outside':
            add(qid, kind, 'decision', f'{blocks} waiting task(s) depend on "{qid}", which is not a Now/Next task '
                '(an outside condition, or a task in Needs decision).', (
                    'Decide it: record the decision in the dependent tasks\' `Dependencies:` lines, or move the '
                    'task that owns it into Now or Next.'), qid if not title else line, blocks)
    order = {e: i for i, e in enumerate(EFFORT_ORDER)}
    return sorted(found.values(), key=lambda q: (order[q['effort']], -q['unblocks'], q['id']))


def previous_since(text):
    """{question id: Since} from an existing block, so a question keeps its first time."""
    block = block_of(text)
    since, current = {}, None
    for line in (block or '').splitlines():
        head = re.match(r'^### Q-(.+?) — ', line)
        if head:
            current = head[1]
        elif current and line.startswith('- Since: '):
            since[current] = line[len('- Since: '):].strip()
    return since


def block_of(text):
    if START in text and END in text and text.index(START) < text.index(END):
        return text[text.index(START) + len(START):text.index(END)]
    return None


def render(questions, since):
    lines = [START, '']
    for q in questions:
        lines += [f"### Q-{q['id']} — {q['type']} — effort {q['effort']} — unblocks {q['unblocks']}", '',
                  f"- Task: {q['task']}", f"- Needs: {q['needs']}", f"- Since: {since.get(q['id'])}",
                  f"- Answer: {q['answer']}", '']
    lines.append(END)
    return '\n'.join(lines)


def update(text, questions, now=None):
    """BLOCKERS.md text with the questions block rewritten; everything else unchanged."""
    if not questions and block_of(text or '') is None:
        return text  # nothing to ask and no block yet: leave the file alone
    stamp = (now or datetime.now(timezone.utc)).strftime('%Y-%m-%dT%H:%M:%SZ')
    known = previous_since(text or '')
    since = {q['id']: known.get(q['id'], stamp) for q in questions}
    block = render(questions, since)
    if not text:
        return f'# Blockers\n\n## Active\n\n{block}\n'
    if block_of(text) is not None:
        start, end = text.index(START), text.index(END) + len(END)
        return text[:start] + block + text[end:]
    active = re.search(r'^## Active[ \t]*\n', text, re.M)
    if active:
        return text[:active.end()] + '\n' + block + '\n' + text[active.end():]
    return text.rstrip('\n') + '\n\n## Active\n\n' + block + '\n'
