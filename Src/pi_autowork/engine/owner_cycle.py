#!/usr/bin/env python3
"""Select and execute repository TODO work directly; no Kanban backend."""
from pi_autowork.engine.task_execution import main

def _compat_main(argv):
    import sys
    previous = sys.argv
    sys.argv = [previous[0], *argv]
    try:
        raise SystemExit(main())
    finally:
        sys.argv = previous
