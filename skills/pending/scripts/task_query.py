#!/usr/bin/env python3
"""Read-only repository task queries. See ../references/query-contract.md."""
import sys

# Loading bundled pure parsers must not create files in the installed bundle.
sys.dont_write_bytecode = True

import argparse
from collections import Counter
from copy import deepcopy
from datetime import date, datetime, time, timezone as datetime_timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
from zoneinfo import ZoneInfo


def bundled(name):
    path = Path(__file__).resolve().parents[2] / 'docs-sync' / 'scripts' / (name + '.py')
    spec = importlib.util.spec_from_file_location('_task_query_' + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


goals = bundled('goals')
archive = bundled('todo_archive')
STATUS = re.compile(r'^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?Status:(?:\*\*)?[ \t]*([^\r\n]*)', re.M | re.I)
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?$')
DETAIL_FIELDS = ('Goal', 'Payoff', 'Sources', 'Scope', 'Scope delivered', 'Acceptance',
                 'Acceptance checked', 'Dependencies', 'Blocker', 'Blocked', 'Checks',
                 'Verification', 'Delivery', 'Remaining work', 'Remaining qualification')


def warning(warnings, source, code, message):
    item = dict(source=source, code=code, message=str(message))
    if item not in warnings:
        warnings.append(item)


def prose(text):
    return re.sub(r'<!--.*?-->', lambda m: re.sub(r'[^\r\n]', ' ', m[0]),
                  goals.task_prose(text), flags=re.S)


def read_source(repo, name):
    """Read local regular sources only; no symlink traversal, caches or repair."""
    path = Path(name)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('nonlocal source')
    if any((repo / part).is_symlink() for part in (path, *path.parents)):
        raise ValueError('symlink source refused')
    try:
        fd = os.open(repo / path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise ValueError('non-regular source refused')
            return source.read()
    except FileNotFoundError:
        return None


def git(repo, *args):
    # No shell, pager, external diff, replacement objects, lazy fetch or index refresh.
    # Trace destinations and injected config can write files even for read commands.
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_REPLACE_OBJECTS='1',
               GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0', GIT_PAGER='cat',
               GIT_LITERAL_PATHSPECS='1', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
    result = subprocess.run(['git', '--no-pager', '-C', str(repo), *args],
                            capture_output=True, env=env, timeout=20)
    if result.returncode:
        raise ValueError('local Git evidence unavailable')
    return result.stdout.decode('utf-8')


def snapshot(repo):
    warnings, blobs = [], {}
    def load(name):
        try:
            blobs[name] = read_source(repo, name)
        except (OSError, ValueError) as exc:
            blobs[name] = None
            warning(warnings, name, 'unreadable', exc)
        try:
            return (blobs[name] or b'').decode('utf-8')
        except UnicodeError:
            warning(warnings, name, 'malformed', 'source is not UTF-8')
            return ''
    todo, ledger = load('TODO.md'), load('goals.json')
    if blobs['TODO.md'] is None:
        warning(warnings, 'TODO.md', 'missing', 'current task source missing')
    known = set(goals.task_bodies(todo))
    owner = None
    try:
        navigation = archive.navigation(todo, prose(todo), known)
        owner = archive.archive_owner(repo, navigation).as_posix()
        history = load(owner)
        if blobs[owner] is None:
            for target in re.findall(r'\[[^\]\n]+\]\(([^)\n]+)\)', navigation):
                if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
                    continue
                try:
                    linked = archive.local_archive(repo, target).as_posix() == owner
                except SystemExit:
                    continue  # Unrelated navigation is not an archive designation.
                if linked:
                    warning(warnings, owner, 'missing', 'linked task history missing')
    except SystemExit as exc:
        history = ''
        warning(warnings, 'TODO.md', 'archive_owner', exc)
    return blobs, todo, ledger, owner, history, warnings


def state_of(raw):
    match = re.match(r'(done|superseded|open|in[_ -]progress|reopened)\b', raw.strip(), re.I)
    if not match:
        return 'unknown'
    state = re.sub(r'[_ -]', '_', match[1].lower())
    return 'open' if state == 'reopened' else state


def occurrences(text, name, known, warnings):
    masked = prose(text)
    for match in re.finditer(r'^[-*] \[([^\]\r\n]*)\]', masked, re.M):
        if match[1] not in (' ', 'x', 'X'):
            warning(warnings, name, 'malformed_task', 'unsupported task checkbox at line ' + str(text.count('\n', 0, match.start()) + 1))
    # Supply known heading IDs to the shared boundary parser in TODO-only repos too.
    known = set(known) | set(goals.task_bodies(text))
    for match in re.finditer(r'^#{3}[ \t]+([^\r\n]+)', masked, re.M):
        heading = re.match(archive.TASK_HEADING, match[1])
        if heading:
            known.add(heading[1])
    spans, headings = archive.entries(text, masked, known)
    # Supersession prefixes belong to the following entry, never the preceding task.
    prefixes = list(re.finditer(r'^Disposition:[ \t]*Superseded[^\r\n]*', masked, re.M | re.I))
    out = []
    for index, (start, end, tid, mark) in enumerate(spans):
        following = spans[index + 1][0] if index + 1 < len(spans) else len(text)
        prefix = next((p for p in reversed(prefixes) if p.start() < start), None)
        previous = spans[index - 1][0] if index else -1
        superseded = prefix is not None and prefix.start() > previous
        end = min([end] + [p.start() for p in prefixes if start < p.start() < following])
        body, clean = text[start:end], masked[start:end]
        statuses = STATUS.findall(clean)
        state = state_of(statuses[0]) if len(statuses) == 1 else ('done' if mark in ('x', 'X') else 'open' if mark == ' ' else 'unknown')
        labels = re.findall(r'^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?([A-Za-z][A-Za-z /-]*):(?:\*\*)?[ \t]*', clean, re.M)
        uncertain = (len(statuses) > 1 or state == 'unknown' or
                     any(count > 1 for count in Counter(label.casefold() for label in labels).values()))
        if superseded:
            state = 'superseded'
        if mark in ('x', 'X') and state not in ('done', 'superseded'):
            uncertain = True
        if state == 'done' and not archive.explicitly_closed(clean, mark):
            uncertain = True
        if any(a < end and start < b for a, b, other, _ in spans if a != start or other != tid):
            uncertain = True
        fields = goals.task_fields(clean)
        # task_fields omits empty values; an explicit empty gate is not absent.
        if any(label.casefold() == 'dependencies' for label in labels):
            fields['Dependencies'] = next((v for k, v in fields.items()
                                            if k.casefold() == 'dependencies'), '')
        first = clean.splitlines()[0]
        title = re.sub(r'^#{3,6}\s+', '', first)
        title = re.sub(r'^[-*] \[[ xX]\]\s+', '', title)
        title = re.sub(r'^(?:\*\*)?`?' + re.escape(tid) + r'`?(?:\*\*)?\s*(?:[—–:-]\s*)?', '', title).strip()
        section = next((h[2].strip() for h in reversed(headings) if h.start() < start and len(h[1]) == 2), '')
        # The shared live parser understands the explicit Now / Next section spelling.
        live = goals.task_bodies(text).get(tid, [])
        if len(live) == 1:
            section = live[0][2]
        out.append(dict(id=tid, title=title or tid, state=state, uncertain=uncertain,
                        path=name, line=text.count('\n', 0, start) + 1, section=section,
                        fields=fields, _body=clean))
    counts = Counter(row['id'] for row in out)
    for row in out:
        if counts[row['id']] > 1:
            row['uncertain'] = True
        if row['uncertain']:
            warning(warnings, name, 'ambiguous_task', f"{row['id']}: conflicting metadata, duplicate or overlapping task boundaries")
    return out


def collect(todo, ledger, owner, history, warnings, *, ledger_present=False):
    data, rows = None, []
    if ledger_present and not ledger:
        warning(warnings, 'goals.json', 'malformed', 'empty ledger')
    if ledger:
        try:
            data = goals.parse_ledger(ledger)
            problems = goals.shape_errors(data)
            if problems:
                raise ValueError('; '.join(problems))
            # Only normalize an in-memory copy. Report original source states below.
            normalized = goals.normalize(deepcopy(data))
            problems = goals.errors(normalized, allow_pending_evidence=True)
            if problems:
                warning(warnings, 'goals.json', 'invalid_ledger', '; '.join(problems))
            rows = data['tasks']
        except (ValueError, TypeError) as exc:
            warning(warnings, 'goals.json', 'malformed', exc)
            data = None
    known = {row['id'] for row in rows}
    live = occurrences(todo, 'TODO.md', known, warnings)
    known |= {r['id'] for r in live}
    historical = occurrences(history, owner, known, warnings) if owner else []
    ids = list(dict.fromkeys([r['id'] for r in live] + sorted({r['id'] for r in rows + historical})))
    records = []
    for tid in ids:
        current = [r for r in live if r['id'] == tid]
        past = [r for r in historical if r['id'] == tid]
        indexed = [r for r in rows if r['id'] == tid]
        sources = current + past
        primary = next(iter(current or past), None)
        state = current[0]['state'] if current else indexed[0].get('status', 'open') if indexed else past[0]['state']
        uncertain = len(indexed) > 1 or any(r['uncertain'] for r in sources)
        dependency_conflict = False
        if data is not None and current and not indexed:
            uncertain = True  # A present ledger cannot silently omit a live task.
        if indexed and current:
            ledger_task = indexed[0]
            if ledger_task.get('status', 'open') != state:
                uncertain = True
            if state in ('open', 'in_progress'):
                body_task = current[0]
                if body_task['section'] != ledger_task.get('section', 'Next'):
                    uncertain = True
                goal_field = body_task['fields'].get('Goal')
                if goal_field and re.split(r'[\s—–:]', goal_field, 1)[0] != ledger_task.get('goal'):
                    uncertain = True
                dependency_field = body_task['fields'].get('Dependencies')
                if dependency_field is not None:
                    # Validate the entire field: finding zero IDs in punctuation
                    # must never silently authorize an empty dependency gate.
                    if re.fullmatch(r'none[.\s]*', dependency_field, re.I):
                        body_deps = set()
                    elif re.fullmatch(goals.TASK_ID + r'(?:(?:\s*,\s*|\s+)' + goals.TASK_ID + r')*\.?', dependency_field):
                        body_deps = set(re.findall(goals.TASK_ID, dependency_field))
                    else:
                        body_deps = None
                    dependency_conflict = body_deps is None or body_deps != set(ledger_task.get('depends_on', []))
                    if dependency_conflict:
                        uncertain = True
        # Archived done evidence can explain reopening, not override it. Conversely,
        # an unfinished/superseded archived copy contradicts a current done claim.
        if current and state == 'done' and any(r['state'] != 'done' for r in past):
            uncertain = True
        if indexed and not current and any(r['state'] != state for r in past):
            uncertain = True
        if not current and len({r['state'] for r in past}) > 1:
            uncertain = True
        # A current body must exist for an unfinished ledger task to be eligible.
        if indexed and not current and state not in ('done', 'superseded'):
            uncertain = True
        if uncertain:
            warning(warnings, tid, 'conflicting_task', 'attributed sources do not establish one consistent current state')
        source_info = [dict(path=r['path'], line=r['line'], state=r['state'],
                            section=r['section'], goal=r['fields'].get('Goal'),
                            dependencies=r['fields'].get('Dependencies'), uncertain=r['uncertain']) for r in sources]
        source_info += [dict(path='goals.json', state=r.get('status', 'open'),
                             task=tid, goal=r.get('goal'), section=r.get('section', 'Next'),
                             depends_on=r.get('depends_on', [])) for r in indexed]
        fields = primary['fields'] if primary else {}
        deps = indexed[0].get('depends_on', []) if indexed else []
        records.append(dict(id=tid, title=primary['title'] if primary else indexed[0].get('title', tid),
                            state=state, section=primary['section'] if primary else indexed[0].get('section', ''),
                            uncertain=uncertain,
                            pending=any(r['state'] not in ('done', 'superseded') for r in current) or
                                    any(r.get('status', 'open') not in ('done', 'superseded') for r in indexed),
                            reopened=bool(current and state in ('open', 'in_progress') and any(r['state'] == 'done' for r in past)),
                            sources=source_info, details={k: v for k, v in fields.items() if k in DETAIL_FIELDS},
                            depends_on=deps, blocked=bool(dependency_conflict or fields.get('Blocker') or fields.get('Blocked') or
                                                         (primary and primary['section'] == 'Needs decision')),
                            date=None, events=[],
                            _sources=sources, _ledger=indexed,
                            _body='\n'.join(r['_body'] for r in sources)))
    return records, data


def timezone_info(name):
    if name:
        return ZoneInfo(name), name
    # Preserve DST rules where the host exposes its zone, rather than today's offset.
    env_zone = os.environ.get('TZ', '').lstrip(':')
    if env_zone and not env_zone.startswith('/'):
        try:
            return ZoneInfo(env_zone), env_zone
        except (ValueError, KeyError):
            pass
    try:
        target = str(Path('/etc/localtime').resolve())
        if '/zoneinfo/' in target:
            key = target.split('/zoneinfo/', 1)[1]
            return ZoneInfo(key), key
        with open('/etc/localtime', 'rb') as source:
            zone = ZoneInfo.from_file(source, key='host-local')
            return zone, 'host-local (/etc/localtime)'
    except (OSError, ValueError):
        local = datetime.now().astimezone().tzinfo
        return local, str(local)


def timestamp(value, zone):
    if not isinstance(value, str) or not DATE.fullmatch(value):
        raise ValueError('expected ISO date or timestamp')
    if len(value) == 10:
        return datetime.combine(date.fromisoformat(value), time.min, zone)
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    # Naive timestamps during DST folds/gaps cannot establish an instant safely.
    if parsed.tzinfo is None:
        first, second = parsed.replace(tzinfo=zone, fold=0), parsed.replace(tzinfo=zone, fold=1)
        if first.utcoffset() != second.utcoffset():
            raise ValueError('ambiguous or nonexistent local timestamp; specify an offset')
        parsed = first
    return parsed.astimezone(zone)


def explicit_dates(records, zone, warnings):
    for record in records:
        evidence = []
        for source in record['_sources']:
            if source['state'] != 'done' or source['uncertain']:
                continue
            for match in re.finditer(r'^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?(Completed(?: at| on)?|Completion date|Completion receipt):(?:\*\*)?[ \t]*([^\r\n]+)', source['_body'], re.M | re.I):
                evidence.append((match[2].strip(), dict(path=source['path'], line=source['line'], field=match[1])))
        for source in record['_ledger']:
            if source.get('status') == 'done':
                for field in ('completed_at', 'completed_on', 'completion_date'):
                    if field in source:
                        evidence.append((source[field], dict(path='goals.json', task=record['id'], field=field)))
        parsed = []
        for value, origin in evidence:
            try:
                instant = timestamp(value, zone)
                parsed.append(dict(kind='explicit', at=instant.isoformat(), value=value, source=origin))
            except ValueError as exc:
                record['_date_conflict'] = True
                warning(warnings, origin['path'], 'invalid_date', f"{record['id']}: {exc}")
        if len({datetime.fromisoformat(e['at']).timestamp() for e in parsed}) > 1:
            record['_date_conflict'] = True
            warning(warnings, record['id'], 'conflicting_dates', 'completion dates disagree; no date selected')
        record['events'] = parsed
        if record['state'] == 'done' and not record['uncertain'] and parsed and not record.get('_date_conflict'):
            record['date'] = parsed[0]


def git_dates(repo, records, paths, limit, head, zone, warnings, include_pending=False):
    targets = {r['id']: r for r in records if not r.get('_date_conflict') and not r['uncertain'] and
               ((r['state'] == 'done' and r['date'] is None) or r['reopened'] or
                (include_pending and r['state'] in ('open', 'in_progress')))}
    try:
        if head is None:
            raise ValueError('target has no local Git history')
        shallow = git(repo, 'rev-parse', '--is-shallow-repository').strip() == 'true'
        if shallow:
            warning(warnings, 'Git', 'shallow', 'local history is shallow; completion coverage is partial')
        if not targets:
            return
        commits = git(repo, 'log', '--first-parent', '--format=%H', f'-{limit + 1}', head, '--', *paths).splitlines()
        if len(commits) > limit:
            warning(warnings, 'Git', 'bounded', f'only {limit} relevant commits searched; request a larger git_limit to expand')
        cache = {}
        def at(revision):
            if revision in cache:
                return cache[revision]
            texts = {}
            tree = git(repo, 'ls-tree', '-rz', '--full-tree', revision, '--', *paths)
            for entry in tree.split('\0'):
                if not entry:
                    continue
                metadata, path = entry.split('\t', 1)
                mode, kind, _ = metadata.split()
                if kind != 'blob' or mode not in ('100644', '100755'):
                    warning(warnings, 'Git:' + path, 'historical_sources', 'non-regular historical source; transitions excluded')
                    cache[revision] = {}
                    return {}
                # An absent tree path is missing; a present but unreadable blob is
                # unavailable evidence, not permission to omit a disagreeing source.
                texts[path] = git(repo, 'show', f'{revision}:{path}')
            todo, ledger = texts.get('TODO.md', ''), texts.get('goals.json', '')
            # Only examine archives in the resolved local evidence set. Never follow
            # historical task links to arbitrary files or remote content.
            archives = [(p, text) for p, text in texts.items() if p not in ('TODO.md', 'goals.json') and text]
            scratch = []
            hist = '\n'.join(text for _, text in archives)
            result, _ = collect(todo, ledger, 'Git archive', hist, scratch,
                                ledger_present='goals.json' in texts)
            for issue in scratch:
                warning(warnings, 'Git:' + issue['source'], 'historical_sources',
                        'conflicting/malformed historical source; affected transitions excluded')
            fatal = any(w['code'] not in ('ambiguous_task', 'conflicting_task') for w in scratch)
            cache[revision] = {r['id']: dict(state=r['state'], uncertain=r['uncertain']) for r in result} if not fatal else {}
            return cache[revision]
        # Only a transition in the current uninterrupted done cycle can date it.
        # In particular an uncommitted re-completion after a committed reopening
        # cannot borrow the previous cycle's recording time.
        tip = at(head)
        current_cycle = {tid: record['state'] == 'done' and
                         tip.get(tid, {}).get('state') == 'done' and
                         not tip.get(tid, {}).get('uncertain', True)
                         for tid, record in targets.items()}
        for commit in commits[:limit]:
            parent_line = git(repo, 'rev-list', '--parents', '-n', '1', commit).split()
            if len(parent_line) < 2:
                continue  # A root/import is not an observed transition.
            after, before = at(commit), at(parent_line[1])
            for tid, record in targets.items():
                if any(e['kind'] == 'git_recorded' for e in record['events']):
                    continue
                a, b = after.get(tid), before.get(tid)
                if not a or a['uncertain'] or a['state'] != 'done':
                    current_cycle[tid] = False
                if (a and b and not a['uncertain'] and not b['uncertain'] and
                        a['state'] == 'done' and b['state'] in ('open', 'in_progress')):
                    instant = timestamp(git(repo, 'show', '-s', '--format=%cI', commit).strip(), zone)
                    event = dict(kind='git_recorded', at=instant.isoformat(), commit=commit,
                                 source=dict(paths=paths, before=parent_line[1]),
                                 meaning='recorded complete in Git; not the time work finished')
                    record['events'].append(event)
                    if current_cycle[tid]:
                        record['date'] = event
                    elif record['state'] in ('open', 'in_progress'):
                        record['reopened'] = True
        if any(r['date'] is None and r['state'] == 'done' for r in targets.values()):
            warning(warnings, 'Git', 'undated', 'some completion dates are unestablished; imports/additions alone are not transitions')
    except (OSError, ValueError, subprocess.SubprocessError):
        warning(warnings, 'Git', 'unavailable', 'local Git completion evidence unavailable; history/date coverage is partial')


def selection(records, data, todo, unsafe):
    result = dict(focus=data.get('primary_milestone') if data else None, next_eligible=None,
                  eligible=[], excluded=[], priority={'state': 'unavailable'}, notes=[])
    by_id = {r['id']: r for r in records}
    if not data:
        result['notes'] = ['No usable goals.json: TODO order is available, dependency eligibility is unestablished.']
        return result
    normalized = goals.normalize(deepcopy(data))
    result['priority'] = goals.priority_status(normalized, todo)
    for record in records:
        task = next((t for t in normalized['tasks'] if t['id'] == record['id']), None)
        if task:
            goal = next((g for g in normalized['goals'] if g['id'] == task.get('goal')), {})
            record['blocked'] = bool(record['blocked'] or
                                     task.get('section') == 'Needs decision' or
                                     any(by_id.get(d, {}).get('state') != 'done' or by_id.get(d, {}).get('uncertain', True) for d in task['depends_on']) or
                                     any(next((g.get('status') for g in normalized['goals'] if g['id'] == dep), None) != 'met' for dep in goal.get('depends_on', [])))
    if unsafe or any(r['uncertain'] for r in records):
        result['notes'] = ['Conflicting/incomplete sources: no next-eligible claim.']
        return result
    if result['priority']['state'] == 'drift':
        result['notes'] = ['Priority drift: human TODO order shown without reconciliation or selection.']
        return result
    # The shared selection guard (drift was reported above, so it cannot raise here).
    picks, _ = goals.queue(normalized, todo)
    ordered = [t['id'] for t, _ in picks if t['id'] in by_id]
    result['excluded'] = [tid for tid in ordered if by_id[tid]['blocked']]
    result['eligible'] = [tid for tid in ordered if tid not in result['excluded']]
    result['next_eligible'] = next(iter(result['eligible']), None)
    result['notes'] = (['Recorded blockers exclude ' + ', '.join(result['excluded']) + ' from dependency-eligible ordering.']
                       if result['excluded'] else goals.selection_notes(normalized, [r['id'] for r in records]))
    result['notes'].append('Eligibility is recorded dependency/priority evidence, not worker admission or liveness.')
    return result


def query(repo=None, *, mode='pending', text=None, task_id=None, since=None, until=None,
          timezone=None, limit=5, git_limit=500, state='all'):
    """Return JSON-compatible evidence without changing repository bytes or refs."""
    if mode not in ('pending', 'detail', 'search', 'history') or state not in ('all', 'pending', 'done'):
        raise ValueError('invalid mode or state filter')
    if limit != 'all' and (type(limit) is not int or limit < 1):
        raise ValueError('limit must be positive or all')
    if type(git_limit) is not int or git_limit < 1:
        raise ValueError('git_limit must be positive')
    if repo is None:
        repo = Path.cwd()
        try:
            repo = Path(git(repo, 'rev-parse', '--show-toplevel').strip())
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    repo = Path(repo).resolve()
    zone, zone_name = timezone_info(timezone)
    lower, upper = timestamp(since, zone) if since else None, timestamp(until, zone) if until else None
    # Same-ZoneInfo comparisons ignore folds; compare instants, not wall clocks.
    lower_utc = lower.astimezone(datetime_timezone.utc) if lower else None
    upper_utc = upper.astimezone(datetime_timezone.utc) if upper else None
    if lower_utc and upper_utc and lower_utc >= upper_utc:
        raise ValueError('since must precede until (half-open interval)')
    for attempt in range(2):
        blobs, todo, ledger, owner, history, warnings = snapshot(repo)
        records, data = collect(todo, ledger, owner, history, warnings,
                                ledger_present=blobs.get('goals.json') is not None)
        unsafe = any(w['code'] not in ('ambiguous_task', 'conflicting_task') for w in warnings)
        explicit_dates(records, zone, warnings)
        try:
            if Path(git(repo, 'rev-parse', '--show-toplevel').strip()).resolve() != repo:
                raise ValueError('Git belongs to an enclosing repository, not the target')
            head = git(repo, 'rev-parse', '--verify', 'HEAD').strip()
        except (OSError, ValueError, subprocess.SubprocessError):
            head = None
        if mode in ('history', 'detail') or since or until:
            paths = list(dict.fromkeys(['TODO.md', 'goals.json'] + ([owner] if owner else []) + list(archive.LEGACY) + [archive.DEFAULT]))
            git_dates(repo, records, paths, git_limit, head, zone, warnings,
                      include_pending=(mode == 'detail' or bool(task_id or text)))
        changed = []
        for name, original in blobs.items():
            try:
                if read_source(repo, name) != original:
                    changed.append(name)
            except (OSError, ValueError):
                changed.append(name)
        # Re-resolve the owner too: a new conventional archive can change ownership.
        fresh = snapshot(repo)
        if fresh[0] != blobs or fresh[3] != owner:
            changed.extend(set(fresh[0]) | set(blobs))
        try:
            if head and git(repo, 'rev-parse', '--verify', 'HEAD').strip() != head:
                changed.append('Git HEAD')
        except (OSError, ValueError, subprocess.SubprocessError):
            if head:
                changed.append('Git HEAD')
        if changed and not attempt:
            continue
        if changed:
            unsafe = True
            for name in sorted(set(changed)):
                warning(warnings, name, 'unstable', 'source changed during both attempts; claims suppressed')
        for record in records:
            if unsafe:
                record['uncertain'] = True
            if record['uncertain']:
                record['date'] = None  # Attributed events are not confirmed range matches.
        picks = selection(records, data, todo, unsafe)
        break
    counts = dict(Counter(r['state'] for r in records if r['pending']))
    needle = task_id if task_id is not None else text
    exact, identity = [], False
    if needle:
        folded = needle.casefold()
        exact = [r for r in records if r['id'].casefold() == folded]
        if not exact:
            exact = [r for r in records if folded in [p.casefold() for p in r['id'].split('-')] or
                     r['id'].casefold().endswith('-' + folded) or r['id'].casefold().startswith(folded + '-')]
        identity = bool(exact)
        exact.sort(key=lambda r: r['id'])
    candidates = exact if identity else records
    if not identity:
        if mode == 'pending' or state == 'pending':
            candidates = [r for r in candidates if r['pending']]
        elif mode == 'history' or state == 'done':
            candidates = [r for r in candidates if r['state'] == 'done' and not r['uncertain']]
        if needle:
            folded = needle.casefold()
            candidates = [r for r in candidates if folded in r['title'].casefold() or folded in r['_body'].casefold()]
            candidates.sort(key=lambda r: (0 if folded in r['title'].casefold() else 1, r['id']))
    undated = []
    if mode == 'history' or lower or upper:
        undated = sorted([r for r in candidates if r['date'] is None], key=lambda r: r['id'])
        dated = [r for r in candidates if r['date'] is not None and not r['uncertain']]
        dated.sort(key=lambda r: (-datetime.fromisoformat(r['date']['at']).timestamp(), r['id']))
        if lower or upper:
            candidates = [r for r in dated if
                          (not lower_utc or datetime.fromisoformat(r['date']['at']).astimezone(datetime_timezone.utc) >= lower_utc) and
                          (not upper_utc or datetime.fromisoformat(r['date']['at']).astimezone(datetime_timezone.utc) < upper_utc)]
        elif not identity:
            candidates = dated or undated
    total = len(candidates)
    cap = None if limit == 'all' else limit
    def public(record):
        return {k: v for k, v in record.items() if not k.startswith('_')}
    return dict(mode=mode, repo=str(repo), timezone=zone_name,
                interval=dict(since=lower.isoformat() if lower else None, until=upper.isoformat() if upper else None),
                records=[public(r) for r in candidates[:cap]], total=total,
                counts=counts, pending_total=sum(counts.values()),
                uncertain_ids=sorted(r['id'] for r in records if r['uncertain']),
                remaining=max(0, total - (cap or total)),
                ambiguous=bool(needle and len(candidates) > 1),
                undated=[public(r) for r in undated[:cap]], undated_total=len(undated),
                recency='dated' if any(r['date'] for r in candidates) else 'unknown',
                selection=picks, warnings=warnings, partial=bool(warnings),
                totals_provenance='partial repository evidence' if warnings else 'current repository evidence')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('pending', 'detail', 'search', 'history'))
    parser.add_argument('--repo')
    parser.add_argument('--text')
    parser.add_argument('--id', dest='task_id')
    parser.add_argument('--since')
    parser.add_argument('--until')
    parser.add_argument('--timezone')
    parser.add_argument('--limit', default='5')
    parser.add_argument('--git-limit', type=int, default=500)
    parser.add_argument('--state', choices=('all', 'pending', 'done'), default='all')
    args = vars(parser.parse_args())
    try:
        args['limit'] = 'all' if args['limit'] == 'all' else int(args['limit'])
        result = query(**args)
    except (ValueError, KeyError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
