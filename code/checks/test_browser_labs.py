"""可编辑练习与正文数值一致；示例复用实际课程模块。"""
import contextlib
import io
import json
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE))
from visuals.browser_labs import LABS, module_bundle, render_lab


def execute(number, **changes):
    source = LABS[number]['code']
    for name, value in changes.items():
        import re
        source = re.sub(r'^' + name + r' = .*$', name + ' = ' + repr(value), source, flags=re.M)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exec(compile(source, 'reader-experiment.py', 'exec'), {'__name__': '__main__'})
    return output.getvalue()


class BrowserLabChecks(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), '代码编辑器的文本检查需要 Node.js')
    def test_editor_keeps_source_exact_and_indents_selected_lines(self):
        module = (CODE / 'visuals/reading_site/code-editor.mjs').as_uri()
        script = r'''
import assert from 'node:assert/strict';
const {tokenizePython, indentSelection, newlineEdit} = await import(process.argv[1]);
const source = '# 中文注释\nfrom tiny_lm.scalar import forward\nx2 = 1.25e-3\nprint("<img src=x onerror=alert(1)>")\ntext = """first\nsecond"""\n';
const tokens = tokenizePython(source);
assert.equal(tokens.map(token => token.text).join(''), source);
for (const type of ['comment','keyword','number','builtin','string']) assert(tokens.some(token => token.type === type));
assert.equal(tokens.find(token => token.text.startsWith('"""')).type, 'string');
const apply = (text, edit) => text.slice(0, edit.start) + edit.text + text.slice(edit.end);
assert.equal(apply('x = 1', indentSelection('x = 1',0,0)), '    x = 1');
assert.equal(apply('\nx', indentSelection('\nx',0,0)), '    \nx');
const original = 'first\nsecond\nthird';
let edit = indentSelection(original,0,13);
let changed = apply(original,edit);
assert.equal(changed,'    first\n    second\nthird');
assert.equal(apply(changed,indentSelection(changed,edit.selectionStart,edit.selectionEnd,true)),original);
assert.equal(apply('    x = 1',indentSelection('    x = 1',2,2,true)),'x = 1');
assert.equal(newlineEdit('if True: # explain',18,18).text,'\n    ');
assert.equal(newlineEdit('    print(1)',12,12).text,'\n    ');
assert.equal(newlineEdit('print(":")',10,10).text,'\n');
assert.equal(newlineEdit('\nx',0,0).text,'\n');
'''
        subprocess.run([shutil.which('node'), '--input-type=module', '-e', script, module],
                       check=True, capture_output=True, text=True)

    def test_parameter_fields_reject_missing_values(self):
        class Inputs(HTMLParser):
            def __init__(self):
                super().__init__()
                self.fields = []

            def handle_starttag(self, tag, attrs):
                if tag == 'input':
                    self.fields.append(dict(attrs))

        for number in LABS:
            for english in (False, True):
                parser = Inputs()
                parser.feed(render_lab(number, english))
                for field in parser.fields:
                    self.assertIn('required', field, (number, english, field['id']))

    def test_neuron_and_linear_layer_match_hand_calculations(self):
        self.assertIn('output = 4.0', execute('01'))
        self.assertIn('output = 7.0', execute('01', x2=2))
        self.assertIn('outputs = [5.0, 9.0]', execute('02'))

    def test_removing_nonlinearity_changes_xor_behavior(self):
        self.assertEqual(execute('03').splitlines(), ['[0, 0] -> 0.0', '[0, 1] -> 1.0', '[1, 0] -> 1.0', '[1, 1] -> 0.0'])
        self.assertTrue(all(line.endswith('0.0') for line in execute('03', use_relu=False).splitlines()))

    def test_learning_rate_can_reduce_or_increase_error(self):
        self.assertIn('weight=2.6000, loss=0.6400', execute('04'))
        self.assertIn('weight=5.8000, loss=31.3600', execute('04', learning_rate=0.3))

    def test_manual_backprop_repeats_from_the_same_initial_parameters(self):
        first = execute('05')
        self.assertIn('prediction=-0.2896, loss=1.6631', first)
        self.assertEqual(first, execute('05'))
        self.assertIn('step 10:', execute('05', steps=10))

    def test_browser_modules_are_current_course_sources(self):
        bundle = json.loads(module_bundle())
        for name, code in bundle.items():
            self.assertEqual(code, (CODE / 'tiny_lm' / name).read_text(encoding='utf-8'))
        self.assertNotIn('import torch', '\n'.join(bundle.values()))


if __name__ == '__main__':
    unittest.main()
