"""核对网页训练的数据、默认配方、初值与实际 PyTorch 更新规则。"""
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import unittest

import numpy as np
import torch

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE))
from tiny_lm import train
from tiny_lm.checkpoint import load_checkpoint
from tiny_lm.data import build_records, make_pretrain_batch, make_sft_batch
from tiny_lm.model import ModelConfig
from tiny_lm.tokenizer import CharTokenizer
from visuals.export_browser_training import DESTINATION, check_assets, training_recipe
from visuals.training_lab import render_training_lab


class BrowserTrainingChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = check_assets()
        cls.data = json.loads((DESTINATION / 'data.json').read_text(encoding='utf-8'))
        cls.groups = build_records()
        cls.tokenizer = CharTokenizer.for_course()

    def test_all_samples_and_masks_match_course_builders(self):
        self.assertEqual(self.data['tokens'], self.tokenizer.itos)
        for key, records in self.groups.items():
            builder = make_sft_batch if key.startswith('sft') else make_pretrain_batch
            ids, targets = builder(records, self.tokenizer, self.manifest['sequence_length'])
            encoded = self.data['groups'][key]
            self.assertEqual([r['record_id'] for r in encoded], [r['record_id'] for r in records])
            np.testing.assert_array_equal([r['ids'] for r in encoded], ids.numpy())
            np.testing.assert_array_equal([r['targets'] for r in encoded], targets.numpy())
            if key.startswith('sft'):
                self.assertEqual([(r['prompt'], r['answer']) for r in encoded],
                                 [(r['prompt'], r['answer']) for r in records])

    def test_every_batch_uses_the_original_random_sampler(self):
        for stage in ('pretrain', 'sft'):
            preset = self.manifest['presets'][stage]
            sampler = random.Random(preset['seed'])
            ids = [r['record_id'] for r in self.groups[stage + '_train']]
            self.assertEqual(len(self.data['schedules'][stage]), self.manifest['max_steps'])
            for indices in self.data['schedules'][stage]:
                self.assertEqual([ids[i] for i in indices], sampler.sample(ids, preset['batch_size']))

    @unittest.skipUnless(shutil.which('node'), '样本编辑检查需要 Node.js')
    def test_edited_browser_samples_use_the_course_tokenization_and_loss_masks(self):
        script = '''
import {readableSamples, applySampleEdits} from %s;
let input='';for await(const chunk of process.stdin)input+=chunk;
const data=JSON.parse(input), before=JSON.stringify(data), raw=readableSamples(data);
const edits=[{group:'pretrain_train',record_id:raw.pretrain_train[0].record_id,text:'早上，小丁喜欢黄色的香蕉。'},
{group:'sft_train',record_id:raw.sft_train[0].record_id,prompt:raw.sft_train[0].prompt,answer:'黄色的香蕉。'}];
const changed=applySampleEdits(data,edits,32);
process.stdout.write(JSON.stringify({raw,edited:[changed.pretrain_train[0],changed.sft_train[0]],
untouched:before===JSON.stringify(data),validationUnchanged:JSON.stringify(changed.sft_val)===JSON.stringify(data.groups.sft_val)}));
''' % json.dumps((CODE / 'visuals/reading_site/training-engine.mjs').as_uri())
        result = subprocess.run([shutil.which('node'), '--input-type=module', '-e', script],
                                input=json.dumps(self.data), text=True, capture_output=True, check=True)
        actual = json.loads(result.stdout)
        self.assertTrue(actual['untouched'])
        self.assertTrue(actual['validationUnchanged'])
        self.assertEqual([r['text'] for r in actual['raw']['pretrain_train']],
                         [r['text'] for r in self.groups['pretrain_train']])
        records = [{**self.groups['pretrain_train'][0], 'text': '早上，小丁喜欢黄色的香蕉。'},
                   {**self.groups['sft_train'][0], 'answer': '黄色的香蕉。'}]
        for index, builder in enumerate((make_pretrain_batch, make_sft_batch)):
            ids, targets = builder([records[index]], self.tokenizer, 32)
            self.assertEqual(actual['edited'][index]['ids'], ids[0].tolist())
            self.assertEqual(actual['edited'][index]['targets'], targets[0].tolist())

    @unittest.skipUnless(shutil.which('node'), '样本边界检查需要 Node.js')
    def test_browser_sample_edits_reject_unknown_chars_truncation_and_validation_leaks(self):
        script = '''
import {readableSamples, applySampleEdits} from %s;
let input='';for await(const chunk of process.stdin)input+=chunk;
const data=JSON.parse(input), raw=readableSamples(data), base={group:'pretrain_train',record_id:raw.pretrain_train[0].record_id};
const cases=[{...base,text:'唐'},{...base,text:'早'.repeat(32)},{...base,text:''},
{...base,text:raw.pretrain_val[0].text},{...base,group:'pretrain_val',record_id:raw.pretrain_val[0].record_id,text:'早'},
{group:'sft_train',record_id:raw.sft_train[0].record_id,prompt:raw.sft_val[0].prompt,answer:'红色的苹果。'},
{...base,text:raw.sft_val[0].prompt+raw.sft_val[0].answer},
{group:'sft_train',record_id:raw.sft_train[0].record_id,prompt:'问：',answer:raw.pretrain_val[0].text}];
process.stdout.write(JSON.stringify(cases.map(edit=>{try{applySampleEdits(data,[edit],32);return 'accepted'}catch(e){return e.sampleError?.code}})));
''' % json.dumps((CODE / 'visuals/reading_site/training-engine.mjs').as_uri())
        result = subprocess.run([shutil.which('node'), '--input-type=module', '-e', script],
                                input=json.dumps(self.data), text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout), ['UNKNOWN_CHARACTER', 'TOO_LONG', 'EMPTY_SAMPLE',
                                                     'VALIDATION_OVERLAP', 'READ_ONLY_GROUP', 'VALIDATION_OVERLAP',
                                                     'VALIDATION_OVERLAP', 'VALIDATION_OVERLAP'])

    @unittest.skipUnless(shutil.which('node'), '生成边界检查需要 Node.js')
    def test_browser_generation_can_finish_long_answers_and_score_eos_at_context_limit(self):
        script = '''
import {TrainingEngine} from %s;
let input='';for await(const chunk of process.stdin)input+=chunk;
const {data,manifest}=JSON.parse(input);
async function generate(prompt,answer){
 const engine=new TrainingEngine(null,manifest,data,null,null,null,null), expected=Array.from(answer);
 let calls=0;
 engine.calculate=async(_session,batch)=>{
  const row=Array.from(batch.ids.slice(0,manifest.sequence_length));
  const padding=row.indexOf(0n),length=padding<0?row.length:padding;
  const logits=new Float32Array(manifest.batch_size*manifest.sequence_length*data.tokens.length).fill(-10);
  const next=calls<expected.length?data.tokens.indexOf(expected[calls]):2;
  logits[(length-1)*data.tokens.length+next]=10;calls++;
  return {logits:{data:logits,dispose(){}},loss:{data:[0],dispose(){}}};
 };
 return {...await engine.generate(prompt,expected.length+1),calls};
}
const raw=data.groups.sft_train[0];
process.stdout.write(JSON.stringify(await Promise.all([generate(raw.prompt,'香蕉，它是黄色的。'),generate('早'.repeat(30),'上')])));
''' % json.dumps((CODE / 'visuals/reading_site/training-engine.mjs').as_uri())
        result = subprocess.run([shutil.which('node'), '--input-type=module', '-e', script],
                                input=json.dumps({'data': self.data, 'manifest': self.manifest}),
                                text=True, capture_output=True, check=True)
        outputs = json.loads(result.stdout)
        self.assertEqual([(row['text'], row['stop'], row['calls']) for row in outputs],
                         [('香蕉，它是黄色的。', 'eos', 10), ('上', 'eos', 2)])

    def test_course_defaults_and_all_initial_parameters_match(self):
        optimizer, presets = training_recipe(train)
        self.assertEqual(json.loads(json.dumps(optimizer)), self.manifest['optimizer'])
        self.assertEqual(presets, self.manifest['presets'])
        # 精确核对保存的课程权重；相同种子在不同平台上不保证逐位一致。
        initial, saved_tokenizer, metadata = load_checkpoint(CODE / 'artifacts/first_run/initial.pt')
        self.assertEqual(initial.config, ModelConfig(vocab_size=self.tokenizer.vocab_size))
        self.assertEqual(saved_tokenizer.itos, self.tokenizer.itos)
        self.assertEqual(metadata['stage'], 'initial')
        self.assertEqual(metadata['seed'], presets['pretrain']['seed'])
        pretrained, _, _ = load_checkpoint(CODE / 'artifacts/first_run/pretrain.pt')
        for name, model in [('initial', initial), ('pretrained', pretrained)]:
            expected = np.concatenate([p.detach().numpy().ravel() for p in model.parameters()])
            np.testing.assert_array_equal(np.fromfile(DESTINATION / (name + '.f32'), dtype='<f4'), expected)
            self.assertEqual(expected.size, self.manifest['parameter_count'])
            self.assertEqual([p['name'] for p in self.manifest['parameters']], [n for n, _ in model.named_parameters()])

    def test_exported_graphs_have_no_machine_paths(self):
        for name in ('train-step.onnx', 'evaluate.onnx'):
            content = (DESTINATION / name).read_bytes()
            markers = [b'/' + root + b'/' for root in (b'Users', b'home', b'private')]
            markers.append(b'\\' + b'Users' + b'\\')
            for marker in markers:
                self.assertNotIn(marker, content)

    def test_three_lessons_have_distinct_questions_and_current_presets(self):
        for number, mode in [('17', 'pretrain'), ('19', 'sft'), ('20', 'pipeline')]:
            for english in (False, True):
                rendered = render_training_lab(number, english)
                self.assertIn('data-default-mode="' + mode + '"', rendered)
                presets = json.loads(html.unescape(re.search(r'data-presets="([^"]+)"', rendered)[1]))
                self.assertEqual(presets, self.manifest['presets'])
                self.assertIn('training-extra-generations', rendered)
                self.assertIn('training-comparison', rendered)
                self.assertNotIn('onnxruntime', rendered)
        self.assertEqual(render_training_lab('16'), '')

    def test_training_fields_reject_missing_values_before_loading(self):
        class Inputs(HTMLParser):
            def __init__(self):
                super().__init__()
                self.fields = []

            def handle_starttag(self, tag, attrs):
                if tag == 'input':
                    self.fields.append(dict(attrs))

        for number in ('17', '19', '20'):
            for english in (False, True):
                parser = Inputs()
                parser.feed(render_training_lab(number, english))
                self.assertEqual(len(parser.fields), 4)
                for field in parser.fields:
                    self.assertIn('required', field, (number, english, field['id']))

    @unittest.skipUnless(shutil.which('node'), '更新器的交叉验证需要 Node.js')
    def test_javascript_optimizer_matches_pytorch_with_the_same_gradients(self):
        # 包括触发裁剪的梯度、零梯度，以及与 eps 同量级的梯度。
        rng = np.random.default_rng(42)
        values = [rng.normal(size=n).astype('float32') for n in (11, 7, 3)]
        gradients = [[(rng.normal(size=len(v)) * scale).astype('float32') for v in values]
                     for scale in (10, 0.1, 1e-9, 0, 3, 0.01, 1)]
        parameters = [torch.nn.Parameter(torch.from_numpy(v.copy())) for v in values]
        optimizer = torch.optim.AdamW(parameters, lr=.003, betas=(.9, .99), eps=1e-8, weight_decay=.01)
        expected = []
        for group in gradients:
            for p, g in zip(parameters, group):
                p.grad = torch.from_numpy(g.copy())
            torch.nn.utils.clip_grad_norm_(parameters, 1.)
            optimizer.step()
            expected.append([p.detach().numpy().tolist() for p in parameters])
        script = '''
import {adamStep} from %s;
let input='';for await(const chunk of process.stdin)input+=chunk;
const data=JSON.parse(input), parameters=data.values.map(values=>({values:new Float32Array(values),moment:new Float32Array(values.length),variance:new Float32Array(values.length)}));
const actual=[];data.gradients.forEach((gradients,i)=>{adamStep(parameters,gradients,i+1,.003,data.settings);actual.push(parameters.map(p=>Array.from(p.values)));});
process.stdout.write(JSON.stringify(actual));
''' % json.dumps((CODE / 'visuals/reading_site/training-engine.mjs').as_uri())
        payload = {'values': [v.tolist() for v in values],
                   'gradients': [[g.tolist() for g in group] for group in gradients],
                   'settings': self.manifest['optimizer']}
        result = subprocess.run([shutil.which('node'), '--input-type=module', '-e', script],
                                input=json.dumps(payload), text=True, capture_output=True, check=True)
        for actual, reference in zip(json.loads(result.stdout), expected):
            for a, b in zip(actual, reference):
                np.testing.assert_allclose(a, b, atol=3e-7, rtol=1e-6)


if __name__ == '__main__':
    unittest.main()
