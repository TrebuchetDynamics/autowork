"""The owner's questions, kept by the runner in the repository's BLOCKERS.md.

Owner direction (2026-10-16): the owner only plans and answers; questions live in the
repository, never in a chat. Each cycle the runner turns what holds its queue into a
fixed set of questions, without a model: held tasks whose resolution genuinely requires owner
input, task records the engine will not run as their records state them, outside conditions and
dependency cycles. A technical hold remains a visible engineering incident even after its
bounded repair or recovery budget ends; it is never relabelled as an owner decision. They live
under BLOCKERS.md's `## Active`, between

    <!-- pi-autowork:questions:start -->
    <!-- pi-autowork:questions:end -->

and nothing outside those markers changes. `/blockers` reads this block to
resolve them with the owner, easiest first; an answered question leaves the block when
its cause is gone (Git history keeps it).
"""
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
import failure_policy  # noqa: E402

START = '<!-- pi-autowork:questions:start -->'
END = '<!-- pi-autowork:questions:end -->'
EFFORT_ORDER = ('quick', 'decision', 'input', 'investigate')
INPUT_CAUSES = ('blocker', 'scope_request', 'scope')


def _one_line(value):
    return ' '.join(str(value).split())


def _question_id(value):
    text = _one_line(value)
    if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', text):
        return text
    return 'COND-' + sha1(text.encode('utf-8'), usedforsecurity=False).hexdigest()[:8]


def _store(repo):
    """The task store at the repository's HEAD, or None when it cannot be read."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
    import task_queue
    try:
        return task_queue, task_queue.store(Path(repo))
    except task_queue.StoreError:
        return task_queue, None


def technical(row):
    """A failure an agent or the engine can act on. The shared policy owns the boundary;
    a failed review, a dead worker or a merge conflict never becomes an owner decision merely
    because its retry budget ran out."""
    if 'owner_decision_required' in row:  # the status row already carries the slot's classification
        return not row['owner_decision_required']
    return failure_policy.technical(row.get('cause'), row.get('reason'))


def exhausted(row):
    """A held task the runner will not retry on its own. Only an owner-owned hold becomes a
    question; an exhausted technical hold stays a visible engineering incident."""
    if technical(row):
        return False
    adoption = row.get('merge_adoption') or {}
    return row.get('state') == 'held' and (int(row.get('attempt') or 0) >= 2 or row.get('cause') in INPUT_CAUSES
                                          or adoption.get('allowed') is False or bool(adoption.get('merged_count'))
                                          or bool(row.get('quick_hold'))
                                          # the status row says a person owns it (a used report resume)
                                          or bool(row.get('owner_decision_required')))


def build(snapshot, repo, repairs=(), resolving=(), *, now=None):
    """Questions from an engine status snapshot and the task store at ``repo``'s HEAD, without a
    model: dicts sorted easiest first.
    ``resolving`` names held conflicts the runner's merge resolver still settles by itself: seven
    such holds were posted as owner questions while three resolvers were clearing them."""
    now = datetime.now(timezone.utc).timestamp() if now is None else now
    rows = {r.get('task'): r for r in snapshot.get('tasks') or [] if r.get('task')}
    roots = {r['id']: r for r in snapshot.get('roots') or []}
    found = {}
    task_queue, store = _store(repo)
    deferred = task_queue.deferred(store) if store else set()

    def title_of(task):
        record = store.tasks.get(task) if store else None
        return record.title if record else ''

    def add(qid, kind, effort, needs, answer, task_line, unblocks):
        qid = _question_id(qid)
        found[qid] = dict(id=qid, type='USER_INPUT' if effort == 'input' else 'USER_DECISION', effort=effort,
                          unblocks=unblocks, task=_one_line(task_line), needs=_one_line(needs),
                          answer=_one_line(answer), kind=kind)

    if snapshot.get('ledger_errors'):
        add('LEDGER', 'ledger', 'investigate',
            'invalid task store: ' + '; '.join(snapshot['ledger_errors']),
            'DOCS-MAINTAINER could not repair the task store. Read the errors above (each names a file '
            'and line) and its run record under the runner state directory (maintainer.json); fix those '
            'task or goal files, then run `autowork tasks validate --worktree`.',
            'LEDGER — task store validation', len(rows))

    for task, row in rows.items():
        hold = row.get('quick_hold')
        if row.get('state') != 'held' or not hold:
            continue
        title = title_of(task)
        attempts = ', '.join(
            f"{a['attempt']}: {a['seconds']:.0f}s "
            f"(held {datetime.fromtimestamp(a['held_at'], timezone.utc):%Y-%m-%d %H:%M:%S UTC})"
            for a in hold['attempts'])
        add(task, 'quick_hold', 'input',
            f"Repeated quick hold: {hold['reason']}; attempts {attempts}. Automatic reruns stopped.",
            f"Produce the missing input (add its producer task and dependency), or move {task} to Needs decision. "
            f"To rerun, add the note `Blocker resolution: {hold['fingerprint']}; <producer task or decision "
            f"evidence>` to tasks/items/{task}.md. Other edits to the record do not answer this blocker.",
            f'{task} — {title}' if title else task, (roots.get(task) or {}).get('blocks', 0))

    for repair in repairs:
        task = repair['task']
        if task in found:
            continue
        title = title_of(task)
        add(task, 'maintainer', 'decision',
            f"{repair['reason']}; DOCS-MAINTAINER already changed {', '.join(repair['fields'])}, "
            'but the task is still waiting for the same reason.',
            f"Decide the missing input or disposition in tasks/items/{task}.md, or move it to Needs decision. "
            'The maintainer will not repeat this repair unless the record or waiting reason changes.',
            f'{task} — {title}' if title else task, (roots.get(task) or {}).get('blocks', 0))

    for task, row in rows.items():
        if task in found or task in resolving:
            continue
        waits = row.get('waits_for') if row.get('state') == 'held' else None
        if waits:
            since = row.get('wait_since')
            if technical(row) or since is None or now - since < 24 * 3600:
                continue
        elif not exhausted(row):
            continue
        title = title_of(task)
        line = f'{task} — {title}' if title else task
        blocks = (roots.get(task) or {}).get('blocks', 0)
        if waits:
            add(task, 'held', 'input', 'Waiting for ' + ', '.join(waits) + ' to land for at least 24 hours. ' +
                (row.get('reason') or ''),
                'Inspect the prerequisite tasks and resolve their holds or close them with verified evidence. '
                'The runner resumes this task on the same attempt when all prerequisites close.', line, blocks)
        elif row.get('cause') in INPUT_CAUSES:
            add(task, 'held', 'input', row.get('reason') or 'the worker stopped and asked for input', (
                f"Answer in tasks/items/{task}.md: widen `touches`, supply the input, narrow the acceptance, "
                "or add a dated `Owner decision:` note. The runner reruns it when the record changes."), line, blocks)
        else:
            add(task, 'held', 'investigate', row.get('reason') or 'held with no attempt left', (
                f"Read the evidence (the worker's report and validation log under .git/autowork-execution/"
                f"slot-data/{task}/), then rescope or split {task} in tasks/items/{task}.md. The runner reruns "
                "it when the record changes."), line, blocks)
    for qid, root in roots.items():
        kind, blocks = root.get('kind'), root.get('blocks', 0)
        if _question_id(qid) in found:
            continue
        title = title_of(qid)
        line = f'{qid} — {title}' if title else qid
        if kind == 'claim':
            continue  # its `Held by:` note is the answer; `autowork tasks release` lifts it
        elif kind == 'cycle':
            add(qid, kind, 'quick', f'{qid} is part of a dependency cycle.', (
                f"Cut one dependency in the cycle: edit `depends_on` in tasks/items/{qid}.md or in the record "
                "of the task it waits on."), line, blocks)
        elif kind == 'contract':
            row = rows.get(qid) or {}
            add(qid, kind, 'decision', row.get('reason') or 'its task record is not runnable as written', (
                f"Fix tasks/items/{qid}.md as the reason says (for example add the missing scope, acceptance "
                "or checks), or move it out of Now/Next."), line, blocks)
        elif kind == 'outside':
            if qid.startswith('Live authorization: '):
                task = qid.removeprefix('Live authorization: ')
                if task not in found:
                    title = title_of(task)
                    add(task, kind, 'decision', f'{task} requires owner action or recorded live authorization; '
                        'an unattended runner cannot run it.', (
                            f'Run it yourself, set `live = "authorized"` in tasks/items/{task}.md with an '
                            '`Owner decision:` note (who authorized which live scope and when), or move it to '
                            'Needs decision. Only the owner grants it; a worker\'s edit to the record never does.'),
                        f'{task} — {title}' if title else task, blocks)
                continue
            if qid in deferred:
                continue  # the dated owner deferral is already the answer; its dependents wait
            add(qid, kind, 'decision', f'{blocks} waiting task(s) depend on "{qid}", which is not a Now/Next task '
                '(an outside condition, or a task in Needs decision).', (
                    'Decide it: record the decision in the dependent tasks\' `depends_on`, or move the '
                    'task that owns it into Now or Next. To defer it, keep that task in Needs decision with a dated '
                    '`Owner decision:` note; its dependents then wait without another question.'),
                qid if not title else line, blocks)
    order = {e: i for i, e in enumerate(EFFORT_ORDER)}
    return sorted(found.values(), key=lambda q: (order[q['effort']], -q['unblocks'], q['id']))


def full_check_question():
    """One question for a repository that declares no full check (TOOLSET-180-72)."""
    return dict(id='FULL-CHECK', type='USER_INPUT', effort='input', unblocks=0, kind='full_check',
                task='the repository\'s whole offline test suite',
                needs='no full-suite gate: a commit can land while breaking tests its own task never ran, '
                      'and main is never checked',
                answer='Add one line to AGENTS.md, `Full check: <command>` (the command that runs the whole '
                       'offline suite), or set PI_AUTOWORK_VALIDATE in the runner\'s settings.')


def update_planning(text, base=None):
    """Add/remove just the startup question, preserving other questions and owner prose."""
    block = block_of(text or '')
    if block is None:
        return update(text, [planning(base)]) if base else text
    kept = re.sub(r'^### Q-RUNNER-PLANNING — .*?(?=^### Q-|\Z)', '', block, flags=re.M | re.S)
    if base:
        stamp = previous_since(text).get('RUNNER-PLANNING') or datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        question = render([planning(base)], {'RUNNER-PLANNING': stamp})
        kept = block_of(question) + kept.lstrip('\n')
    return text[:text.index(START) + len(START)] + kept + text[text.index(END):]


def planning(base):
    """One actionable runner question before a committed plan can reach a session."""
    return dict(id='RUNNER-PLANNING', type='USER_INPUT', effort='quick', unblocks=0,
                task='Runner startup', kind='runner',
                needs=f'planning files are not committed on {base}',
                answer=f'commit tasks/ on {base} first. The runner resumes automatically; '
                       'it will not commit these files for you at startup.')


def previous_since(text):
    """{question id: Since} from an existing block, so a question keeps its first time."""
    block = block_of(text)
    since, current, heading = {}, None, None
    for line in (block or '').splitlines():
        if line.startswith('### '):
            current, heading = None, line
        elif heading is not None:
            if re.match(r'^- (?:Task|Needs|Since|Answer|Kind):', line):
                heading = None
            else:
                heading += ' ' + line
        elif current and line.startswith('- Since: '):
            since.setdefault(current, _one_line(line[len('- Since: '):]))
        if heading is not None:
            # Match the metadata suffix: legacy prose can wrap or contain an em dash.
            head = re.fullmatch(r'### Q-(.+?) — USER_(?:INPUT|DECISION) — effort \S+ — unblocks \S+',
                                _one_line(heading))
            if head:
                current, heading = _question_id(head[1]), None
    return since


def block_of(text):
    if START in text and END in text and text.index(START) < text.index(END):
        return text[text.index(START) + len(START):text.index(END)]
    return None


def render(questions, since):
    lines = [START, '']
    for question in questions:
        q = {key: _one_line(value) for key, value in question.items()}
        q['id'] = _question_id(q['id'])
        lines += [f"### Q-{q['id']} — {q['type']} — effort {q['effort']} — unblocks {q['unblocks']}", '',
                  f"- Task: {q['task']}", f"- Needs: {q['needs']}", f"- Since: {_one_line(since.get(q['id']))}",
                  f"- Answer: {q['answer']}", f"- Kind: {_one_line(question.get('kind') or 'other')}", '']
    lines.append(END)
    return '\n'.join(lines)


def update(text, questions, now=None):
    """BLOCKERS.md text with the questions block rewritten; everything else unchanged."""
    if not questions and block_of(text or '') is None:
        return text  # nothing to ask and no block yet: leave the file alone
    stamp = (now or datetime.now(timezone.utc)).strftime('%Y-%m-%dT%H:%M:%SZ')
    known = previous_since(text or '')
    since = {_question_id(q['id']): known.get(_question_id(q['id']), stamp) for q in questions}
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
