"""将课程 PyTorch 的前向、反向和数据导出到浏览器；--check 只核对源与产物。"""
import argparse
import ast
import hashlib
import inspect
import json
from pathlib import Path
import random
import shutil
import sys
import tempfile

CODE = Path(__file__).resolve().parents[1]
COLUMN = CODE.parent
DESTINATION = Path(__file__).with_name('reading_site') / 'training'
SOURCE_FILES = [*(CODE/'tiny_lm'/name for name in ('model.py','layers.py','attention.py','rope.py',
    'train.py','data.py','tokenizer.py','losses.py','generate.py','checkpoint.py')),
    CODE/'artifacts/first_run/pretrain.pt', CODE/'requirements.txt',
    CODE/'requirements-browser-training.txt', Path(__file__)]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    return {p.relative_to(COLUMN).as_posix(): digest(p) for p in SOURCE_FILES}


def check_assets(folder=DESTINATION):
    manifest = json.loads((folder/'model.json').read_text(encoding='utf-8'))
    if manifest['sources'] != source_hashes():
        raise ValueError('网页训练资源与课程源码不同步，请运行 export_browser_training.py')
    for name, record in manifest['files'].items():
        path = folder/name
        if not path.is_file() or digest(path) != record['sha256']:
            raise ValueError('网页训练资源缺失或已改变：'+name)
    return manifest


def training_recipe(train_module):
    """读取课程函数的默认参数和优化器字面量，避免维护另一套训练配置。"""
    tree = ast.parse(inspect.getsource(train_module))
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    optimizer = next(n for n in ast.walk(functions['_fit']) if isinstance(n, ast.Call)
                     and isinstance(n.func, ast.Attribute) and n.func.attr == 'AdamW')
    settings = {k.arg: ast.literal_eval(k.value) for k in optimizer.keywords if k.arg != 'lr'}
    settings['clip_norm'] = inspect.signature(train_module.train_step).parameters['clip_norm'].default
    presets = {}
    for key, name in [('pretrain', 'run_pretrain'), ('sft', 'run_sft')]:
        function = getattr(train_module, name)
        fit = next(n for n in ast.walk(functions[name]) if isinstance(n, ast.Call)
                   and isinstance(n.func, ast.Name) and n.func.id == '_fit')
        keywords = {k.arg: k.value for k in fit.keywords}
        defaults = inspect.signature(function).parameters
        presets[key] = {n: defaults[n].default for n in ('steps', 'seed', 'batch_size')}
        presets[key]['learning_rate'] = ast.literal_eval(keywords['learning_rate'])
    presets['quick'] = {**presets['pretrain'], 'steps': 100, 'batch_size': 4}
    return settings, presets


def build():
    sys.path.insert(0, str(CODE))
    import numpy as np
    import onnx
    import onnxruntime as ort
    import torch
    from torch._decomp import get_decompositions
    from torch._functorch.aot_autograd import aot_export_module
    from tiny_lm import train
    from tiny_lm.checkpoint import load_checkpoint
    from tiny_lm.data import build_records, make_pretrain_batch, make_sft_batch
    from tiny_lm.losses import token_loss
    from tiny_lm.model import ModelConfig, TinyLM
    from tiny_lm.tokenizer import CharTokenizer

    torch.set_num_threads(1)
    optimizer, presets = training_recipe(train)
    torch.manual_seed(presets['pretrain']['seed'])
    groups, tokenizer = build_records(), CharTokenizer.for_course()
    config = ModelConfig(vocab_size=tokenizer.vocab_size)
    model = TinyLM(config)
    batch_size, positions = presets['pretrain']['batch_size'], config.max_seq_len
    if batch_size != presets['sft']['batch_size']:
        raise ValueError('预训练与微调批量变化后需重新定义浏览器图输入')
    x, y = make_pretrain_batch(groups['pretrain_train'][:batch_size], tokenizer, positions)

    class TrainingGraph(torch.nn.Module):
        def __init__(self, model):
            super().__init__()
            self.model = model

        def forward(self, ids, targets):
            logits = self.model(ids)
            # 与 token_loss 相同的公式；批次合法性在进入图之前校验。
            loss = torch.nn.functional.cross_entropy(logits.reshape(-1, logits.shape[-1]),
                                                     targets.reshape(-1), ignore_index=-100)
            return loss, logits.detach()

    wrapper = TrainingGraph(model)
    params = list(wrapper.parameters())
    input_names = [f'param_{i}' for i in range(len(params))] + ['ids','targets']
    output_names = ['loss','logits'] + [f'grad_{i}' for i in range(len(params))]
    arguments = tuple(params) + (x,y)
    # 将有效标签数保留在图内；NLL 的第二输出供平均损失的反向缩放使用。
    decompositions = get_decompositions([torch.ops.aten.nll_loss_forward.default])
    graphs = {}
    for name, joint in [('train-step.onnx', True), ('evaluate.onnx', False)]:
        graph, _ = aot_export_module(wrapper, (x,y), trace_joint=joint,
                                    output_loss_index=0 if joint else None,
                                    decompositions=decompositions)
        graphs[name] = graph

    def strip_source_metadata(message):
        # ONNX 导出器的调试元数据可能带有生成机器的文件路径。
        for field, value in list(message.ListFields()):
            if field.name in ('doc_string','metadata_props'):
                message.ClearField(field.name)
            elif field.type == field.TYPE_MESSAGE:
                for child in value if field.is_repeated else [value]:
                    strip_source_metadata(child)

    def encode(records, builder):
        encoded = []
        for record in records:
            ids, targets = builder([record], tokenizer, positions)
            encoded.append({'record_id': record['record_id'], 'ids': ids[0].tolist(),
                            'targets': targets[0].tolist(),
                            'text': record.get('text', record.get('prompt','')+record.get('answer','')),
                            **{key: record[key] for key in ('prompt', 'answer') if key in record}})
        return encoded

    encoded = {key: encode(records, make_sft_batch if key.startswith('sft') else make_pretrain_batch)
               for key, records in groups.items()}
    schedules = {}
    for key in ('pretrain','sft'):
        sampler = random.Random(presets[key]['seed'])
        schedules[key] = [sampler.sample(range(len(groups[key+'_train'])), batch_size)
                          for _ in range(1000)]

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='hello-browser-export-') as directory:
        stage = Path(directory)/'training';stage.mkdir()
        for name, graph in graphs.items():
            torch.onnx.export(graph, arguments, stage/name, input_names=input_names,
                              output_names=output_names if name.startswith('train') else output_names[:2],
                              opset_version=18, dynamo=True, external_data=False)
            exported = onnx.load(stage/name)
            strip_source_metadata(exported)
            onnx.checker.check_model(exported)
            onnx.save(exported, stage/name)
            private_roots = [b'/' + root + b'/' for root in (b'Users', b'home', b'private')]
            private_roots.append(b'\\' + b'Users' + b'\\')
            if any(value in (stage/name).read_bytes() for value in private_roots):
                raise ValueError('导出图仍包含本地路径')

        # 对不同的有效标签数量验证前向与反向，包括 SFT 的答案掩码。
        session = ort.InferenceSession(stage/'train-step.onnx', providers=['CPUExecutionProvider'])
        maximum = {'loss':0.,'logits':0.,'gradients':0.}
        batches = [(x,y), make_pretrain_batch(groups['pretrain_train'][128:144], tokenizer, positions),
                   make_sft_batch(groups['sft_train'][:batch_size], tokenizer, positions)]
        for bx, by in batches:
            model.zero_grad(set_to_none=True)
            logits = model(bx);loss = token_loss(logits, by);loss.backward()
            expected = [loss.detach(),logits.detach(),*[p.grad.detach() for p in params]]
            feeds = {n: v.detach().numpy() for n,v in zip(input_names, (*params,bx,by))}
            actual = session.run(None, feeds)
            for i,(a,b) in enumerate(zip(actual,expected)):
                np.testing.assert_allclose(a,b.numpy(),atol=3e-6,rtol=2e-3)
                key = 'loss' if i==0 else 'logits' if i==1 else 'gradients'
                maximum[key] = max(maximum[key],float(np.max(np.abs(a-b.numpy()))))

        parameter_info = []
        offset = 0
        for i,(name,p) in enumerate(model.named_parameters()):
            parameter_info.append({'input':f'param_{i}','name':name,'shape':list(p.shape),
                                   'offset':offset,'length':p.numel()})
            offset += p.numel()
        np.concatenate([p.detach().numpy().ravel() for p in model.parameters()]).astype('<f4').tofile(stage/'initial.f32')
        pretrained, saved_tokenizer, metadata = load_checkpoint(CODE/'artifacts/first_run/pretrain.pt')
        if pretrained.config != config or saved_tokenizer.itos != tokenizer.itos:
            raise ValueError('微调初始检查点与课程模型或词表不一致')
        if metadata['steps'] != presets['pretrain']['steps']:
            raise ValueError('微调需要课程完整预训练检查点')
        np.concatenate([p.detach().numpy().ravel() for p in pretrained.parameters()]).astype('<f4').tofile(stage/'pretrained.f32')
        data = {'tokens':tokenizer.itos,'groups':encoded,'schedules':schedules}
        (stage/'data.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8',newline='\n')
        from dataclasses import asdict
        manifest = {'schema':1,'config':asdict(config),'batch_size':batch_size,'sequence_length':positions,
                    'parameter_count':offset,'parameters':parameter_info,'optimizer':optimizer,'presets':presets,
                    'max_steps':1000,'sources':source_hashes(),'export_validation':maximum,
                    'files':{p.name:{'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(stage.iterdir())}}
        (stage/'model.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
        check_assets(stage)
        # 文件集合固定，禁止把人工新增文件当作缓存删除。
        expected_files = set(manifest['files']) | {'model.json'}
        if DESTINATION.exists() and any(p.name not in expected_files for p in DESTINATION.iterdir()):
            raise ValueError('网页训练目录包含非生成文件，拒绝覆盖')
        for p in stage.iterdir():
            DESTINATION.mkdir(exist_ok=True)
            shutil.copy2(p, DESTINATION/p.name)
        print(json.dumps({'parameters':offset,'presets':presets,'maximum_export_errors':maximum},ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    if parser.parse_args().check:
        check_assets();print('网页训练资源与课程源码一致。')
    else:
        build()
