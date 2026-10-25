"""把已保存的预训练前向记录做成离线解剖台，不训练、不修改实验文件。"""
import hashlib
import json
from pathlib import Path
import sys

from figure_tools import COLUMN, CODE

sys.path.insert(0, str(CODE))


def load_data():
    """返回真实trace、词表与输出矩阵；检查它们来自同一份权重。"""
    from tiny_lm.checkpoint import load_checkpoint
    from tiny_lm.trace import parameter_digest

    record_path = CODE/'artifacts/first_run/forward_trace.json'
    checkpoint = CODE/'artifacts/first_run/pretrain.pt'
    before = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    record = json.loads(record_path.read_text(encoding='utf-8'))
    model, tokenizer, _ = load_checkpoint(checkpoint)
    assert record['stage'] == 'pretrain'
    assert parameter_digest(model) == record['parameter_sha256']
    assert tokenizer.encode(record['input_text'], add_bos=True) == record['trace']['ids'][0]
    data = {
        'kind': 'saved_pretrain_forward', 'text': record['input_text'],
        'tokens': tokenizer.itos, 'trace': record['trace'],
        'parameter_sha256': record['parameter_sha256'],
        'output_weights': model.output.weight.detach().tolist(),
        'final_scale': model.final_norm.scale.detach().tolist(),
        'norm_eps': model.config.norm_eps,
    }
    # 逐位置、逐候选检查手动展开的点积，不能混用不同阶段的输出矩阵。
    for position, normalized in enumerate(data['trace']['normalized'][0]):
        for candidate, weights in enumerate(data['output_weights']):
            dot = sum(a*b for a, b in zip(normalized, weights))
            assert abs(dot-data['trace']['logits'][0][position][candidate]) < 1e-4
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == before
    return data


def build():
    """模板只增强观察，不在浏览器重训模型；内联数据使离线也可查看。"""
    source = Path(__file__).with_name('model_xray.html').read_text(encoding='utf-8')
    # 防止记录文本意外闭合script标签；这里不是将JSON拼入shell命令。
    data = json.dumps(load_data(), ensure_ascii=False, separators=(',', ':'))
    data = data.replace('<', '\\u003c')
    target = COLUMN/'chapters/16-transformer/model-inspector.html'
    target.write_text(source.replace('__MODEL_DATA__', data), encoding='utf-8')
    print(target)


if __name__ == '__main__':
    build()
