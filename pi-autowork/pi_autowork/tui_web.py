"""`tx autowork web`: the pi-autowork TUI in a web browser.

Serves pi_autowork/tui.py with textual-serve (each browser tab runs its own copy of
the app on this machine). Run by `tx autowork web` under
`uv run --with textual==8.2.8 --with textual-serve==1.1.3`. It binds to 127.0.0.1 by
default: the page has the TUI's full control, so reach it from elsewhere through an
SSH tunnel or a private network, or serve it with --view-only.

    python3 tui_web.py --tx PATH --script PATH [--host H] [--port N] [--view-only]
"""
import argparse
import ipaddress
from pathlib import Path
import shlex
import sys

TUI = Path(__file__).with_name('tui.py')


def command(tx, script, view_only=False, python=sys.executable):
    """The command textual-serve runs for each browser session."""
    argv = [python, str(TUI), '--tx', tx, '--script', script] + (['--view-only'] if view_only else [])
    return shlex.join(argv)


def loopback(host):
    if host == 'localhost':
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--tx', required=True)
    parser.add_argument('--script', required=True)
    parser.add_argument('--host', default='127.0.0.1', help='Address to bind (default 127.0.0.1, this machine only).')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--view-only', action='store_true', help='Serve without control keys.')
    args = parser.parse_args(argv)
    if not loopback(args.host) and not args.view_only:
        print(f'tx autowork web: serving full runner control on {args.host}:{args.port}; anyone who can reach it '
              'can stop runners. Use --view-only for a shared network.', file=sys.stderr)
    from textual_serve.server import Server
    Server(command(args.tx, args.script, args.view_only), host=args.host, port=args.port,
           title='pi-autowork').serve()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
