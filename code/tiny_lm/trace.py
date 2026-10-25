"""将计算中的张量和普通数据导出为 JSON，并对模型状态计算内容摘要。

导出记录可供检查和绘图使用；转换过程不参与反向传播，也不更新模型。
"""
import hashlib
import json
import math
from pathlib import Path


def json_value(value):
    """递归转成 JSON 可表示的数据；张量脱离梯度图后复制到 CPU 并转成列表。"""
    if hasattr(value, 'detach'):
        return json_value(value.detach().cpu().tolist())
    if isinstance(value, dict):
        return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_value(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        # 因果掩码里的 -inf 等非有限数转为 null，保证生成的是标准 JSON。
        return None
    return value


def export_trace(path, value):
    """将结构化记录写为 UTF-8 JSON，无返回值；不会保存自动求导的计算图。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_value(value), ensure_ascii=False, indent=2, allow_nan=False),
                    encoding='utf-8', newline='\n')


def parameter_digest(model):
    """对 state_dict 的名称与数值字节计算 SHA-256 字符串，用于核对权重是否变化。

    摘要不是参数副本，无法靠它恢复模型；这里也不会把梯度或优化器状态算入摘要。
    """
    digest = hashlib.sha256()
    for name, parameter in model.state_dict().items():
        digest.update(name.encode())
        digest.update(parameter.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()
