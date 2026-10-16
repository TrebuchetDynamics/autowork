#!/usr/bin/env python3
"""Audit a README's local images the way GitHub resolves them.

Extends the pinned upstream audit, whose SVG checks it reuses unchanged. It also
checks `<picture><source srcset>` variants (dark mode), reference-style images
(`![alt][label]`, `![label][]`, `![label]`), root-relative paths (resolved against
the repository root) and `<…>` destinations, and skips images inside fenced code.
Exit 0 when every local image exists and passes, 1 on issues, 2 on usage errors.
"""
import importlib.util
from pathlib import Path
import re
import sys
from urllib.parse import unquote

UPSTREAM = Path(__file__).resolve().parents[1] / 'upstream/scripts/audit_readme.py'
FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})')
DESTINATION = r'(<[^>\n]*>|[^\s()<>]+)'
INLINE_IMAGE = re.compile(r'!\[(?:[^\]\\]|\\.)*\]\(\s*' + DESTINATION + r'(?:\s+[^)]*)?\)')
FULL_REFERENCE = re.compile(r'!\[((?:[^\]\\]|\\.)*)\]\[((?:[^\]\\]|\\.)*)\]')
SHORTCUT_REFERENCE = re.compile(r'!\[((?:[^\]\\]|\\.)+)\](?![\[(])')
DEFINITION = re.compile(r'^ {0,3}\[((?:[^\]\\]|\\.)+)\]:[ \t]*' + DESTINATION, re.M)
HTML_IMAGE = re.compile(r'<img\b[^>]*>', re.I)
SOURCE = re.compile(r'<source\b[^>]*\bsrcset=["\']([^"\']+)["\']', re.I)
REMOTE = ('http://', 'https://', '//', 'data:', '#')


def load_upstream():
    # No bytecode cache: a __pycache__ beside the pinned files breaks their hash check.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('beautify_upstream_audit', UPSTREAM)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def without_fenced_code(text):
    kept, fence = [], None
    for line in text.splitlines():
        match = FENCE.match(line)
        if fence is None and match:
            fence = match.group(1)
        elif fence is not None and line.strip().startswith(fence[0] * len(fence)) and not line.strip().strip(fence[0]):
            fence = None
        elif fence is None:
            kept.append(line)
    return '\n'.join(kept)


def label_key(label):
    return ' '.join(label.split()).casefold()


def destination(raw):
    return raw[1:-1] if raw.startswith('<') and raw.endswith('>') else raw


def repository_root(readme):
    for folder in (readme.parent, *readme.parent.parents):
        if (folder / '.git').exists():
            return folder
    return readme.parent


def local_target(src, readme, root):
    if src.lower().startswith(REMOTE):
        return None
    clean = unquote(src.split('#', 1)[0].split('?', 1)[0])
    if not clean:
        return None
    return (root / clean.lstrip('/')).resolve() if clean.startswith('/') else (readme.parent / clean).resolve()


def without_inline_code(text):
    """Mask complete single-line image examples, not general Markdown code."""
    offset = until = protected = 0
    images = sorted(match.span() for pattern in (INLINE_IMAGE, HTML_IMAGE, SOURCE, DEFINITION)
                    for match in pattern.finditer(text))
    spans = []
    for line in text.splitlines(keepends=True):
        runs = list(re.finditer(r'`+', line))
        escaped = []
        for run in runs:
            cursor = run.start()
            while cursor > 0 and line[cursor - 1] == '\\':
                cursor -= 1
            escaped.append((run.start() - cursor) % 2)
        following, last = {}, {}
        # Index the next exact closing run once; unmatched openers never rescan
        # the rest of the line. Backslashes are literal inside a code span.
        for index in range(len(runs) - 1, -1, -1):
            run = runs[index]
            length = len(run.group())
            following[index] = last.get(length - escaped[index])
            last[length] = index
        for index, run in enumerate(runs):
            start = offset + run.start() + escaped[index]
            if start < until or start >= offset + run.end():
                continue
            closing = following[index]
            if closing is not None:
                until = offset + runs[closing].end()
                content = line[run.end():runs[closing].start()].strip()
                # Restrict this partial capability to a whole image example.
                # Mixed text and ambiguous markup retain the original audit;
                # a delimiter from a URL or HTML fragment must not hide images.
                while protected < len(images) and images[protected][1] <= start:
                    protected += 1
                if protected < len(images) and images[protected][0] < start < images[protected][1]:
                    continue  # literal backticks inside an existing image/path
                if (INLINE_IMAGE.fullmatch(content) or FULL_REFERENCE.fullmatch(content)
                        or SHORTCUT_REFERENCE.fullmatch(content) or HTML_IMAGE.fullmatch(content)
                        or re.fullmatch(r'<source\b[^>]*>', content, re.I)):
                    spans.append((start, until))
        offset += len(line)
    pieces, previous = [], 0
    for start, end in spans:
        pieces.extend((text[previous:start], ' ' * (end - start)))
        previous = end
    pieces.append(text[previous:])
    return ''.join(pieces)


def collect(text, upstream):
    """Image sources in document order, undefined reference labels and alt-text warnings."""
    text = without_inline_code(text)
    definitions = {}
    for label, raw in DEFINITION.findall(text):
        definitions.setdefault(label_key(label), destination(raw))
    sources, undefined, warnings = [], [], []
    sources += [destination(raw) for raw in INLINE_IMAGE.findall(text)]
    references = [label or alt for alt, label in FULL_REFERENCE.findall(text)]
    references += SHORTCUT_REFERENCE.findall(FULL_REFERENCE.sub('', INLINE_IMAGE.sub('', text)))
    for label in references:
        if label_key(label) in definitions:
            sources.append(definitions[label_key(label)])
        else:
            undefined.append(label)
    for tag in HTML_IMAGE.findall(text):
        src = upstream.HTML_IMAGE.search(tag)
        if src:
            sources.append(src.group(1))
        alt = upstream.HTML_ALT.search(tag)
        if not alt or not alt.group(1).strip():
            warnings.append(f'HTML image missing useful alt text: {tag[:100]}')
    for srcset in SOURCE.findall(text):
        sources += [candidate.split()[0] for candidate in srcset.split(',') if candidate.strip()]
    return sources, undefined, warnings


def main(argv):
    if len(argv) != 2:
        print('usage: audit_readme.py /path/to/README.md', file=sys.stderr)
        return 2
    readme = Path(argv[1]).expanduser().resolve()
    if not readme.is_file():
        print(f'ERROR: README not found: {readme}')
        return 2
    upstream = load_upstream()
    root = repository_root(readme)
    sources, undefined, warnings = collect(without_fenced_code(readme.read_text(encoding='utf-8')), upstream)
    warnings += [f'undefined image reference: [{label}]' for label in dict.fromkeys(undefined)]
    checked = {}
    for src in sources:
        target = local_target(src, readme, root)
        if target is not None:
            checked.setdefault(target, src)
    for target, src in checked.items():
        if not target.is_file():
            warnings.append(f'missing image: {src}')
        elif target.suffix.lower() == '.svg':
            warnings += [f'{src}: {issue}' for issue in upstream.audit_svg(target)]
    print(f'README: {readme}')
    print(f'Local images checked: {len(checked)}')
    if warnings:
        print('Issues:')
        for warning in warnings:
            print(f'- {warning}')
        return 1
    print('OK: image references and SVG basics passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
