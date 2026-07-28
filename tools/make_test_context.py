#!/usr/bin/env python3
"""Build a document context from a squashed knowledge model, for offline rendering.

A real DSW project export is the better test input, but it needs a running instance
and a filled-in questionnaire. This replays the Add* events of a squashed KM into
the entity maps the document worker expects and attaches synthetic replies, so the
template can be rendered end to end before any export exists.

With --replies none every question renders its "not answered" placeholder; with
--replies all every question gets a plausible reply (first answer, one list item,
all choices), which exercises the option/list/multi-choice/table paths.

Usage:
    python tools/make_test_context.py \
        --km ../KM-tooling/mapJsonKeysWF/results/research.data.no_norway-generic_1.2.1-squashed.km \
        --replies all -o /tmp/ctx-full.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

METAMODEL_VERSION = '18'

ENTITY_EVENTS = {
    'AddChapterEvent': 'chapters',
    'AddQuestionEvent': 'questions',
    'AddAnswerEvent': 'answers',
    'AddChoiceEvent': 'choices',
    'AddExpertEvent': 'experts',
    'AddReferenceEvent': 'references',
    'AddTagEvent': 'tags',
    'AddMetricEvent': 'metrics',
    'AddPhaseEvent': 'phases',
    'AddIntegrationEvent': 'integrations',
    'AddResourceCollectionEvent': 'resourceCollections',
    'AddResourcePageEvent': 'resourcePages',
}

# Child lists the document worker reads, per parent entity kind.
CHILD_FIELDS = {
    'chapters': 'questionUuids',
    'answers': 'followUpUuids',
}


def build_entities(events: list[dict]) -> tuple[dict, dict, dict]:
    """Return (entities, parent_of, order) from a squashed event stream."""
    entities: dict[str, dict] = {name: {} for name in ENTITY_EVENTS.values()}
    parent_of: dict[str, str] = {}
    order: list[tuple[str, str]] = []

    for event in events:
        content = event.get('content', {})
        collection = ENTITY_EVENTS.get(content.get('eventType', ''))
        if collection is None:
            continue
        uuid = event['entityUuid']
        entity = {k: v for k, v in content.items() if k != 'eventType'}
        entity['uuid'] = uuid
        entity.setdefault('annotations', [])
        entities[collection][uuid] = entity
        parent_of[uuid] = event.get('parentUuid')
        order.append((collection, uuid))

    _attach_children(entities, parent_of, order)
    return entities, parent_of, order


def _attach_children(entities: dict, parent_of: dict, order: list) -> None:
    """Rebuild the *Uuids link lists that squashed events express through parentUuid."""
    for collection, uuid in order:
        entity = entities[collection][uuid]
        if collection == 'chapters':
            entity['questionUuids'] = []
        elif collection == 'questions':
            entity.setdefault('tagUuids', [])
            entity.setdefault('referenceUuids', [])
            entity.setdefault('expertUuids', [])
            entity.setdefault('requiredPhaseUuid', None)
            entity.setdefault('text', None)
            qtype = entity.get('questionType')
            if qtype == 'OptionsQuestion':
                entity['answerUuids'] = []
            elif qtype == 'ListQuestion':
                entity['itemTemplateQuestionUuids'] = []
            elif qtype == 'MultiChoiceQuestion':
                entity['choiceUuids'] = []
        elif collection == 'answers':
            entity['followUpUuids'] = []
            entity.setdefault('advice', None)
            entity.setdefault('metricMeasures', [])
        elif collection == 'resourceCollections':
            entity['resourcePageUuids'] = []

    for collection, uuid in order:
        parent = parent_of.get(uuid)
        if parent is None:
            continue
        if collection == 'questions':
            if parent in entities['chapters']:
                entities['chapters'][parent]['questionUuids'].append(uuid)
            elif parent in entities['answers']:
                entities['answers'][parent]['followUpUuids'].append(uuid)
            elif parent in entities['questions']:
                entities['questions'][parent].setdefault(
                    'itemTemplateQuestionUuids', []).append(uuid)
        elif collection == 'answers' and parent in entities['questions']:
            entities['questions'][parent].setdefault('answerUuids', []).append(uuid)
        elif collection == 'choices' and parent in entities['questions']:
            entities['questions'][parent].setdefault('choiceUuids', []).append(uuid)
        elif collection == 'references' and parent in entities['questions']:
            entities['questions'][parent].setdefault('referenceUuids', []).append(uuid)
        elif collection == 'experts' and parent in entities['questions']:
            entities['questions'][parent].setdefault('expertUuids', []).append(uuid)
        elif collection == 'resourcePages' and parent in entities['resourceCollections']:
            entities['resourceCollections'][parent]['resourcePageUuids'].append(uuid)


def make_replies(entities: dict) -> dict:
    """One plausible reply per question, walking the tree the way a user would."""
    replies: dict[str, dict] = {}
    questions = entities['questions']
    meta = {'createdAt': '2026-01-01T00:00:00Z', 'createdBy': None}

    def visit(question_uuid: str, path: str) -> None:
        question = questions.get(question_uuid)
        if question is None:
            return
        path = f'{path}.{question_uuid}'
        qtype = question.get('questionType')

        if qtype == 'ValueQuestion':
            replies[path] = {'value': {'type': 'StringReply', 'value': 'Test value'}, **meta}
        elif qtype == 'IntegrationQuestion':
            replies[path] = {'value': {'type': 'IntegrationReply',
                                       'value': {'type': 'PlainType', 'value': 'Test entry'}},
                             **meta}
        elif qtype == 'OptionsQuestion':
            answers = question.get('answerUuids') or []
            if answers:
                answer_uuid = answers[0]
                replies[path] = {'value': {'type': 'AnswerReply', 'value': answer_uuid}, **meta}
                for followup in entities['answers'][answer_uuid].get('followUpUuids', []):
                    visit(followup, f'{path}.{answer_uuid}')
        elif qtype == 'MultiChoiceQuestion':
            choices = question.get('choiceUuids') or []
            if choices:
                replies[path] = {'value': {'type': 'MultiChoiceReply', 'value': choices}, **meta}
        elif qtype == 'ListQuestion':
            item_uuid = '00000000-0000-0000-0000-000000000001'
            replies[path] = {'value': {'type': 'ItemListReply', 'value': [item_uuid]}, **meta}
            for followup in question.get('itemTemplateQuestionUuids', []):
                visit(followup, f'{path}.{item_uuid}')

    for chapter in entities['chapters'].values():
        for question_uuid in chapter['questionUuids']:
            visit(question_uuid, chapter['uuid'])

    return replies


def build_context(km_path: Path, with_replies: bool) -> dict:
    km = json.loads(km_path.read_text())
    package = km['packages'][0]
    entities, _, _ = build_entities(package['events'])
    replies = make_replies(entities) if with_replies else {}

    return {
        'metamodelVersion': METAMODEL_VERSION,
        'uuid': '00000000-0000-0000-0000-0000000000ff',
        'config': {
            'clientUrl': 'https://example.test',
        },
        'knowledgeModel': {
            'uuid': '00000000-0000-0000-0000-0000000000aa',
            'chapterUuids': list(entities['chapters'].keys()),
            'tagUuids': list(entities['tags'].keys()),
            'metricUuids': list(entities['metrics'].keys()),
            'phaseUuids': list(entities['phases'].keys()),
            'integrationUuids': list(entities['integrations'].keys()),
            'resourceCollectionUuids': list(entities['resourceCollections'].keys()),
            'annotations': [],
            'entities': entities,
        },
        'knowledgeModelPackage': {
            'id': km['id'],
            'organizationId': km['organizationId'],
            'kmId': km['kmId'],
            'version': km['version'],
            'name': km['name'],
            'description': '',
            'createdAt': '2026-01-01T00:00:00Z',
            'organization': None,
            'versions': [km['version']],
        },
        'organization': {
            'organizationId': 'test',
            'name': 'Test Organization',
            'description': '',
            'affiliations': [],
        },
        'project': {
            'uuid': '00000000-0000-0000-0000-0000000000bb',
            'name': 'Test project',
            'description': '',
            'eventUuid': '00000000-0000-0000-0000-0000000000f1',
            'createdAt': '2026-01-01T00:00:00Z',
            'updatedAt': '2026-01-01T00:00:00Z',
            'createdBy': None,
            'phaseUuid': None,
            'replies': replies,
            'versions': [],
            'files': [],
            'users': [],
            'userGroups': [],
            'tags': [],
        },
        'report': {
            'uuid': '00000000-0000-0000-0000-0000000000dd',
            'createdAt': '2026-01-01T00:00:00Z',
            'updatedAt': '2026-01-01T00:00:00Z',
            'totalReport': {'chapterUuid': None, 'indications': [], 'metrics': []},
            'chapterReports': [],
        },
        'users': [],
        'groups': [],
        'document': {
            'uuid': '00000000-0000-0000-0000-0000000000cc',
            'name': 'Test document',
            'documentTemplateUuid': '00000000-0000-0000-0000-0000000000ee',
            'formatUuid': '00000000-0000-0000-0000-0000000000ef',
            'createdAt': '2026-01-01T00:00:00Z',
            'createdBy': None,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--km', required=True, type=Path)
    parser.add_argument('--replies', choices=['none', 'all'], default='all')
    parser.add_argument('-o', '--output', required=True, type=Path)
    args = parser.parse_args()

    context = build_context(args.km, args.replies == 'all')
    args.output.write_text(json.dumps(context, indent=1))
    print(f'wrote {args.output} '
          f'({len(context["knowledgeModel"]["entities"]["questions"])} questions, '
          f'{len(context["project"]["replies"])} replies)')


if __name__ == '__main__':
    main()
