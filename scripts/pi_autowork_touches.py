"""Compatibility entry point: Touches inference now lives in the pi-autowork component.

Older copied runners call this path; it runs pi-autowork/pi_autowork/touches_inference.py
from the same release.
"""
from pathlib import Path
import runpy
import sys

sys.argv[0] = str(Path(__file__).resolve().parents[1] / 'pi-autowork/pi_autowork/touches_inference.py')
runpy.run_path(sys.argv[0], run_name='__main__')
