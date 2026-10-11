"""Strict, read-only YAML validation in Hermes's Python; never imports Hermes."""
import sys
from pathlib import Path


def main(args):
    try:
        from ruamel.yaml import YAML
    except ImportError:
        return 3
    core = '--core' in args
    yaml = YAML(typ='safe')
    yaml.allow_duplicate_keys = False
    failed = False
    for name in (x for x in args if x != '--core'):
        path = Path(name)
        try:
            config = yaml.load(path.read_text()) if path.exists() else {}
            if config is None:
                config = {}
            if not isinstance(config, dict):
                raise ValueError()
            for key in ('plugins', 'approvals', 'skills', 'memory'):
                if key in config and not isinstance(config[key], dict):
                    raise ValueError()
            plugins = config.get('plugins', {})
            entries = plugins.get('entries', {})
            if not isinstance(entries, dict) or any(not isinstance(v, dict) for v in entries.values()):
                raise ValueError()
            if not core and config.get('memory', {}).get('provider') not in (None, '', 'builtin', 'omh'):
                print(f'{path}: existing memory provider conflicts with OMH setup')
                failed = True
        except Exception:
            # Parser exceptions may contain source lines with credentials.
            print(f'{path}: invalid/duplicate YAML or incompatible configuration shape; repair before setup')
            failed = True
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
