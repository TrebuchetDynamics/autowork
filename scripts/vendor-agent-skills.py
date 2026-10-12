#!/usr/bin/env python3
"""Package a reviewed, exact Addy commit. No implicit network or latest updates."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
TREES={'skills','references','docs','agents','commands'}
ROOT_FILES={'README.md','LICENSE','CONTRIBUTING.md'}


def package(source, revision, destination):
    resolved=subprocess.check_output(['git','-C',str(source),'rev-parse',revision+'^{commit}'],text=True).strip()
    if revision != resolved:
        raise ValueError('Use the full reviewed commit SHA, not a branch or tag')
    entries=subprocess.check_output(['git','-C',str(source),'ls-tree','-rz',revision]).split(b'\0')
    files={};skills=[]
    upstream=destination/'upstream'
    prepared=[]
    for entry in entries:
        if not entry:continue
        info,raw=entry.split(b'\t',1);mode,kind,oid=info.split();name=raw.decode()
        path=Path(name)
        if path.parts[0] not in TREES and name not in ROOT_FILES:continue
        if kind!=b'blob' or mode not in (b'100644',b'100755'):raise ValueError('Unsupported entry: '+name)
        # Protocol bytes unchanged; avoid recursive host SKILL discovery/collisions.
        relative=path.with_name('PROTOCOL.md') if path.name=='SKILL.md' else path
        data=subprocess.check_output(['git','-C',str(source),'cat-file','blob',oid.decode()])
        prepared.append((relative,data,int(mode,8)&0o777))
        files[name]={'path':str(Path('upstream')/relative),'sha256':hashlib.sha256(data).hexdigest()}
        if len(path.parts)==3 and path.parts[0]=='skills' and path.name=='SKILL.md':skills.append(path.parts[1])
    if upstream.exists():
        # Only the managed upstream subtree is replaceable; preserve adapter/helpers.
        if upstream.is_symlink():raise ValueError('Symlinked vendor destination')
        shutil.rmtree(upstream)
    for relative,data,mode in prepared:
        target=upstream/relative;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data);target.chmod(mode)
    manifest={'repository':'https://github.com/addyosmani/agent-skills','revision':revision,
              'license':'MIT','skills':sorted(skills),'files':files,
              'transform':'SKILL.md filenames become PROTOCOL.md; file bytes unchanged',
              'included':sorted(TREES|ROOT_FILES),'excluded':'Host manifests/hooks, evals, root scripts and hidden integration directories; never activated by Hermes'}
    (destination/'UPSTREAM.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(f'Packaged {len(skills)} skills and {len(files)} files from {revision}')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True,type=Path);p.add_argument('--revision',required=True)
    a=p.parse_args();package(a.source,a.revision,ROOT/'skills/engineering')
