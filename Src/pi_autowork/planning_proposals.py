"""Planning-only proposal validation and guarded local Git landing.

Model text is data, never a shell command. Only complete regular Markdown files
in the small planning allowlist can enter a candidate. Git hooks still execute
with the owner's usual local authority when the owner explicitly applies it.
"""
from contextlib import contextmanager, ExitStack
import difflib
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tempfile
import tomllib

from . import landing, task_commands


class PlanningError(RuntimeError):
    """A planning refusal; retained sessions/worktrees are not discarded."""


MAX_FILE = 256 * 1024
MAX_TOTAL = 2 * 1024 * 1024
MAX_FILES = 64
SECRET = re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bsk-[A-Za-z0-9_-]{12,}'
                    r'|\bBearer [A-Za-z0-9._~+/=-]{12,}'
                    r'|(?i:API_KEY|ACCESS_TOKEN|PASSWORD|CLIENT_SECRET)\s*[=:]\s*["\']?[^\s"\']{8,}')


def run_git(repo, *args, env=None, data=None, check=True):
    clean = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    try:
        result = subprocess.run(['git', '--no-replace-objects', '--no-optional-locks', '-C', str(repo), *args],
                                input=data, capture_output=True, timeout=60,
                                env={**clean, **(env or {})})
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PlanningError('Git operation failed or timed out: ' + args[0]) from exc
    if check and result.returncode:
        # Hook output can contain credentials; do not copy arbitrary stderr to UI.
        raise PlanningError('Git operation refused: ' + args[0] + ' (inspect the retained worktree)')
    return result


def git(repo, *args, **kwargs):
    return run_git(repo, *args, **kwargs).stdout.decode('utf-8').strip()


def canonical(repo):
    listing = run_git(repo, 'worktree', 'list', '--porcelain', '-z').stdout.decode().split('\0\0')[0].split('\0')
    if 'bare' in listing or not listing[0].startswith('worktree '):
        raise PlanningError('a canonical non-bare checkout is required')
    return Path(git(listing[0][9:], 'rev-parse', '--show-toplevel')).resolve()


def path_allowed(name):
    if not isinstance(name, str) or len(name) > 240:
        raise PlanningError('invalid planning path')
    parts = name.split('/')
    if any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', p) or p in ('.', '..') for p in parts):
        raise PlanningError('unsafe planning path: ' + name)
    if any(re.search(r'(?i)credential|secret|evidence|^\.git$', p) for p in parts):
        raise PlanningError('sensitive planning path refused: ' + name)
    task = re.fullmatch(r'tasks/(?:items|goals)/[A-Za-z0-9][A-Za-z0-9_-]*\.md', name)
    doc = len(parts) >= 3 and parts[:2] in (['docs', 'plans'], ['docs', 'specs']) and name.endswith('.md')
    if not task and not doc:
        raise PlanningError('path outside planning allowlist: ' + name)
    return PurePosixPath(name)


def safe_file(root, name):
    path_allowed(name)
    path = Path(root) / name
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise PlanningError('symlink planning path refused: ' + name)
    if path.exists():
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise PlanningError('planning path must be an ordinary unlinked file: ' + name)
        if info.st_mode & 0o111:
            raise PlanningError('executable planning file refused: ' + name)
    return path


def check_files(files):
    if not isinstance(files, dict) or not files or len(files) > MAX_FILES:
        raise PlanningError('proposal must contain 1–64 complete files')
    total = 0
    for name, content in files.items():
        path_allowed(name)
        if not isinstance(content, str) or '\x00' in content:
            raise PlanningError('planning files must contain UTF-8 text')
        size = len(content.encode('utf-8'))
        total += size
        if size > MAX_FILE or total > MAX_TOTAL:
            raise PlanningError('proposal exceeds size budget')
        if SECRET.search(content):
            raise PlanningError('credential-like content refused in proposal')


def stage(meta, files):
    check_files(files)
    root = Path(meta['worktree'])
    targets = {}
    for name, content in files.items():
        path = safe_file(root, name)
        if run_git(root, 'check-ignore', '-q', '--', name, check=False).returncode == 0:
            raise PlanningError('ignored proposal path refused: ' + name)
        targets[path] = content
    # Every name/content is checked before any write. Invalid task schemas remain
    # visible as an invalid preview for the next conversational correction.
    for path, content in targets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        safe_file(root, path.relative_to(root).as_posix())
        fd, temp = tempfile.mkstemp(prefix='.planning-', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content.encode('utf-8'))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, path)
        finally:
            Path(temp).unlink(missing_ok=True)


def snapshot(meta):
    root, base = meta['worktree'], meta['base']
    paths = set(run_git(root, 'diff', '--name-only', '-z', base, '--').stdout.decode().split('\0'))
    paths.update(run_git(root, 'ls-files', '--others', '--exclude-standard', '-z').stdout.decode().split('\0'))
    files = {}
    for name in sorted(paths - {''}):
        path = safe_file(root, name)
        if not path.exists():
            raise PlanningError('deletions are not planning proposals: ' + name)
        if path.stat().st_size > MAX_FILE:
            raise PlanningError('proposal exceeds size budget')
        try:
            files[name] = path.read_bytes().decode('utf-8')
        except UnicodeError as exc:
            raise PlanningError('planning file is not UTF-8: ' + name) from exc
    if files:
        check_files(files)
    return files


def original(meta, name):
    result = run_git(meta['worktree'], 'show', meta['base'] + ':' + name, check=False)
    if result.returncode:
        return None
    return result.stdout.decode('utf-8')


def header(text):
    lines = text.split('\n')
    if lines[0] != '+++' or '+++' not in lines[1:]:
        raise PlanningError('task record requires TOML frontmatter')
    end = lines.index('+++', 1)
    try:
        return tomllib.loads('\n'.join(lines[1:end])), '\n'.join(lines[end + 1:])
    except ValueError as exc:
        raise PlanningError('invalid task TOML') from exc


def authority(meta, files):
    for name, content in files.items():
        if not name.startswith('tasks/'):
            continue
        new, body = header(content)
        old_content = original(meta, name)
        old, old_body = header(old_content) if old_content is not None else ({}, '')
        protected = ('closure', 'closure_actor', 'closure_timestamp', 'closure_reason', 'closure_evidence',
                     'owner_waiver', 'owner_qualification')
        for field in protected:
            if new.get(field) != old.get(field):
                raise PlanningError(name + ': planner cannot change closure/owner evidence field ' + field)
        if '/items/' in name:
            if new.get('status', 'open') != old.get('status', 'open'):
                raise PlanningError(name + ': planner cannot close, supersede or reopen tasks')
            if new.get('live', 'denied') != old.get('live', 'denied'):
                raise PlanningError(name + ': planner cannot change live authorization')
            if old and new.get('ownership', 'unknown') != old.get('ownership', 'unknown'):
                raise PlanningError(name + ': planner cannot change existing ownership')
            if ('live' in new.get('resources', [])) != ('live' in old.get('resources', [])):
                raise PlanningError(name + ': planner cannot change the live resource authorization gate')
        elif new.get('status') != old.get('status', 'unmet'):
            raise PlanningError(name + ': planner cannot invent goal progress or completion')
        # Evidence/holds and owner attestations are not free planning prose.
        def notes(text):
            return [line for line in text.splitlines() if re.match(
                r'\s*-?\s*(Evidence|Verified|Held by|Owner (decision|waiver|qualification)|Live authorization)\s*:',
                line, re.I)]
        if notes(body) != notes(old_body):
            raise PlanningError(name + ': planner cannot invent evidence, owner authority or release holds')


def revision(meta, files):
    return hashlib.sha256(json.dumps({'base': meta['base'], 'repo': meta['repo'], 'files': files},
                                    sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def preview(meta):
    errors, files = [], {}
    try:
        files = snapshot(meta)
        authority(meta, files)
        if git(meta['worktree'], 'diff', '--cached', '--name-only'):
            raise PlanningError('proposal index contains external staged edits')
        if (Path(meta['worktree']) / 'tasks').exists():
            task_commands.worktree_store(meta['worktree'])
    except (PlanningError, task_commands.CommandError, task_commands.StoreError, OSError, ValueError) as exc:
        errors.append(str(exc))
    diff = ''.join(''.join(difflib.unified_diff((original(meta, name) or '').splitlines(keepends=True),
                                              text.splitlines(keepends=True),
                                              fromfile='a/' + name, tofile='b/' + name))
                   for name, text in files.items())
    return {'id': meta['id'], 'revision': revision(meta, files), 'diff': diff,
            'files': sorted(files), 'valid': not errors, 'errors': errors}


@contextmanager
def exclusive(path):
    if path.is_symlink() or path.parent.is_symlink():
        raise PlanningError('unsafe writer lock path')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise PlanningError('planning writer busy; retry after the active writer finishes') from exc
        yield
    finally:
        os.close(fd)


def _target_checks(meta, files):
    repo = meta['repo']
    if git(repo, 'rev-parse', 'HEAD') != meta['base']:
        raise PlanningError('canonical source base changed; create a fresh planning session')
    if git(repo, 'symbolic-ref', '--short', 'HEAD') != meta['target_branch']:
        raise PlanningError('canonical checkout branch changed')
    for root in (repo, meta['worktree']):
        reason = landing.checkout_operation(root)
        if reason:
            raise PlanningError(reason)
    if git(repo, 'status', '--porcelain', '--untracked-files=all', '--', *files):
        raise PlanningError('dirty canonical paths overlap the proposal')
    held, problems = task_commands.in_flight(repo)
    if held or problems:
        raise PlanningError('cannot establish idle execution guard: live/unfinished workers or coordinator')


def apply(meta, accepted, state):
    repo, root = meta['repo'], meta['worktree']
    # Existing landing uses process environment; never let inherited Git routing
    # select another checkout/index/config. Do not mutate process-global env in a UI.
    if any(k.startswith('GIT_') for k in os.environ):
        raise PlanningError('unset inherited GIT_* overrides before applying a plan')
    common = Path(git(repo, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
    with ExitStack() as stack:
        stack.enter_context(exclusive(common / 'autowork-execution/writer.lock'))
        stack.enter_context(exclusive(common / 'interactive-writer.json.lock'))
        if (common / 'interactive-writer.json').exists():
            raise PlanningError('canonical checkout has an interactive writer; release it before applying')
        stack.enter_context(task_commands.locked(repo))
        stack.enter_context(task_commands.locked(root))
        shown = preview(meta)
        if not shown['valid']:
            raise PlanningError('; '.join(shown['errors']))
        if shown['revision'] != accepted:
            raise PlanningError('proposal revision changed; preview and accept it again')
        files = snapshot(meta)
        if revision(meta, files) != accepted:
            raise PlanningError('proposal changed during acceptance')
        if not files:
            raise PlanningError('there is no proposal to apply')
        _target_checks(meta, files)
        head = git(root, 'rev-parse', 'HEAD')
        if head not in (meta['base'], meta.get('candidate')):
            raise PlanningError('proposal worktree HEAD changed')
        # Build the index from immutable accepted bytes, never `git add` mutable
        # working files. Hooks run normally and their final tree is checked below.
        with tempfile.TemporaryDirectory(prefix='commit-', dir=state) as tmp:
            env = {'GIT_INDEX_FILE': str(Path(tmp) / 'index')}
            git(root, 'read-tree', meta['base'], env=env)
            for name, text in files.items():
                blob = git(root, 'hash-object', '-w', '--stdin', '--no-filters', data=text.encode(), env=env)
                git(root, 'update-index', '--add', '--cacheinfo', '100644', blob, name, env=env)
            tree = git(root, 'write-tree', env=env)
            if head == meta['base']:
                if revision(meta, snapshot(meta)) != accepted:
                    raise PlanningError('proposal changed before commit')
                git(root, 'commit', '-m', 'docs(plan): apply reviewed planning proposal', env=env)
                head = git(root, 'rev-parse', 'HEAD')
            if (git(root, 'rev-parse', head + '^{tree}') != tree
                    or git(root, 'rev-list', '--parents', '-n', '1', head).split() != [head, meta['base']]):
                raise PlanningError('commit hooks or another writer changed the accepted commit tree')
        meta['candidate'] = head
        # The controller persists this even when landing refuses, so a retry can
        # reuse only this exact parent/tree-checked candidate, never another HEAD.
        # The real proposal index still describes the base. Move it only if it
        # remains untouched, using read-tree (no working-file replacement).
        if git(root, 'write-tree') != git(root, 'rev-parse', meta['base'] + '^{tree}'):
            if git(root, 'write-tree') != tree:
                raise PlanningError('proposal index changed during commit')
        else:
            git(root, 'read-tree', head)
        if revision(meta, snapshot(meta)) != accepted:
            raise PlanningError('proposal changed after commit; candidate retained, not landed')
        _target_checks(meta, files)
        reason = landing.land_around_edits(repo, meta['target_branch'], meta['base'], head, require_clean=True)
        if reason:
            raise PlanningError('local landing refused: ' + reason)
        return {'id': meta['id'], 'commit': head, 'status': 'applied', 'files': sorted(files), 'pushed': False}
