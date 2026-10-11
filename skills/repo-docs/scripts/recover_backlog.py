#!/usr/bin/env python3
"""Repair accepted-plan binding and restore missing bodies from immutable same-task history.

Run only as the integration owner (or in a private proposal checkout). This never
accepts a plan, changes ledger state, deduplicates conflicting bodies or dispatches.
"""
import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re
import subprocess
import sys

import goals


def committed(repo, pin, name):
    if re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', pin) is None:
        raise ValueError('source commit must be a full immutable commit ID')
    env = {k: v for k, v in goals.os.environ.items() if not k.startswith('GIT_')}
    mode = subprocess.check_output(['git', '-C', str(repo), 'ls-tree', pin, '--', name],
                                   env=env, text=True, timeout=10)
    if not mode.startswith(('100644 blob ', '100755 blob ')):
        raise ValueError('recovery source must be a committed regular file: ' + name)
    return subprocess.check_output(['git', '-C', str(repo), 'show', pin + ':' + name],
                                   env=env, timeout=10).decode('utf-8')


def field(body, label):
    return re.search(r'^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?' + label
                     + r':(?:\*\*)?[ \t]*([^\n]*)', body, re.M)


def repair(repo, plan, ids, pin=None):
    data = goals.load(repo)
    problems = goals.errors(data)
    if problems:
        raise ValueError('; '.join(problems))
    reasons, blobs = [], {}
    decision = goals.local_reference(repo, plan, blobs, reasons)
    if '#' not in plan or not re.search(r'^\s*(?:\*\*)?Status:(?:\*\*)?\s*Accepted\s*$', decision, re.M | re.I):
        raise ValueError('accepted plan required; recovery cannot manufacture approval')
    if reasons:
        raise ValueError('; '.join(reasons))
    if len(set(ids)) != len(ids) or any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', tid) for tid in ids):
        raise ValueError('unique literal task IDs required')
    original = goals.checked_bytes(repo / 'TODO.md')
    text = original.decode('utf-8') if original is not None else '# TODO\n'
    tasks = {t['id']: t for t in data['tasks']}
    owners = {g['id']: g for g in data['goals']}
    repairs = []
    for tid in ids:
        task = tasks.get(tid)
        if task is None or task['status'] == 'done':
            raise ValueError('existing unfinished task required: ' + tid)
        owner = owners[task['goal']]
        if owner['source'] != plan:
            raise ValueError('accepted plan is not the goal intent source: ' + tid)
        entries = goals.task_bodies(text).get(tid, [])
        if len(entries) > 1:
            if any(entry != entries[0] for entry in entries[1:]):
                raise ValueError('conflicting or duplicate bodies require owner reconciliation: ' + tid)
            headers = list(re.finditer(r'^[-*] \[([ xX])\]\s+(?:\*\*)?`?' + re.escape(tid)
                                      + r'`?(?:\*\*)?(?=\s|:)', text, re.M))
            if len(headers) != len(entries):
                raise ValueError('duplicate spans cannot be safely located: ' + tid)
            block = entries[0][0]
            for header in reversed(headers[1:]):
                end = header.end() + len(block)
                if text[header.end():end] != block:
                    raise ValueError('duplicate spans differ from task parser: ' + tid)
                text = text[:header.start()] + text[end:]
            entries = goals.task_bodies(text)[tid]
            repairs.append(tid + ': removed identical duplicate body')
        if not entries:
            if not pin:
                raise ValueError('missing body requires immutable same-task source: ' + tid)
            prior = json.loads(committed(repo, pin, 'goals.json'))
            previous = next((t for t in prior['tasks'] if t['id'] == tid), None)
            prior_goal = next((g for g in prior['goals'] if g['id'] == task['goal']), None)
            if (previous is None or any(previous.get(k, [] if k == 'depends_on' else None) != task.get(k, [] if k == 'depends_on' else None)
                                        for k in ('goal', 'title', 'depends_on'))
                    or prior_goal is None or prior_goal['source'] != plan):
                raise ValueError('immutable task intent differs from current ledger: ' + tid)
            history = goals.task_bodies(committed(repo, pin, 'TODO.md')).get(tid, [])
            if len(history) != 1:
                raise ValueError('immutable source lacks unique full body: ' + tid)
            body, mark, _ = history[0]
            fields = goals.task_fields(body)
            ownership = fields.get('Ownership') or re.search(r'(?:^|\.\s+)Ownership:[ \t]*\S[^\n]*', body, re.M)
            if mark != ' ' or not ownership or any(label not in fields for label in
                                   ('Goal', 'Scope', 'Acceptance', 'Dependencies', 'Sources')):
                raise ValueError('immutable source lacks unfinished complete body: ' + tid)
            if not re.match(r'`?' + re.escape(task['goal']) + r'`?(?:[.\s]|$)', fields['Goal']):
                raise ValueError('immutable body goal differs: ' + tid)
            section = task.get('section', 'Next')
            sections = list(re.finditer(r'^##\s+' + re.escape(section) + r'\s*$', text, re.M))
            if len(sections) > 1:
                raise ValueError('duplicate TODO section: ' + section)
            entry = '\n- [ ] ' + tid + body.rstrip() + '\n\n'
            if sections:
                following = re.search(r'^##\s', text[sections[0].end():], re.M)
                end = sections[0].end() + following.start() if following else len(text)
                text = text[:end] + entry + text[end:]
            else:
                text += '\n## ' + section + '\n' + entry
            repairs.append(tid + ': restored committed task body')
        body, _, _ = goals.task_bodies(text)[tid][0]
        sources = field(body, 'Sources')
        fields = goals.task_fields(body)
        if sources is None or 'Sources' not in fields:
            raise ValueError('existing body lacks unique nonempty Sources; do not invent a contract: ' + tid)
        links = re.findall(r'\[[^\]]*\]\(([^\s)]+)\)', fields['Sources'])
        if plan not in links:
            # The ledger already binds this exact accepted intent; add only its link.
            header = re.search(r'^[-*] \[([ xX])\]\s+(?:\*\*)?`?' + re.escape(tid)
                               + r'`?(?:\*\*)?(?=\s|:)', text, re.M)
            if header is None:
                raise ValueError('selected task header cannot be located: ' + tid)
            start = header.end() + sources.end()
            text = text[:start] + ' [Accepted plan](' + plan + ')' + text[start:]
            repairs.append(tid + ': linked accepted goal source')
    if any(goals.checked_bytes(repo / name) != blob for name, blob in blobs.items()):
        raise ValueError('plan inputs changed during recovery')
    if text.encode() != original:
        goals.atomic_write(repo / 'TODO.md', text)
    return repairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo')
    parser.add_argument('--plan', required=True)
    parser.add_argument('--tasks', required=True)
    parser.add_argument('--source-commit')
    parser.add_argument('--expected-revision', required=True)
    parser.add_argument('--canonical-repo')
    args = parser.parse_args()
    try:
        with goals.coordination(args.repo, args.canonical_repo) as repo:
            if goals.revision(repo) != args.expected_revision:
                raise ValueError('stale revision; no recovery write')
            repairs = repair(repo, args.plan, args.tasks.split(','), args.source_commit)
            args.repo, args.receipt = str(repo), None
            output = io.StringIO()
            with redirect_stdout(output):
                code = goals.backlog_check(args)
            result = json.loads(output.getvalue())
            result['repairs'] = repairs
            result['boundary'] = 'clerical recovery only; live ownership and execution authority unknown'
            print(json.dumps(result, indent=2))
            return code
    except (ValueError, OSError, subprocess.SubprocessError, KeyError, TypeError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    sys.exit(main())
