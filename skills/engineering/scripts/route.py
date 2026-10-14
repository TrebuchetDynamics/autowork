"""Verify one pinned engineering protocol or an explicitly requested phase bundle."""
import argparse
import hashlib
import json
from pathlib import Path

PACK=Path(__file__).resolve().parents[1]
PHASES={
    'plan':['planning-and-task-breakdown','documentation-and-adrs'],
    'implement':['incremental-implementation','test-driven-development'],
    'debug':['debugging-and-error-recovery','test-driven-development'],
    'review':['code-review-and-quality'],
    'document':['documentation-and-adrs'],
    'deliver':['git-workflow-and-versioning'],
}


def route(phase=None, domains=(), pack=PACK, *, protocol=None):
    if protocol is not None:
        if phase is not None or domains:
            raise ValueError('--protocol selects one method; do not combine it with a phase or --domain')
        names = [protocol]
    else:
        if phase not in PHASES:
            raise ValueError('Select --protocol NAME or an explicit phase bundle')
        names = list(dict.fromkeys(PHASES[phase] + list(domains)))
    manifest=json.loads((pack/'UPSTREAM.json').read_text())
    rows=[]
    for name in names:
        if name not in manifest['skills']:raise ValueError('Unknown engineering skill: '+name)
        item=manifest['files'][f'skills/{name}/SKILL.md'];path=pack/item['path']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Vendored protocol changed: '+name)
        rows.append({'name':name,'path':str(path),'sha256':item['sha256']})
    # Shared checklists are part of the same pin; verify but load only relevant ones.
    for name,item in manifest['files'].items():
        if name.startswith('references/'):
            if hashlib.sha256((pack/item['path']).read_bytes()).hexdigest()!=item['sha256']:
                raise ValueError('Vendored reference changed: '+name)
    return {'phase':phase,'revision':manifest['revision'],'adapter':str(pack/'SKILL.md'),'skills':rows,
            'boundary':'Selection is not proof of skill application, execution or completed tasks.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', nargs='?', choices=PHASES, help='opt into a phase bundle')
    p.add_argument('--protocol', help='select exactly one protocol without phase defaults')
    p.add_argument('--domain', action='append', default=[], help='add a protocol to a phase bundle')
    a=p.parse_args()
    try:print(json.dumps(route(a.phase,a.domain,protocol=a.protocol),indent=2))
    except (ValueError,OSError,KeyError) as e:p.exit(1,str(e)+'\n')
