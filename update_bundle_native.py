"""Narrow subprocess adapter to the installed Hermes plugin manager.

Run with the native Hermes interpreter. No scanner consent, profile enablement,
configuration edits, gateway reload, dependency consent or worker restart is added.
Native API absence or refusal is an incomplete deployment, never a fallback copy.
"""
import json
import os
from pathlib import Path
import sys
import tempfile


def main():
    action, home, source, revision = sys.argv[1:]
    source = Path(source).resolve(strict=True)
    os.environ['HERMES_HOME'] = home
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    if action in ('scan', 'install'):
        from hermes_cli import plugins_cmd as native
        if not native._scan_on_install_enabled():
            raise ValueError('Native security scanning is disabled; scoped deployment requires admission')
        if action == 'scan':
            if native._scan_plugin_tree(source, source.as_uri(), force=False) is None:
                raise ValueError('Native scanner did not admit the staged source')
        else:
            # The selected slot has been backed up, so no replacement force is needed.
            # cmd_install performs its own scan, manifest, kill-list and PM admission.
            native.cmd_install(source.as_uri(), force=False, ref=revision, enable=False)
        print(json.dumps({'admitted': True}))
    elif action == 'verify':
        # Loading the bundle provisions skills and can apply runtime policy. Probe
        # in a disposable home so registration never rewrites the selected settings.
        with tempfile.TemporaryDirectory(prefix='toolset-registration-') as directory:
            probe = Path(directory)
            (probe / 'plugins').mkdir()
            (probe / 'plugins/hermes-toolset').symlink_to(source, target_is_directory=True)
            (probe / 'config.yaml').write_text(
                'plugins:\n  enabled: [hermes-toolset]\n  entries:\n'
                '    hermes-toolset:\n      apply_runtime_defaults: false\n')
            os.environ['HERMES_HOME'] = str(probe)
            os.chdir(probe)  # avoid project plugin discovery from the caller's cwd
            from hermes_cli.plugins import get_plugin_manager, get_plugin_commands
            get_plugin_manager().discover_and_load()
            commands = sorted(name for name, row in get_plugin_commands().items()
                              if row.get('plugin') == 'hermes-toolset')
            expected = {path.parent.name.replace('_', '-')
                        for path in (source / 'skills').glob('*/SKILL.md')
                        if path.parent.name not in ('repo-docs', 'repo-interview')}
            expected.add('toolset')
            if not expected.issubset(commands):
                raise ValueError('Native registration probe missing: ' + ', '.join(sorted(expected - set(commands))))
            print(json.dumps({'commands': commands, 'scope': 'isolated native registration probe'}))
    else:
        raise ValueError('Unknown native admission action')


if __name__ == '__main__':
    main()
