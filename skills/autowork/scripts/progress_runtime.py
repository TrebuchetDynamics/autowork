"""Durable local owner mailboxes. Transport is not ownership or execution authority."""
import json
import os
from pathlib import Path
import re
import tempfile


def private_path(path):
    path = Path(path).expanduser().absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('private state must not traverse symlinks')
    return path


def write(path, value):
    path = private_path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.progress-')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def route(request, owner_state):
    owner_state = private_path(owner_state)
    if not owner_state.is_dir():
        raise ValueError('owner state must already exist; do not invent an owner')
    if not request.get('owner') or request['owner'] == 'unassigned':
        raise ValueError('named integration owner required')
    target = request.get('target_session')
    if target is not None and (not isinstance(target, str) or not target.strip()):
        raise ValueError('target_session must be a nonempty observed session ID')
    key = request['request_id']
    if not re.fullmatch(r'[A-Za-z0-9_-]+', key):
        raise ValueError('invalid request ID')
    path = private_path(owner_state/'inbox'/f'{key}.json')
    if path.exists():
        old = json.loads(path.read_text())
        for field in ('request_id','owner','consumer','plan','task_ids','target_session'):
            if old.get(field) != request.get(field):
                raise ValueError('conflicting owner inbox request')
    else:
        # Publish complete bytes atomically; a competing delivery cannot overwrite.
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.delivery-')
        try:
            with os.fdopen(fd,'w') as stream:
                json.dump(request,stream,indent=2)
            os.link(temporary, path)
        finally:
            os.unlink(temporary)
    return {'state':'delivered','inbox_path':str(path),
            'target_session': target, 'session_wakeup':'not_attempted',
            'reply_path':str(owner_state/'outbox'/f'{key}.json'),
            'boundary':'local durable delivery only; not read, acknowledged or authorized'}


def read_reply(request, delivery):
    path = private_path(delivery['reply_path'])
    if not path.exists(): return None
    reply = json.loads(path.read_text())
    if (not isinstance(reply,dict) or reply.get('request_id') != request['request_id']
            or reply.get('owner') != request['owner']
            or reply.get('status') not in ('acknowledged','resolved','blocked')
            or not isinstance(reply.get('evidence'),str) or not reply['evidence'].strip()):
        raise ValueError('owner reply must bind request, owner, status and evidence')
    if request.get('target_session') and reply.get('session_id') != request['target_session']:
        raise ValueError('owner reply must bind the designated target session; same-profile cron evidence is not a parent reply')
    reply = dict(reply)
    if reply['status'] == 'resolved': reply['status'] = 'resolution_reported'
    return reply


def ready_queue(consumer, limit=3):
    """Validate a bounded same-plan frontier; no focus changes or task invention."""
    import retry_selection
    first = retry_selection.select(consumer)
    if first['state'] != 'ready_for_autowork':
        return {'tasks': [], 'selection': first, 'target': limit, 'shortfall': limit}
    goals = retry_selection.goals
    with goals.coordination(consumer) as repo:
        revision = goals.revision(repo)
        data = goals.normalize(goals.load(repo))
        chosen = first['selected_task']
        candidates = [t for t, _ in goals.eligible(data)
                      if t['status'] == 'open' and t['goal'] == chosen['goal']][:limit]
    checked = retry_selection.select(repo, plan=first['plan'], task_ids=[t['id'] for t in candidates])
    if goals.revision(repo) != revision:
        raise ValueError('consumer changed during queue validation')
    if checked['state'] != 'ready_for_autowork':
        # Revalidate the frontier rather than reuse the earlier snapshot.
        fresh = retry_selection.select(consumer)
        tasks = [fresh['selected_task']] if fresh['state'] == 'ready_for_autowork' else []
        return {'tasks': tasks, 'selection': fresh, 'target':limit, 'shortfall':limit-len(tasks),
                'queue_gap':checked['reasons']}
    return {'tasks': candidates, 'selection': checked, 'target':limit, 'shortfall':max(0,limit-len(candidates))}


def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('inbox','reply'))
    parser.add_argument('--state-dir', required=True)
    parser.add_argument('--request-id')
    parser.add_argument('--owner')
    parser.add_argument('--status', choices=('acknowledged','resolved','blocked'))
    parser.add_argument('--evidence')
    parser.add_argument('--session-id', default=os.environ.get('HERMES_SESSION_ID'),
                        help='Observed replying session ID, not a copied target or ownership grant')
    args=parser.parse_args(argv)
    state=private_path(args.state_dir)
    if args.action=='inbox':
        rows=[json.loads(private_path(p).read_text()) for p in sorted((state/'inbox').glob('*.json'))]
        print(json.dumps(rows,indent=2))
        return 0
    if not args.request_id or not re.fullmatch(r'[A-Za-z0-9_-]+',args.request_id):
        parser.error('valid --request-id required')
    request=json.loads(private_path(state/'inbox'/f'{args.request_id}.json').read_text())
    if args.owner != request['owner'] or not args.status or not args.evidence:
        parser.error('exact --owner, --status and actual --evidence required')
    reply={'request_id':args.request_id,'owner':args.owner,'status':args.status,'evidence':args.evidence}
    if request.get('target_session'):
        if args.session_id != request['target_session']:
            parser.error('reply requires the observed designated owner session; a sibling cron cannot answer for it')
        reply['session_id']=args.session_id
    write(state/'outbox'/f'{args.request_id}.json',reply)
    print(json.dumps(reply))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
