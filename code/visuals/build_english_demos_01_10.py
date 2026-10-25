"""Build English versions of the five interactive pages in Lessons 01–10.

Translate only explicit UI strings. Step demos embed the English SVGs produced
by the figure build, while preserving the original frame sequence and phases.
Run the English figure build first, then this script. --check checks freshness.
"""
from __future__ import annotations

import argparse
import ast
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re

CODE = Path(__file__).resolve().parents[1]
COLUMN = CODE.parent
TRANSLATIONS = CODE / 'visuals/reading_site/demo_translations_01_10.json'
PAGES = (
    '01-neuron/walkthrough.html',
    '04-gradients/walkthrough.html',
    '05-backpropagation/walkthrough.html',
    '10-attention/walkthrough.html',
)
SCRIPT = re.compile(r'(<script\b[^>]*>)(.*?)(</script>)', re.S | re.I)
STRING = re.compile(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"")
CJK = re.compile(r'[\u3400-\u9fff]')


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style'}:
            self.hidden += 1
        self.text.extend(value for key, value in attrs
                         if key in {'aria-label', 'alt', 'title'} and value)

    def handle_endtag(self, tag):
        if tag in {'script', 'style'}:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.text.append(data.strip())


def translated_markup(markup, mapping):
    def text_node(match):
        value = match[0]
        stripped = html.unescape(value.strip())
        if stripped not in mapping:
            return value
        leading = value[:len(value) - len(value.lstrip())]
        trailing = value[len(value.rstrip()):]
        return leading + html.escape(mapping[stripped], quote=False) + trailing

    markup = re.sub(r'(?<=>)[^<>]+(?=<)', text_node, markup)

    def attribute(match):
        name, quote, raw = match.groups()
        value = html.unescape(raw)
        if name in {'aria-label', 'alt', 'title'}:
            value = mapping.get(value, value)
        elif name == 'lang' and value == 'zh-CN':
            value = 'en'
        elif name in {'href', 'src'}:
            if value in {'README.md', 'index.html'}:
                value = 'index.en.html'
            elif value in {'walkthrough.html', 'lab3d.html'}:
                value = value.removesuffix('.html') + '.en.html'
            elif value.startswith('images/') and not value.startswith('images/en/'):
                value = value.replace('images/', 'images/en/', 1)
        return f'{name}={quote}{html.escape(value, quote=True)}{quote}'

    return re.sub(r'\b(aria-label|alt|title|lang|href|src)=([\"\'])(.*?)\2',
                  attribute, markup)


def translated_script(script, translations):
    # Templates are exact, reviewed literals: their interpolation expressions
    # stay in place. Ordinary replacements apply only to allowlisted strings.
    for old, new in translations['js_templates'].items():
        script = script.replace(old, new)

    def literal(match):
        value = ast.literal_eval(match[0])
        before = script[:match.start()].rstrip()
        after = script[match.end():].lstrip()
        # Never translate an object property name, even if added to the map.
        if after.startswith(':') and before.endswith(('{', ',')):
            return match[0]
        translated = translations['js_literals'].get(value)
        return json.dumps(translated, ensure_ascii=False) if translated is not None else match[0]

    return STRING.sub(literal, script)


def translated_frames(raw, translations):
    data = json.loads(raw)
    labels = translations['frame_labels']
    data['labels'] = [labels[label] for label in data['labels']]
    for frame in data['frames']:
        relative = Path(frame['figure'])
        english_relative = relative.parent / 'en' / relative.name
        english_svg = (COLUMN / english_relative).read_text(encoding='utf-8')
        original_phases = re.findall(r'data-phase="(\d+)"', frame['markup'])
        english_phases = re.findall(r'data-phase="(\d+)"', english_svg)
        if original_phases != english_phases:
            raise AssertionError(f'English SVG changed animation phases: {english_relative}')
        frame['caption'] = labels[frame['caption']]
        frame['figure'] = english_relative.as_posix()
        frame['markup'] = english_svg
    return json.dumps(data, ensure_ascii=False).replace('</', '<\\/')


def render(source, translations):
    original = source.read_text(encoding='utf-8')
    mapping = dict(translations['html'])
    chinese_title = (source.parent / 'README.md').read_text(encoding='utf-8').splitlines()[0][2:]
    english_title = (source.parent / 'README.en.md').read_text(encoding='utf-8').splitlines()[0][2:]
    mapping[chinese_title] = english_title
    mapping[chinese_title + ' · 逐步演示'] = english_title + ' · Step-by-step demo'
    parts = []
    cursor = 0
    for match in SCRIPT.finditer(original):
        parts.append(translated_markup(original[cursor:match.start()], mapping))
        opening, body, closing = match.groups()
        if re.search(r'\bid=[\"\']data[\"\']', opening):
            body = translated_frames(body, translations)
        else:
            body = translated_script(body, translations)
        parts.append(opening + body + closing)
        cursor = match.end()
    parts.append(translated_markup(original[cursor:], mapping))
    result = ''.join(parts)
    visible = VisibleText()
    visible.feed(result)
    leftovers = [text for text in visible.text if CJK.search(text.replace('好好用 AI', ''))]
    if leftovers:
        raise AssertionError(f'Untranslated visible text in {source.name}: {leftovers}')
    return result


def build(check=False):
    translations = json.loads(TRANSLATIONS.read_text(encoding='utf-8'))
    stale = []
    for relative in PAGES:
        source = COLUMN / 'chapters' / relative
        target = source.with_name(source.stem + '.en.html')
        result = render(source, translations)
        if check:
            if not target.exists() or target.read_text(encoding='utf-8') != result:
                stale.append(str(target.relative_to(COLUMN)))
        else:
            target.write_text(result, encoding='utf-8')
    if stale:
        raise AssertionError('Stale English demos: ' + ', '.join(stale))
    print(f'{"Checked" if check else "Built"} {len(PAGES)} English interactive pages.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
