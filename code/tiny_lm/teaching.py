"""课程可选教学日志：沿真实源码观察变量，不改写模型算法。

line 事件发生在该行执行之前，return 事件发生在函数返回时。
--step 在观察点等待读者按回车，输入 c 则连续运行。
暂停时间属于教学操作，不能拿带暂停的耗时当作训练性能。
"""
import ast
import json
import math
from pathlib import Path
import sys
from contextlib import contextmanager

CODE = Path(__file__).resolve().parents[1]

WATCH = {
    1: [('tiny_lm/scalar.py', 'forward'), ('tiny_lm/scalar.py', 'relu')],
    2: [('tiny_lm/scalar.py', 'linear'), ('tiny_lm/scalar.py', 'forward')],
    3: [('tiny_lm/manual_mlp.py', 'forward')],
    4: [('lessons/experiments.py', 'lesson04')],
    5: [('tiny_lm/manual_mlp.py', 'backward'), ('tiny_lm/manual_mlp.py', 'step')],
    6: [('tiny_lm/tensor_mlp.py', 'forward'), ('tiny_lm/tensor_mlp.py', 'train_xor')],
    7: [('lessons/experiments.py', 'lesson07')],
    8: [('lessons/experiments.py', 'lesson08')],
    9: [('tiny_lm/data.py', 'make_pretrain_batch'), ('tiny_lm/losses.py', 'token_loss')],
    10: [('tiny_lm/attention.py', 'attention_2d')],
    11: [('tiny_lm/attention.py', 'attention_2d')],
    12: [('tiny_lm/attention.py', 'split_heads'), ('tiny_lm/attention.py', 'merge_heads')],
    13: [('tiny_lm/rope.py', 'apply_rope'), ('tiny_lm/rope.py', 'rotate')],
    14: [('lessons/experiments.py', 'lesson14')],
    15: [('tiny_lm/layers.py', 'forward')],
    16: [('tiny_lm/model.py', 'forward')],
    17: [('tiny_lm/train.py', 'train_step')],
    18: [('tiny_lm/generate.py', 'generate')],
    19: [('tiny_lm/data.py', 'make_sft_batch'), ('tiny_lm/train.py', 'train_step')],
    20: [('lessons/experiments.py', 'lesson20')],
}

NAMES = set('name values i j w b t d heads head_dim batch seq width inputs x y weights bias total value weight row z hidden prediction cache target params gradients learning_rate d_output d_hidden d_z table ids selected scores p shifted variant q k v output mask allowed weights rms normalized residual normalized_x tokens prefix targets pairs max_len logits loss grad_norm old_value gradient new_value index probabilities generated stop_reason step observe_token result eps inverse x1 x2 cos sin positions frequencies up gate_input gate product out changed a b start'.split())


def value_summary(value, depth=0):
    """小数表完整显示；大张量明确写出形状和前八项，避免日志淹没画面。"""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if depth > 3:
        return '…'
    if hasattr(value, 'detach') and hasattr(value, 'shape'):
        tensor = value.detach().cpu()
        result = {'shape': list(tensor.shape), 'dtype': str(tensor.dtype)}
        if tensor.numel() <= 12:
            result['values'] = value_summary(tensor.tolist(), depth)
        else:
            result['first_8'] = value_summary(tensor.reshape(-1)[:8].tolist(), depth)
        if getattr(value, 'is_leaf', False) and getattr(value, 'grad', None) is not None:
            result['grad'] = value_summary(value.grad, depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        result = [value_summary(v, depth + 1) for v in value[:12]]
        return result if len(value) <= 12 else {'length': len(value), 'first_12': result, 'last_8': [value_summary(v, depth + 1) for v in value[-8:]]}
    if isinstance(value, dict):
        return {str(k): value_summary(v, depth + 1) for k, v in list(value.items())[:12]}
    return None


class Observer:
    def __init__(self, number, step):
        self.number, self.step = number, step
        self.targets = {(str(CODE / p), name) for p, name in WATCH[number]}
        self.called, self.active, self.seen, self.completed = set(), set(), set(), set()
        self.sources = {p: Path(p).read_text(encoding='utf-8').splitlines() for p, _ in self.targets}
        self.previous = {}
        self.exceptions = {}
        self.count = 0
        self.executable = {}
        for path in self.sources:
            tree = ast.parse(Path(path).read_text(encoding='utf-8'))
            # 只停在完整语句开头，不在多行字典/表达式的每个续行停一次。
            self.executable[path] = {n.lineno for n in ast.walk(tree) if isinstance(n, ast.stmt)
                and not isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom))
                and not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str))}

    def __call__(self, frame, event, arg):
        path, name = frame.f_code.co_filename, frame.f_code.co_name
        key = (path, frame.f_code.co_qualname)
        if event == 'call':
            if (path, name) not in self.targets or key in self.called:
                return None
            if self.number == 3 and frame.f_locals.get('inputs') != [0, 1]:
                return None
            self.called.add(key)
            self.active.add(id(frame))
            return self
        if id(frame) not in self.active:
            return None
        if event == 'exception':
            self.exceptions[id(frame)] = f'{arg[0].__name__}: {arg[1]}'
            return self
        if event == 'line':
            # 捕获异常后仍继续执行的函数，不应被记成异常退出。
            self.exceptions.pop(id(frame), None)
        line = frame.f_lineno
        location = (key, line)
        progress = self.number in (1, 2) and path.endswith('scalar.py') or self.number == 5 and name == 'step'
        if self.number == 6 and name == 'train_xor' and 'rows.append' in self.sources[path][line - 1]:
            progress = frame.f_locals.get('step', 0) % 100 == 0
        if self.number == 18 and name == 'generate' and 'tokens.append(selected)' in self.sources[path][line - 1]:
            progress = True
        if event == 'line':
            if line not in self.executable[path] or (location in self.seen and not progress):
                return self
            self.seen.add(location)
        elif event == 'return':
            self.active.discard(id(frame))
            self.completed.add((path, name))
            error = self.exceptions.pop(id(frame), None)
            if error:
                print(f'\n{frame.f_code.co_qualname} 抛出异常：{error}', flush=True)
                return self
        else:
            return self
        values = {}
        for name_, val in frame.f_locals.items():
            if name_ in NAMES:
                summary = value_summary(val)
                if summary is not None:
                    values[name_] = summary
        if event == 'return':
            values['return'] = value_summary(arg)
        if self.number == 18 and 'selected' in frame.f_locals:
            tok = frame.f_locals['tokenizer']
            values['selected_token'] = tok.itos[frame.f_locals['selected']]
        self.count += 1
        phase = '执行前' if event == 'line' else '返回值已算出'
        source = str(Path(path).relative_to(CODE))
        print(f'\n[{self.count:02d}] {source}:{line} · {frame.f_code.co_qualname} · {phase}', flush=True)
        print('  ' + self.sources[path][line - 1].strip(), flush=True)
        changed = {k: v for k, v in values.items() if k not in self.previous or self.previous[k] != v}
        for name_, val in changed.items():
            text = json.dumps(val, ensure_ascii=False, allow_nan=False)
            if len(text) > 200:
                text = text[:200] + '…（后略）'
            print(f'  {name_} = {text}', flush=True)
        self.previous = values
        if self.step:
            try:
                command = input('  回车继续；输入 c 连续运行：').strip()
            except EOFError:
                command = 'c'
            if command in ('c', 'continue'):
                self.step = False
        if not self.active and self.completed >= self.targets:
            sys.settrace(None)
        return self



def add_observation_arguments(parser):
    """逐讲入口共用的可选参数；不改变普通运行方式。"""
    parser.add_argument('--verbose', action='store_true', help='显示关键源码行和本次运行的变量')
    parser.add_argument('--step', action='store_true', help='在教学观察点暂停；回车继续，c 连续运行')


@contextmanager
def observe_lesson(number, *, verbose=False, step=False):
    """临时观察当前进程，离开后恢复原 trace；不修改模型、梯度或输入。"""
    if not verbose and not step:
        yield
        return
    previous = sys.gettrace()
    observer = Observer(number, step)
    print('教学日志：执行前显示的是该行尚未执行时的变量；返回时显示计算结果。', flush=True)
    if step:
        print('逐步模式含人工停留，耗时不代表训练性能。', flush=True)
    sys.settrace(observer)
    try:
        yield
    finally:
        sys.settrace(previous)
