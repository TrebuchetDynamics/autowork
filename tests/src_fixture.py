"""Private selected-release copies; no synthesized product implementations or Git state."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def copy_sources(destination, *, source=ROOT, entries=()):
    """Copy the complete Python source closure plus explicitly needed resources.

    Keep old public entries, including standalone hooks, alongside Src owners. Never
    borrow a missing source from the calling checkout when the selected copy is used.
    """
    source, destination = Path(source).resolve(), Path(destination)
    paths = set(source.glob('*.py'))
    for folder in ('Src', 'pi-autowork/pi_autowork', 'pi-autowork/engine'):
        paths.update(p for p in (source / folder).rglob('*.py')
                     if not p.name.startswith('test_') and '__pycache__' not in p.parts)
    paths.update(source / entry for entry in entries)
    for path in sorted(paths):
        if not path.resolve().is_relative_to(source):
            raise ValueError(f'source escapes selected release: {path}')
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    return destination
