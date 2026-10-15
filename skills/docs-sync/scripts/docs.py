#!/usr/bin/env python3
"""Document role manifest: the machine-checkable map of Docs Sync's core owners.

  docs.py validate <repo> [--manifest PATH]   manifest shape and field rules (exit 1 on errors)
  docs.py check <repo> [--manifest PATH]      validate, then check mapped documents, local
                                               links/anchors, documented script paths, covered
                                               paths and unmapped baseline roles
  docs.py stale <repo> [--manifest PATH]      list roles whose covered paths changed after
                                               their verified_at commit (Git history only)
  docs.py profiles                            print each repository-type profile's baseline roles

The manifest defaults to docs/roles.json. Without one, both commands report
`no manifest` and exit 0 so Docs Sync keeps its prose-only behavior. Both commands
are read-only; external URLs are never fetched.
"""
import argparse
import json
from pathlib import Path, PurePosixPath
import os
import re
import subprocess
import sys
from urllib.parse import unquote

DEFAULT_MANIFEST = 'docs/roles.json'
BASELINE = ('readme', 'prd', 'architecture', 'spec', 'test-plan', 'runbook', 'changelog')
# A manifest's optional `profile` replaces BASELINE; keep document-scaffold.md's table in sync.
PROFILES = {
    'service': BASELINE,
    'library': ('readme', 'reference', 'architecture', 'test-plan', 'changelog'),
    'cli-plugin': ('readme', 'reference', 'install-upgrade', 'troubleshooting', 'architecture',
                   'test-plan', 'changelog'),
    'application': ('readme', 'prd', 'architecture', 'spec', 'test-plan', 'user-guide',
                    'troubleshooting', 'changelog'),
    'infrastructure': ('readme', 'architecture', 'runbook', 'test-plan', 'changelog'),
}
MAPPED = {'maintained', 'created', 'unchanged_verified', 'created_with_open_questions'}
UNMAPPED = {'conditional_not_applicable', 'not_applicable'}
FIELDS = {'status', 'path', 'reason', 'covers', 'verified_at'}
COMMIT = re.compile(r'^[0-9a-f]{7,40}$')
FENCE = re.compile(r'^[ \t]{0,3}(`{3,}|~{3,})[^\n]*\n.*?(?:^[ \t]{0,3}\1[`~]*[ \t]*$|\Z)', re.M | re.S)
CODE = re.compile(r'`([^`\n]+)`')
LINK = re.compile(r'!?\[[^\]\n]*\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"\n]*")?\s*\)')
SCRIPT = re.compile(r'(?:^|\s)(?:python3?|sh|bash|node)\s+(?:-\S+\s+)*([^\s`]+\.(?:py|sh|mjs|js))(?=\s|$)')
HEADING = re.compile(r'^(?:#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*|(?![ \t]*[-=>*+#|])([^\n]*\S[^\n]*)\n[ \t]{0,3}(?:=+|-+)[ \t]*)$', re.M)
REFERENCE = re.compile(r'^[ \t]{0,3}\[[^\]\n]+\]:[ \t]*<?([^\s>]+)>?', re.M)
CD = re.compile(r'(?:^|[;&|]\s*)cd\s+([^\s;&|]+)')
HTML_ANCHOR = re.compile(r'<a\s[^>]*?\b(?:id|name)\s*=\s*["\']([^"\']+)["\']', re.I)


def relative(value):
    """A repository-relative POSIX path, or None when it would escape the repository."""
    if not isinstance(value, str) or not value or '\\' in value:
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts:
        return None
    return path


def validate(data):
    if not isinstance(data, dict):
        return ['manifest: must be a JSON object']
    errors = []
    if type(data.get('version')) is not int or data['version'] != 1:
        errors.append('manifest: unsupported version (expected 1)')
    if 'profile' in data and (not isinstance(data['profile'], str) or data['profile'] not in PROFILES):
        errors.append(f'manifest: unknown profile (expected one of {", ".join(PROFILES)})')
    roles = data.get('roles')
    if not isinstance(roles, dict):
        return errors + ['manifest: roles must be an object keyed by role name']
    for role, entry in roles.items():
        if not isinstance(entry, dict):
            errors.append(f'{role}: entry must be an object')
            continue
        errors += [f'{role}: unknown field {key}' for key in sorted(set(entry) - FIELDS)]
        status = entry.get('status')
        if status in MAPPED:
            path = entry.get('path')
            if path is None:
                errors.append(f'{role}: path is required for status {status}')
            elif relative(str(path).split('#', 1)[0] if isinstance(path, str) else path) is None:
                errors.append(f'{role}: path {path!r} must stay inside the repository')
        elif status in UNMAPPED:
            if not isinstance(entry.get('reason'), str) or not entry['reason'].strip():
                errors.append(f'{role}: reason is required for status {status}')
            if 'path' in entry:
                errors.append(f'{role}: status {status} must not map a path')
        else:
            errors.append(f'{role}: unknown status {status!r}')
        covers = entry.get('covers', [])
        if not isinstance(covers, list):
            errors.append(f'{role}: covers must be a list of repository paths')
        else:
            errors += [f'{role}: covered path {item!r} must stay inside the repository'
                       for item in covers if relative(item) is None]
        if 'verified_at' in entry and not (isinstance(entry['verified_at'], str)
                                           and COMMIT.match(entry['verified_at'])):
            errors.append(f'{role}: verified_at must be a 7-40 character hexadecimal commit')
    return errors


def symlinked(repo, path):
    return any((repo / part).is_symlink() for part in (path, *path.parents) if part.parts)


def slug(text):
    text = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'[`*~]|<[^>]+>|(?<!\w)_+|_+(?!\w)', '', text).strip().lower()
    return re.sub(r'[^\w\- ]', '', text).replace(' ', '-')


def anchors(text):
    prose = FENCE.sub('', text)
    seen, result = {}, {name.lower() for name in HTML_ANCHOR.findall(prose)}
    for atx, setext in HEADING.findall(prose):
        base = slug(atx or setext)
        count = seen.get(base, 0)
        seen[base] = count + 1
        result.add(base if count == 0 else f'{base}-{count}')
    return result


class Repo:
    def __init__(self, root):
        self.root = root
        self.texts = {}

    def text(self, path):
        if path not in self.texts:
            try:
                self.texts[path] = (self.root / path).read_text(encoding='utf-8', errors='replace')
            except OSError:
                self.texts[path] = ''
        return self.texts[path]

    def problem(self, path):
        try:
            if symlinked(self.root, path):
                return 'refusing symlinked path'
            if not (self.root / path).exists():
                return 'does not exist'
        except OSError as error:
            return f'cannot be inspected ({error.__class__.__name__})'
        return None

    def anchor_missing(self, path, anchor):
        return (anchor and path.suffix.lower() == '.md' and (self.root / path).is_file()
                and unquote(anchor).lower() not in anchors(self.text(path)))


def check_document(repo, role, path):
    errors = []
    prose = FENCE.sub('', repo.text(path))
    spans = CODE.findall(prose)
    linkable = CODE.sub('', prose)
    for target in LINK.findall(linkable) + REFERENCE.findall(linkable):
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('//'):
            continue
        file, _, anchor = target.partition('#')
        file = file.split('?', 1)[0]
        if not file:
            if repo.anchor_missing(path, anchor):
                errors.append(f'{role}: {path}: missing anchor #{anchor}')
            continue
        # A leading slash is repository-root relative, as GitHub renders it.
        base = PurePosixPath() if file.startswith('/') else path.parent
        parts = _normalize(base / unquote(file).lstrip('/'))
        resolved = PurePosixPath(*parts) if parts else None
        if resolved is None or repo.problem(resolved):
            errors.append(f'{role}: {path}: broken link {target}')
        elif repo.anchor_missing(resolved, anchor):
            errors.append(f'{role}: {path}: missing anchor {target}')
    for span in spans:
        moves = CD.findall(span)
        if any(relative(move) is None or re.search(r'[<>${}*~]', move) for move in moves):
            continue  # A script run from an unknowable directory cannot be checked.
        bases = [PurePosixPath(), path.parent, *(PurePosixPath(move) for move in moves)]
        for script in SCRIPT.findall(span):
            candidate = relative(script)
            if candidate is None or re.search(r'[<>${}*]', script):
                continue
            if all(repo.problem(base / candidate) for base in bases):
                errors.append(f'{role}: {path}: documented script {script} does not exist')
    return errors


def _normalize(path):
    """Collapse `..` in a document-relative link; empty parts mean it escaped the repository."""
    parts = []
    for part in PurePosixPath(path).parts:
        if part == '..':
            if not parts:
                return ()
            parts.pop()
        elif part != '.':
            parts.append(part)
    return parts


def check(root, data):
    repo, errors, documents = Repo(root), [], {}
    for role, entry in data['roles'].items():
        if 'path' in entry:
            file, _, anchor = entry['path'].partition('#')
            path = PurePosixPath(file)
            problem = repo.problem(path)
            if problem == 'does not exist':
                errors.append(f'{role}: {entry["path"]}: mapped document does not exist')
            elif problem:
                errors.append(f'{role}: {entry["path"]}: {problem}')
            elif not (root / path).is_file():
                errors.append(f'{role}: {entry["path"]}: mapped document is not a file')
            else:
                if repo.anchor_missing(path, anchor):
                    errors.append(f'{role}: {entry["path"]}: missing anchor')
                documents.setdefault(path, role)
        for item in entry.get('covers', []):
            problem = repo.problem(PurePosixPath(item))
            if problem:
                errors.append(f'{role}: covered path {item} {problem}')
    for path, role in documents.items():
        errors += check_document(repo, role, path)
    errors += [f'{role}: baseline role is neither mapped nor recorded as not applicable'
               for role in PROFILES.get(data.get('profile'), BASELINE) if role not in data['roles']]
    return errors


def git(root, *args):
    """Read the requested checkout's history; inherited Git overrides must not redirect it."""
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    return subprocess.run(['git', '--literal-pathspecs', '-C', str(root), *args], env=env,
                          capture_output=True, text=True, timeout=60)


def stale(root, data):
    if git(root, 'rev-parse', '--verify', '--quiet', 'HEAD^{commit}').returncode:
        return [f'repository: {root} is not a Git repository with commits']
    errors = []
    for role, entry in data['roles'].items():
        covers = entry.get('covers', [])
        if not covers:
            continue
        commit = entry.get('verified_at')
        if commit is None:
            errors.append(f'{role}: unverifiable: no verified_at commit')
        elif git(root, 'rev-parse', '--verify', '--quiet', f'{commit}^{{commit}}').returncode:
            errors.append(f'{role}: unverifiable: {commit} is not a known commit')
        elif git(root, 'merge-base', '--is-ancestor', commit, 'HEAD').returncode:
            errors.append(f'{role}: unverifiable: {commit} is not an ancestor of HEAD')
        else:
            changes = git(root, 'log', '--format=%h', f'{commit}..HEAD', '--', *covers).stdout.split()
            if changes:
                errors.append(f'{role}: stale since {commit}: {len(changes)} covered-path '
                              f'commit(s): {" ".join(changes)}')
    return errors


def load(root, manifest):
    path = relative(manifest)
    if path is None:
        return None, ['manifest: path must stay inside the repository']
    if symlinked(root, path):
        return None, ['manifest: refusing symlinked manifest']
    file = root / path
    if not file.exists():
        return None, []
    try:
        return json.loads(file.read_text(encoding='utf-8')), []
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        return None, [f'manifest: invalid JSON ({error.__class__.__name__})']
    except OSError as error:
        return None, [f'manifest: cannot read ({error.__class__.__name__})']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=('validate', 'check', 'stale', 'profiles'))
    parser.add_argument('repo', nargs='?')
    parser.add_argument('--manifest', default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    if args.command == 'profiles':
        print(json.dumps({name: list(roles) for name, roles in PROFILES.items()}, indent=2))
        return 0
    if args.repo is None:
        parser.error(f'{args.command} requires a repository path')
    root = Path(args.repo).resolve()
    if not root.is_dir():
        print(f'repository {args.repo} is not a directory')
        return 1
    data, errors = load(root, args.manifest)
    if data is None and not errors:
        print(f'no manifest at {args.manifest}; nothing to check')
        return 0
    if not errors:
        errors = validate(data)
    if not errors and args.command == 'check':
        errors = check(root, data)
    if not errors and args.command == 'stale':
        errors = stale(root, data)
    for error in errors:
        print(error)
    if not errors:
        print('ok')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
