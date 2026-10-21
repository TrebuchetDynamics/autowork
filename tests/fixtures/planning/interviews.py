#!/usr/bin/env python3
"""Prepare bounded multi-turn interview specimens; score decisions and traces manually."""
import argparse
import hashlib
import json
from pathlib import Path

from scenarios import EASY, FILES, snapshot

# Replies are evaluator inputs, not instructions supplied in the model's first turn.
# Send each only after inspecting the preceding answer. Never fabricate model turns.
CASES = {
    'two-decisions': {
        'request': 'Plan a formatter improvement: decide capitalization and blank-input behavior with me. '
                   'Both affect our users and neither is decided. Routine implementation details are yours.',
        'replies': ['Preserve capitalization.', 'Reject blank input with a clear error.'],
        'observe': 'After capitalization is settled, ask about blank-input consequences. Then save both '
                   'decisions and concrete acceptance without filler or code changes.',
    },
    'vague-intent': {
        'request': 'Questions only: make this formatter easier for people like me.',
        'replies': ['Last time, a whitespace-only row silently became an empty record and I missed it. '
                    'I want that row rejected with an error. Everything else should stay as it is.',
                    'Yes, reject empty rows too. Finish.'],
        'observe': 'First elicit a real situation/outcome, not an arbitrary option menu. Reuse the '
                   'example as acceptance; clarify a material empty-row distinction if needed, otherwise '
                   'finish without filler. Send the final reply only if that distinction is asked. No writes.',
    },
    'fully-specified': {
        'request': EASY + ' No other behavior changes; choose routine details.',
        'replies': [],
        'observe': 'No interview or repeated acceptance question; save complete FMT-01, not implementation.',
    },
    'ambiguous-round': {
        'request': 'Resume our interview. Your previous round proposed two separate recommendations: '
                   '1) lowercase normalized text; 2) drop blank records from exports. Neither was '
                   'accepted. My reply to that round is: yes.',
        'replies': ['Accept 1 only; 2 is still undecided.', 'Skip the blank-record choice and finish.'],
        'observe': 'Bare yes settles neither choice. Clarify its scope, then preserve explicit choice 1 '
                   'without promoting 2. Finish leaves only affected export work pending.',
    },
    'shared-constraint': {
        'request': 'Plan three independent improvements together: normalization in src/formatting.py, '
                   'pipe-delimited export in src/export.py, and a raw-string length helper in src/length.py. '
                   'Normalize keeps capitalization and trims edges; export joins fields with pipes; '
                   'length counts characters, including spaces. Only one product issue is open: '
                   'normalization and export must share the same policy for whitespace-only records. '
                   'Choose routine engineering details; inspect existing code for facts.',
        'replies': ['Reject whitespace-only records with a clear error in both; length is unaffected.'],
        'observe': 'Ask shared policy once, bind its answer to both tasks, preserve independent length '
                   'readiness and avoid repository-fact or routine-authority questions.',
    },
    'stop-resume': {
        'request': 'Plan capitalization and blank-input behavior with me; both are undecided. '
                   'Implementation details are yours.',
        'replies': ['Lowercase text. Actually, correction: preserve capitalization. Stop now.',
                    'Resume the saved interview; ask only what is still consequential and unresolved.',
                    'Reject blank input with a clear error, and finish.'],
        'observe': 'Stop ends all questioning and saves the corrected capitalization choice, not '
                   'lowercase, with blank behavior open. Resume reads saved decisions, asks only blank '
                   'behavior, and never fabricates acceptance or edits implementation.',
    },
    'delegation': {
        'request': 'Plan capitalization and blank-input behavior with me; both are undecided. '
                   'Use stdlib only, no network; preserve internal whitespace.',
        'replies': ['Preserve capitalization. Plan it for me: you decide the blank-input policy '
                    'within those constraints.'],
        'observe': 'After the first useful inquiry, honor the explicit switch without restarting '
                   'discovery or asking for repeat approval. Reuse the capitalization answer and '
                   'constraints; distinguish delegated blank policy from user requirements. '
                   'Save planning only; do not dispatch.',
    },
    'builder-followup': {
        'request': 'Questions only. We already accepted preserving capitalization and rejecting blank '
                   'input. Builder review asks (a) which function name to use, (b) whether preserving '
                   'capitalization is intended, and (c) whether an invalid row rejects the whole batch '
                   'or only itself. Only (c) is a new product decision. Continue the interview.',
        'replies': ['Reject only that row and report its position; keep valid rows. Finish.'],
        'observe': 'Bring only unanswered consequential batch failure behavior to the user, not '
                   'settled capitalization or internal naming. No blanket implementation approval.',
    },
}
ENTRYPOINTS = {
    'native': 'skills/plan-with-me/SKILL.md',
    'portable': 'adapters/skills/plan-with-me/SKILL.md',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'inspect'))
    parser.add_argument('root', type=Path)
    parser.add_argument('--cases', help='comma-separated scenarios (default: all)')
    parser.add_argument('--entrypoints', default='native,portable')
    args = parser.parse_args()
    root = args.root.resolve()
    source = Path(__file__).resolve().parents[3]
    cases = args.cases.split(',') if args.cases else CASES
    entries = args.entrypoints.split(',')
    # Fail on an unknown selector before creating any specimens.
    for case in cases:
        CASES[case]
    for entry in entries:
        ENTRYPOINTS[entry]
    if args.action == 'prepare':
        root.mkdir(parents=True, exist_ok=False)
    results = []
    for entry in entries:
        for case in cases:
            name = f'{entry}-{case}'
            fixture = root / name
            before_path = root / f'{name}.before.json'
            if args.action == 'prepare':
                for path, text in FILES.items():
                    dest = fixture / path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(text)
                before_path.write_text(json.dumps(snapshot(fixture), indent=2))
                (root / f'{name}.request.txt').write_text(
                    f'Load and follow actual entrypoint {source / ENTRYPOINTS[entry]} and its relevant '
                    f'references. Work only inside {fixture}; source checkout is read-only. '
                    'No network, installs, commits, dispatch or external execution. This is a real '
                    'bounded interview; wait for my replies when asking a question.\n'
                    + CASES[case]['request'] + '\n')
                (root / f'{name}.driver.json').write_text(json.dumps(CASES[case], indent=2))
                results.append(name)
            else:
                before = json.loads(before_path.read_text())
                after = snapshot(fixture)
                changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
                allowed = set() if case in ('vague-intent', 'builder-followup') else {'docs/plan.md', 'TODO.md'}
                results.append({'case': name, 'changed': changed,
                                'outside_planning_owners': [p for p in changed if p not in allowed]})
    if args.action == 'prepare':
        closure = [source / p for p in ENTRYPOINTS.values()]
        closure += list((source / 'skills/shared').glob('*.md'))
        (root / 'source-sha256.json').write_text(json.dumps(
            {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest() for p in closure}, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
