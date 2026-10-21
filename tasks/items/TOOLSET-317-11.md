+++
schema = 1
id = "TOOLSET-317-11"
title = "Ignored leftovers in a checkout cannot fail the integration check"
short = "Leftover caches fail integration"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 13000
depends_on = []
touches = ["install_skills.py", "pi-autowork/engine/parallel_integrate.py", "tests/", "pi-autowork/engine/"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "TOOLSET-304-2c's first attempt was held for a failure no candidate caused: the shared integration worktree kept an ignored skills/autowork/scripts/__pycache__/ (102 .pyc files) from before the engine moved out of the skill (2c34e8c8). install_skills.py ignores __pycache__ and *.pyc but copytree still creates their parent directory, so the installed skill had an empty scripts/ and test_engineering_vendor's 'no scripts' assertion failed in that worktree only; the base check, run elsewhere, passed, so it read as the candidate's new failure. Have the installer leave out directories that hold nothing after its ignore patterns, and have the integration worktree drop directories that contain only ignored build caches before a full check."
acceptance = ["tests cover: installing a skill whose folder holds only __pycache__ in a subdirectory creates no such subdirectory; an integration worktree with an orphaned ignored cache directory does not fail the vendor check; tracked and untracked non-cache files are never removed."]
checks = ["python3 -m unittest discover -s tests; python3 scripts/check.py"]
exclusions = []
+++

