#!/usr/bin/env python3
"""Check an APK's native ABIs; build mode and signing need separate evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile


def verify(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        with zipfile.ZipFile(stream) as archive:
            names = archive.namelist()
            if 'AndroidManifest.xml' not in names:
                raise ValueError('Not an APK: missing root AndroidManifest.xml')
            abis = sorted({parts[1] for name in names
                           if len(parts := name.split('/')) >= 3
                           and parts[0] == 'lib' and name.endswith('.so')})
            if abis != ['arm64-v8a']:
                raise ValueError(f'Expected ARM64-only native libraries; found {abis}')
            if bad := archive.testzip():
                raise ValueError(f'Corrupt APK member: {bad}')
        stream.seek(0)
        digest, size = hashlib.sha256(), 0
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return {'path': str(path), 'bytes': size, 'sha256': digest.hexdigest(), 'abis': abis,
            'checks': ['apk-structure', 'native-abis']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk', type=Path)
    args = parser.parse_args()
    try:
        evidence = verify(args.apk)
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f'APK verification failed: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(evidence))
    return 0


if __name__ == '__main__':
    sys.exit(main())
