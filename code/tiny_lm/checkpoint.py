"""保存和恢复模型结构、词表及权重，避免只存权重却丢失字符编号含义。

检查点包含 config、vocab、state_dict 和 metadata；不保存优化器统计或随机数状态，
因此可用于加载推理和继续微调，但不提供逐步完全一致的中断续训。
"""

from dataclasses import asdict
from pathlib import Path

import torch

from .model import ModelConfig, TinyLM
from .tokenizer import CharTokenizer


def save_checkpoint(path, model, tokenizer, metadata=None):
    """写出检查点，无返回值；metadata 放训练阶段、步数等说明信息。

    state_dict 保存模型登记的参数及持久缓冲区，不包含一次前向的中间张量或梯度。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    # 先完整写临时文件，再替换目标文件，避免写到一半就覆盖已有检查点。
    torch.save({'config': asdict(model.config), 'vocab': tokenizer.to_dict(),
                'state_dict': model.state_dict(), 'metadata': metadata or {}}, temporary)
    temporary.replace(path)


def load_checkpoint(path):
    """在 CPU 上恢复模型和词表，返回 (model, tokenizer, metadata)。

    新建模型先得到临时初值，load_state_dict 再以保存的权重覆盖它们；
    返回模型处于 eval 模式，后续 train_step 会切回训练模式。
    """
    payload = torch.load(Path(path), map_location='cpu', weights_only=True)
    config = ModelConfig(**payload['config'])
    tokenizer = CharTokenizer.from_dict(payload['vocab'])
    if tokenizer.vocab_size != config.vocab_size:
        raise ValueError('词表与模型输出维度不匹配')
    model = TinyLM(config)
    model.load_state_dict(payload['state_dict'])
    model.eval()
    return model, tokenizer, payload['metadata']
