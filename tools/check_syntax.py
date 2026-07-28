#!/usr/bin/env python3
"""Parse every Jinja template in src/ so syntax errors surface without an export.

Uses the same environment as tools/render.py (DSW filters and tests registered), so
unknown filters are the only thing this cannot catch.

Usage:
    python tools/check_syntax.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'dsw_local'))

import jinja2  # noqa: E402

from dsw.document_worker.templates import filters, tests  # noqa: E402


def main() -> int:
    root = Path(__file__).parent.parent
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath=root),
        extensions=['jinja2.ext.do', 'jinja2.ext.loopcontrols'],
    )
    env.filters.update(filters.filters)
    env.tests.update(tests.tests)

    failures = 0
    templates = sorted(root.glob('src/**/*.j2'))
    for template in templates:
        rel = template.relative_to(root)
        try:
            env.parse(template.read_text(), name=str(rel), filename=str(template))
        except jinja2.TemplateSyntaxError as error:
            failures += 1
            print(f'FAIL {rel}:{error.lineno}: {error.message}')

    print(f'{len(templates)} templates parsed, {failures} failed')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
