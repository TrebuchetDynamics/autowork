"""Test-only recognition of pinned Textual's offline uv cache failures."""
import re


def textual_unavailable(result):
    """Do not turn import errors, pilot assertions or other resolver errors into skips."""
    error = ' '.join(result.stderr.lower().split())
    if result.returncode == 1:
        return (error.startswith('× no solution found when resolving `--with` dependencies:')
                and 'because textual was not found in the cache and you require textual==8.2.8,' in error
                and 'hint: packages were unavailable because the network was disabled.' in error)
    if result.returncode == 2:
        return (error.startswith('error:') and re.search(r'\btextual==8\.2\.8(?![\w.+-])', error) is not None
                and 'offline' in error
                and ('not available in the offline cache' in error
                     or 'was not found in the cache' in error))
    return False
