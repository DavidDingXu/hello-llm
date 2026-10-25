"""第18讲：加载一份权重，固定参数，逐项生成文字。

算法在 tiny_lm/generate.py 的 generate，加载在 tiny_lm/checkpoint.py。
本入口把命令行参数交给它们，再打印每次选择的记录，不执行训练。
运行：python -m lessons.l18 --greedy。
"""
import argparse
import json
from pathlib import Path
from tiny_lm.checkpoint import load_checkpoint
from tiny_lm.generate import generate
from tiny_lm.teaching import add_observation_arguments, observe_lesson

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', type=Path, default=Path('artifacts/first_run/pretrain.pt'))
    parser.add_argument('--prompt', default='早上，小丁喜欢')
    parser.add_argument('--greedy', action='store_true')
    parser.add_argument('--temperature', type=float, default=.8)
    parser.add_argument('--max-new-tokens', type=int, default=8)
    add_observation_arguments(parser)
    args = parser.parse_args()
    # 权重、模型配置与词表一同恢复，避免字符编号与参数行对应错位。
    model, tokenizer, _ = load_checkpoint(args.checkpoint)
    # greedy每次选最大项；采样分支才使用temperature。生成内部遇到EOS或长度上限停止。
    with observe_lesson(18, verbose=args.verbose, step=args.step):
        result = generate(model, tokenizer, args.prompt, greedy=args.greedy,
                          temperature=args.temperature, max_new_tokens=args.max_new_tokens)
    print(json.dumps(result, ensure_ascii=False, indent=2))
