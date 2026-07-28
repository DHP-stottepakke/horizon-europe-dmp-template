#!/usr/bin/env python3
"""Validate src/_sections.j2 against the Norwegian knowledge model.

Runs without a project export, so it is the cheap check to run after every edit of
the section skeleton. It reports:

  * anchors that do not exist as "<chapterKey>.<questionKey>" in the KM (typos, or
    keys that belong to a follow-up rather than a top-level question),
  * anchors listed more than once (only the first occurrence would ever render),
  * questions carrying the template's KM tag that no section picks up,
  * anchors that are used but do not carry that tag, so the deviation stays visible.

Usage:
    python tools/check_sections.py \
        --km ../KM-tooling/mapJsonKeysWF/results/research.data.no_norway-generic_1.2.1-squashed.km \
        --tag "Horizon Europe"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

KEY_RE = re.compile(r'"([A-Za-z][A-Za-z0-9_]*\.[A-Za-z][A-Za-z0-9_]*)"')

# Front-matter questions are rendered by contributors.html.j2 / projects.html.j2,
# so they are expected to be tagged but absent from the section skeleton.
FRONT_MATTER = {
    'administrativeInformation.contributors',
    'administrativeInformation.dmpTitle',
    'researchProjectChapter.name',
    'researchProjectChapter.abstract',
    'researchProjectChapter.startDate',
    'researchProjectChapter.endDate',
    'researchProjectChapter.didPlanApply',
}


def annotation(annotations, key: str) -> str | None:
    for item in annotations or []:
        if item.get('key') == key:
            value = item.get('value')
            if isinstance(value, list):
                value = value[0] if value else None
            if value:
                return value
    return None


def load_km(path: Path):
    """Return (anchors, tags) where anchors maps chapter-qualified key -> tag uuids."""
    events = json.loads(path.read_text())['packages'][0]['events']

    chapters: dict[str, str] = {}      # chapter uuid -> json.key
    questions: dict[str, dict] = {}    # question uuid -> {key, parent, tags, title}
    tag_names: dict[str, str] = {}     # tag uuid -> name

    for event in events:
        content = event.get('content', {})
        event_type = content.get('eventType')
        uuid = event['entityUuid']
        if event_type == 'AddChapterEvent':
            key = annotation(content.get('annotations'), 'json.key')
            if key:
                chapters[uuid] = key
        elif event_type == 'AddQuestionEvent':
            questions[uuid] = {
                'key': annotation(content.get('annotations'), 'json.key'),
                'parent': event.get('parentUuid'),
                'tags': set(content.get('tagUuids') or []),
                'title': content.get('title', ''),
            }
        elif event_type == 'AddTagEvent':
            tag_names[uuid] = content.get('name', '')

    anchors = {}
    for question in questions.values():
        chapter_key = chapters.get(question['parent'])
        if chapter_key and question['key']:
            anchors[f'{chapter_key}.{question["key"]}'] = question
    return anchors, tag_names


def load_section_keys(path: Path) -> list[str]:
    """Anchor keys in document order; the section file is data, so a regex suffices."""
    return KEY_RE.findall(path.read_text())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--sections', type=Path, default=Path('src/_sections.j2'))
    parser.add_argument('--km', required=True, type=Path)
    parser.add_argument('--tag', help='KM tag name expected to back the selection')
    args = parser.parse_args()

    anchors, tag_names = load_km(args.km)
    used = load_section_keys(args.sections)

    unknown = [key for key in used if key not in anchors]
    duplicates = sorted({key for key in used if used.count(key) > 1})

    print(f'{args.sections}: {len(used)} anchors, {len(set(used))} unique')
    for key in unknown:
        print(f'  UNKNOWN   {key}  (not a top-level keyed question of an annotated chapter)')
    for key in duplicates:
        print(f'  DUPLICATE {key}  (renders only at its first occurrence)')

    if args.tag:
        tag_uuid = next((u for u, name in tag_names.items() if name == args.tag), None)
        if tag_uuid is None:
            print(f'  ERROR     no tag named {args.tag!r} in the knowledge model')
            return 1
        tagged = {key for key, q in anchors.items() if tag_uuid in q['tags']}
        missing = sorted(tagged - set(used) - FRONT_MATTER)
        extra = sorted(key for key in set(used) if key in anchors and key not in tagged)
        print(f'  tag {args.tag!r}: {len(tagged)} tagged anchors, '
              f'{len(tagged & set(used))} used, {len(missing)} unused, {len(extra)} untagged in use')
        for key in missing:
            print(f'  UNUSED    {key}  ({anchors[key]["title"][:60]})')
        for key in extra:
            print(f'  UNTAGGED  {key}  ({anchors[key]["title"][:60]})')

    return 1 if unknown or duplicates else 0


if __name__ == '__main__':
    sys.exit(main())
