"""Conservative opt-in prose-review pilot, based on committed changes and gate evidence.

This is deliberately not a general source-code risk classifier. Unknown scope, executable
content, explicit review language, and checks not proved by the receipt retain model review.
"""
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tomllib

from . import main_check

INSTRUCTIONS = {'AGENTS.MD', 'CLAUDE.MD', 'GEMINI.MD', 'CONTRIBUTING.MD'}
SENSITIVE = re.compile(
    r'review|secur|auth|permission|secret|credential|payment|billing|migrat|schema|deploy|'
    r'release|workflow|runbook|architecture|plan|spec|polic|contract|instruction|agent|skill|prompt', re.I)
REVIEW = re.compile(r'\breview\w*\b', re.I)
EXTERNAL_ACCEPTANCE = re.compile(r'\b(?:live|device|hardware|production|manual|approval|owner|human)\b', re.I)
EXECUTABLE_MARKUP = re.compile(r'(?m)^\s*(?:```|~~~|\.\.\s)|<[A-Za-z!/]')


def version():
    # Receipt reuse also depends on the integration code that supplied the evidence.
    return hashlib.sha256(Path(__file__).read_bytes()
                          + Path(__file__).with_name('worker.py').read_bytes()).hexdigest()


def git(checkout, *args):
    return subprocess.run(['git', '-C', str(checkout), *args], check=True,
                          capture_output=True, text=True, timeout=10).stdout


def decide(checkout, task, *, evidence=None, env=None):
    """Return a reasoned decision; only explicit ``auto`` invokes the bounded classifier.

    ``0`` retains the existing operator opt-out. The caller supplies a validated producing
    gate receipt, not a worker report or a boolean claiming the gate passed.
    """
    mode = (os.environ if env is None else env).get('PI_AUTOWORK_REVIEW', '1')
    result = {'required': True, 'mode': mode, 'version': version(), 'reason': 'model review is required'}
    if mode == '0':
        return dict(result, required=False, reason='model review explicitly disabled (PI_AUTOWORK_REVIEW=0)')
    if mode != 'auto':
        return result
    try:
        reason = required_reason(checkout, task, evidence)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        reason = 'policy inspection was incomplete'
    return dict(result, required=bool(reason), reason=reason or 'small ordinary prose; task checks covered by gate')


def required_reason(checkout, task, evidence):
    if not isinstance(evidence, dict) or evidence.get('ok') is not True:
        return 'no accepted pre-landing check receipt'
    result = evidence.get('result') or {}
    if (type(result.get('code')) is not int or result['code'] != 0
            or result.get('failures') != [] or result.get('timed_out') is not False
            or result.get('skips') != 0 or result.get('resource_skips') != 0):
        return 'gate evidence is incomplete or includes failures/skips'
    if git(checkout, 'status', '--porcelain=v1', '--untracked-files=all').strip():
        return 'checkout differs from its committed evidence'
    tree = git(checkout, 'rev-parse', 'HEAD^{tree}').strip()
    # A later batch step may fix this one's failures or change its checker. Only the
    # exact tree can skip review; ancestors keep the normal reviewer, without extra suites.
    commit = evidence['commit']
    if (tree != evidence.get('tree')
            or git(checkout, 'rev-parse', f'{commit}^{{tree}}').strip() != tree):
        return 'gate did not check this exact tree'
    selection = evidence.get('selection')
    if selection is not None and (not isinstance(selection, dict) or selection.get('full') is not True):
        return 'affected-only evidence does not prove all declared task checks'
    command = evidence.get('full_command') or evidence.get('command') or ''
    if not command or not main_check.receipt_command_matches(evidence, command):
        return 'gate command is not established'
    path = f'tasks/items/{task}.md'
    before = git(checkout, 'show', f'HEAD^1:{path}')
    contract = git(checkout, 'show', f'HEAD:{path}')
    if before != contract:
        return 'task contract changed with the candidate'
    lines = contract.splitlines()
    if not lines or lines[0] != '+++':
        return 'task contract is not structured'
    record = tomllib.loads('\n'.join(lines[1:lines.index('+++', 1)]))
    checks = record.get('checks')
    if (record.get('schema') != 1 or record.get('id') != task or not isinstance(checks, list)
            or not checks or any(not isinstance(c, str) or c.strip() != command for c in checks)):
        return 'task checks are not all covered by the executed gate'
    prose = ' '.join(str(record.get(key, '')) for key in ('title', 'scope', 'acceptance', 'checks', 'exclusions'))
    prose += '\n' + '\n'.join(lines[lines.index('+++', 1) + 1:])
    if (REVIEW.search(contract) or EXTERNAL_ACCEPTANCE.search(prose)
            or record.get('live', 'denied') != 'denied' or record.get('ownership') != 'worker'):
        return 'task mentions review or external acceptance; preserve its requirement'
    tracked = git(checkout, 'ls-tree', '-r', '-z', 'HEAD').rstrip('\0').split('\0')
    for entry in tracked:
        metadata, item = entry.split('\t', 1)
        if PurePosixPath(item).name.upper() == 'CODEOWNERS':
            return 'repository has an owner-review policy'
        if PurePosixPath(item).name.upper() in INSTRUCTIONS:
            if not metadata.startswith('100644 blob '):
                return f'repository instructions are indirect: {item}'
            instructions = git(checkout, 'show', f'HEAD:{item}')
            # Do not try to infer obligations from arbitrary natural language. This pilot
            # can discharge only full-check declarations identical to the producing gate.
            if (main_check.FULL_CHECK.sub('', instructions).strip()
                    or any(c.strip() != command for c in main_check.FULL_CHECK.findall(instructions))):
                return f'repository instructions have additional obligations: {item}'
    raw = git(checkout, 'diff', '--raw', '-z', '--no-renames', 'HEAD^1', 'HEAD').rstrip('\0').split('\0')
    if not raw or len(raw) % 2 or len(raw) > 20:
        return 'change is empty, malformed or exceeds ten files'
    for header, path in zip(raw[::2], raw[1::2]):
        oldmode, newmode, _, _, status = header.split()
        if oldmode not in (':000000', ':100644') or newmode != '100644' or status not in ('A', 'M'):
            return 'deletions, renames and special file modes require review'
        file = PurePosixPath(path)
        if (not (path.startswith('docs/') or path in ('README.md', 'CHANGELOG.md'))
                or file.suffix not in ('.md', '.rst') or SENSITIVE.search(path)):
            return f'not ordinary prose: {path}'
        # Check old and new text: removing a requirement is not an innocuous prose edit.
        texts = [git(checkout, 'show', f'HEAD:{path}')]
        if status == 'M':
            texts.append(git(checkout, 'show', f'HEAD^1:{path}'))
        if any(SENSITIVE.search(text) or EXECUTABLE_MARKUP.search(text) for text in texts):
            return f'sensitive or executable documentation: {path}'
    counts = git(checkout, 'diff', '--numstat', '--no-renames', 'HEAD^1', 'HEAD').splitlines()
    if sum(int(n) for row in counts for n in row.split('\t', 2)[:2]) > 400:
        return 'change exceeds 400 added/deleted lines'
    return ''
