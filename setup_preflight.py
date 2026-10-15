"""Read-only admission checks for the explicit fleet installer.

Never load Hermes plugins: discovery can apply runtime policy to live profiles.
"""
import ast
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys


def source_available(source):
    try:
        result = subprocess.run(['git', 'ls-remote', '--exit-code', source, 'HEAD'],
                                capture_output=True, timeout=30,
                                env=dict(os.environ, GIT_TERMINAL_PROMPT='0'))
        return result.returncode == 0
    except (OSError, TimeoutError, subprocess.TimeoutExpired):
        return False


def selected_source():
    """Read supported shell launchers without executing bootstrap/repair code."""
    executable = shutil.which('hermes')
    if not executable:
        return None
    path = Path(executable)
    for _ in range(5):
        path = path.resolve()
        text = path.read_text()
        if text.startswith('#!/bin/sh') or text.startswith('#!/usr/bin/env sh'):
            words = shlex.split(text.split('\n', 1)[1], comments=True)
            if not words or words[0] != 'exec' or len(words) < 2:
                return None
            if '-c' in words:
                tree = ast.parse(words[words.index('-c') + 1])
                for node in ast.walk(tree):
                    if (isinstance(node, ast.Call) and ast.unparse(node.func) == 'sys.path.insert'
                            and len(node.args) == 2 and isinstance(node.args[1], ast.Constant)
                            and isinstance(node.args[1].value, str)):
                        candidate = Path(node.args[1].value)
                        if candidate.is_absolute() and (candidate / 'hermes_cli/plugins.py').is_file():
                            return candidate
                return None
            if not Path(words[1]).is_absolute() or words[2:] != ['$@']:
                return None
            path = Path(words[1])
            continue
        # Traditional checkout launch scripts live alongside their source.
        for candidate in (path.parent, *path.parents):
            if (candidate / 'hermes_cli/plugins.py').is_file():
                return candidate
        return None
    return None


def runtime_check(repo, root, profiles, bundle_only):
    """Find Hermes source/interpreter without invoking its stateful CLI."""
    roots = list(dict.fromkeys([root, Path.home() / '.hermes']))
    try:
        source = selected_source()
    except (OSError, ValueError, SyntaxError, UnicodeError):
        source = None
    if source is None:
        return ['Cannot resolve source for Hermes selected on PATH; compatibility unverified']
    errors = []
    try:
        tree = ast.parse((source / 'hermes_cli/plugins.py').read_text())
        methods = {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        inject = methods.get('inject_message')
        if inject is None or 'origin' not in {a.arg for a in [*inject.args.args, *inject.args.kwonlyargs]}:
            errors.append('Hermes lacks inject_message(origin=...) support')
        content = source / 'hermes_cli/plugins_content.py'
        if 'register_skill' not in methods and not (content.is_file() and any(
                isinstance(n, ast.FunctionDef) and n.name == 'register_skill'
                for n in ast.walk(ast.parse(content.read_text())))):
            errors.append('Hermes lacks register_skill support')
        candidates = [source / '.venv/bin/python']
        for r in roots:
            for facts in r.glob('installs/*/facts.json'):
                data = json.loads(facts.read_text())
                candidates.append(Path(data['packages']['venv']['environment']) / 'bin/python')
        candidates.append(Path(sys.executable))
        for executable in dict.fromkeys(candidates):
            if not executable.is_file():
                continue
            command = [str(executable), '-B', str(repo / 'scripts/preflight_config.py'),
                       *(['--core'] if bundle_only else []), *[str(home / 'config.yaml') for _, home in profiles]]
            result = subprocess.run(command, capture_output=True, text=True, timeout=30,
                                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            if result.returncode == 3:  # this interpreter lacks a strict YAML parser
                continue
            if result.returncode:
                errors.append(result.stdout.strip() or 'Profile configuration validation failed')
            break
        else:
            errors.append('No Hermes Python with ruamel.yaml available for strict configuration validation')
    except (OSError, ValueError, KeyError, SyntaxError, subprocess.TimeoutExpired):
        errors.append('Cannot inspect Hermes runtime/configuration safely')
    return errors


def preflight(repo, root, profiles, *, bundle_only=False):
    errors, plan = [], []
    if sys.version_info < (3, 12):
        errors.append('Setup requires Python 3.12 or newer')
    for binary in ('bash', 'python3', 'hermes', *(() if bundle_only else ('git',))):
        if not shutil.which(binary):
            errors.append(f'Required executable missing: {binary}')
    required = ('install-skills.sh', 'install-plugins.sh', 'install_skills.py', 'runtime_defaults.py',
                'plugin.yaml', 'plugins/defaults.json', 'plugins/PLUGINS.md', 'scripts/preflight_config.py')
    for name in required:
        if not (repo / name).is_file():
            errors.append(f'Missing setup file: {name}')
    if errors:
        return {'errors': errors, 'plan': plan}
    errors.extend(runtime_check(repo, root, profiles, bundle_only))
    # Reuse the provisioner's actual path and completeness checks without writes.
    import importlib.util
    spec = importlib.util.spec_from_file_location('preflight_skills', repo / 'install_skills.py')
    provisioner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(provisioner)
    messages = []
    try:
        if provisioner.install(repo / 'skills', profiles, dry_run=True, report=messages.append):
            errors.extend(m for m in messages if m.startswith('Failed:'))
    except (ValueError, OSError) as exc:
        errors.append(str(exc))
    plan.extend(messages)
    defaults = json.loads((repo / 'plugins/defaults.json').read_text())['hermes']
    settings = {
        'approvals.mode': defaults['approvals_mode'],
        'approvals.destructive_slash_confirm': defaults['destructive_slash_confirm'],
        'approvals.mcp_reload_confirm': defaults['mcp_reload_confirm'],
        'agent.max_turns': defaults['max_turns'],
        'skills.platform_disabled': defaults['skills_platform_disabled'],
        'plugins.entries.hermes-toolset.allow_gateway_injection': defaults['allow_gateway_injection'],
    }
    spec = importlib.util.spec_from_file_location('preflight_runtime_defaults', repo / 'runtime_defaults.py')
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    for name, home in profiles:
        plan.append(f'Profile {name}: {home}')
        for relative in ('config.yaml', 'plugins', 'skills'):
            path = home / relative
            if path.is_symlink():
                errors.append(f'{name}: shared/symlinked installation path: {relative}')
            if path.exists() and not os.access(path, os.W_OK):
                errors.append(f'{name}: unwritable path: {relative}')
        if not os.access(home, os.W_OK):
            errors.append(f'{name}: unwritable profile home')
        plugins = home / 'plugins'
        if plugins.exists() and not plugins.is_dir():
            errors.append(f'{name}: plugins must be a directory')
        target = plugins / 'hermes-toolset'
        if target.exists() or target.is_symlink():
            if not (target / 'plugin.yaml').is_file():
                errors.append(f'{name}: existing bundle path is not a complete plugin')
            elif target.resolve() != repo.resolve():
                errors.append(f'{name}: bundle points to another checkout; update/remove it explicitly before fleet setup')
            plan.append(f'  Preserve existing bundle path: {target}')
        else:
            plan.append(f'  Link bundle: {target} -> {repo}')
        opted_out = runtime.setup_opted_out(home / 'config.yaml')
        if opted_out is None:
            errors.append(f'{name}: cannot verify the runtime-defaults opt-out without PyYAML')
        elif opted_out:
            plan.append('  Enable hermes-toolset; runtime-defaults opt-out: bundle policy settings skipped')
        else:
            plan.append('  Enable hermes-toolset; apply settings: ' + json.dumps(settings, sort_keys=True))
        plan.append('  Existing skill copies are preserved; auth and conversation history unchanged')
        if bundle_only:
            plan.append('  External integrations and memory unchanged')
    # Existing dry-run adapters validate the source manifest and OMH isolation
    # without starting Hermes, installing CLIs, or writing profile data.
    command = ['bash', str(repo / 'install-plugins.sh'), '--sources-only', '--setup', '--enable',
               '--dry-run', '--hermes-home', str(root)]
    if bundle_only:
        command.append('--bundle-only')
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60,
                                env=dict(os.environ, HERMES_HOME=str(root), PYTHONDONTWRITEBYTECODE='1'))
        if result.returncode:
            errors.append('Installer prerequisite preview failed: ' + (result.stderr.strip() or result.stdout.strip()))
        else:
            plan.extend(result.stdout.strip().splitlines())
    except (OSError, subprocess.TimeoutExpired):
        errors.append('Installer prerequisite preview could not complete')
    if not bundle_only:
        if not shutil.which('uv') and any(not shutil.which(binary) for binary in ('omh', 'graphify')):
            errors.append('uv is required when OMH or Graphify is not installed')
        spec = importlib.util.spec_from_file_location('preflight_omh', repo / 'install-omh.py')
        omh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(omh)
        try:
            for name, _ in profiles:
                store = omh.profile_plan(root, name, omh.read_defaults())['store'].resolve()
                parent = store
                while not parent.exists() and parent != parent.parent:
                    parent = parent.parent
                if not parent.is_dir() or not os.access(parent, os.W_OK | os.X_OK):
                    errors.append(f'{name}: invalid or unwritable OMH store destination: {store}')
        except (omh.SetupError, ValueError, OSError) as exc:
            errors.append('OMH store validation failed: ' + str(exc))
        # Catalog OMH uses this official upstream; other sources are explicit URLs.
        sources = {'https://github.com/rlaope/oh-my-hermes'}
        for line in (repo / 'plugins/PLUGINS.md').read_text().splitlines():
            sources.update(word for word in line.split() if word.startswith('https://github.com/'))
        if not errors:
            for source in sorted(sources):
                if not source_available(source):
                    errors.append(f'Dependency source unreachable: {source}')
                else:
                    plan.append(f'  Source reachable: {source}')
        plan.append('  Full setup configures OMH memory; existing stores are preserved (see per-profile preview)')
        plan.append('  Native dependency scans still run at install time; source reachability is not scan approval')
    return {'errors': errors, 'plan': plan}


def print_plan(report):
    print('Preflight: proposed fleet changes', flush=True)
    for line in report['plan']:
        print(line, flush=True)
    for error in report['errors']:
        print('BLOCKED: ' + error, flush=True)
    print('Preflight failed; no installation stages started.' if report['errors'] else
          'Preflight passed. Later network, scanner or runtime failures can still cause partial setup.', flush=True)
