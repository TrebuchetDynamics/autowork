"""`autowork plan`: shared planning controller, usable without Textual or a service."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
import signal
import sys
import threading

from .planning_views import event_text, history_text, preview_text, roadmap_text


def add_parser(sub):
    p = sub.add_parser('plan', help='plan, discuss, investigate and review proposals through Pi RPC')
    p.add_argument('target', nargs='?', default='.', help='runner name or repository path')
    p.add_argument('--objective', default='', help='optional direction; empty discovers useful work')
    p.add_argument('--message', default='', help='follow-up for --session (literal text, not a shell command)')
    p.add_argument('--session', help='resume this project-bound session ID')
    p.add_argument('--task', help='scope discussion or investigation to this task')
    p.add_argument('--mode', choices=('plan', 'discuss', 'investigate'), default='plan')
    p.add_argument('--model', help='Pi provider/model for a new session')
    p.add_argument('--json', action='store_true', help='one JSON result; progress goes to stderr')
    p.add_argument('--interactive', action='store_true', help='chat/steer live; /cancel /preview /roadmap /apply REV /quit')
    operations = p.add_mutually_exclusive_group()
    operations.add_argument('--list', action='store_true', help='list private planning sessions; no model call')
    operations.add_argument('--history', action='store_true', help='read saved conversation; requires --session')
    operations.add_argument('--preview', action='store_true', help='validate and show proposed diff; requires --session')
    operations.add_argument('--apply', metavar='REV', help='explicitly accept this reviewed revision; local commit, no push')
    operations.add_argument('--roadmap', action='store_true', help='read goals and dependency diagram; no model call')
    operations.add_argument('--legacy', action='store_true', help='open the original external-agent planner instead')
    return p


def run(args, repo, state_root, *, planner_factory=None):
    if (args.apply is not None or args.preview or args.history or args.message) and not args.session:
        print('autowork plan: this operation requires --session ID', file=sys.stderr)
        return 1
    if args.interactive and (args.json or not sys.stdin.isatty()):
        print('autowork plan: --interactive requires a terminal and cannot use --json', file=sys.stderr)
        return 1
    if args.session and (args.objective or args.task or args.model or args.mode != 'plan'):
        print('autowork plan: a resumed session keeps its scope; use --message for new direction', file=sys.stderr)
        return 1
    try:
        if planner_factory is None:
            from .planning import Planner
            planner_factory = Planner
        planner = planner_factory(repo, state_root=state_root, pi=os.environ.get('AUTOWORK_PI', 'pi'), model=args.model)
        sid = args.session
        if args.list:
            result = planner.sessions()
            display = '\n'.join(f'{s["id"]}  {s.get("status", "")}  {s.get("objective", "")}' for s in result)
        elif args.history:
            result = planner.history(sid)
            display = history_text(result)
        elif args.preview:
            result = planner.preview(sid)
            display = preview_text(result)
        elif args.apply is not None:
            if not args.apply.strip():
                raise ValueError('--apply needs the nonempty revision shown by --preview')
            result = planner.apply(sid, args.apply)
            display = 'Applied locally: ' + str(result.get('commit', '')) + ' (not pushed; runner state unchanged)'
        elif args.roadmap:
            result = planner.roadmap(sid)
            display = roadmap_text(result)
        elif sid and not args.message:
            result = planner.history(sid)
            display = history_text(result)
            if args.interactive:
                print(display)
                return _chat(planner, sid)
        else:
            if not sid:
                sid = planner.create(objective=args.objective, task=args.task, mode=args.mode)['id']
            print(f'Planning session: {sid}', file=sys.stderr)
            if args.interactive:
                return _chat(planner, sid, initial_message=args.message, start=True)
            result = _turn(planner, sid, args.message)
            result = {**result, 'id': sid}
            display = result.get('text', '')
        print(json.dumps(result, indent=2) if args.json else display)
        return 1 if isinstance(result, dict) and (result.get('status') in ('failed', 'error', 'cancelled')
                                                 or result.get('valid') is False) else 0
    except (OSError, ValueError, RuntimeError) as error:
        print(f'autowork plan: {error}', file=sys.stderr)
        return 1


def _turn(planner, sid, message, cancel=None):
    cancel = cancel or threading.Event()
    previous = None
    if threading.current_thread() is threading.main_thread():
        previous = signal.signal(signal.SIGINT, lambda *_: cancel.set())
    def progress(event):
        text = event_text(event)
        if text:
            print(text, end='', file=sys.stderr, flush=True)
    try:
        return planner.send(sid, message, on_event=progress, cancel=cancel)
    finally:
        if previous is not None:
            signal.signal(signal.SIGINT, previous)


def _chat(planner, sid, *, initial_message='', start=False):
    print('Discuss with the planner. During a turn, text steers it. '
          '/steer TEXT /cancel /preview /roadmap /history /apply REV /quit. Ctrl+C cancels a turn.')
    cancel = threading.Event()
    future = None
    def turn(message):
        try:
            result = _turn(planner, sid, message, cancel)
            print('\n' + result.get('text', '') + '\n[' + result.get('status', 'unknown') + ']', flush=True)
        except (OSError, ValueError, RuntimeError) as error:
            print(f'Planning: {error}', file=sys.stderr, flush=True)
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix='planning-chat') as pool:
        if start:
            future = pool.submit(turn, initial_message)
        try:
            while True:
                try:
                    message = input('Plan> ')
                except KeyboardInterrupt:
                    if future is not None and not future.done():
                        cancel.set()
                        print('\nCancellation requested; wait for the turn to stop.')
                        continue
                    return 0
                except EOFError:
                    return 0
                if message == '/quit':
                    return 0
                try:
                    active = future is not None and not future.done()
                    if message == '/cancel':
                        cancel.set()
                        print('Cancellation requested; proposal/history retained.')
                    elif message == '/preview':
                        print(preview_text(planner.preview(sid)))
                    elif message == '/roadmap':
                        print(roadmap_text(planner.roadmap(sid)))
                    elif message == '/history':
                        print(history_text(planner.history(sid)))
                    elif message.startswith('/apply '):
                        if active:
                            raise ValueError('wait for or cancel the active turn before Apply')
                        print(json.dumps(planner.apply(sid, message[7:].strip()), indent=2))
                    elif message.strip():
                        if message.startswith('/steer '):
                            message = message[7:]
                            if not active:
                                raise ValueError('no active turn to steer; send a normal message')
                        if active:
                            planner.steer(sid, message)
                            print('Steering queued (not yet completed).')
                        else:
                            cancel = threading.Event()
                            future = pool.submit(turn, message)
                except (OSError, ValueError, RuntimeError) as error:
                    print(f'Planning: {error}', file=sys.stderr)
        finally:
            cancel.set()
            print('\nSession retained: ' + sid)
            # Executor waits for the controller to finish its bounded child cleanup.
