"""第19讲：从预训练权重继续做全量监督微调，或查看原实验。

答案目标由 tiny_lm/data.py 的 make_sft_batch 构造；真实训练在
tiny_lm/train.py 的 run_sft。--inspect 只读已保存的结果；新训练需要
--checkpoint 指定预训练权重。运行：python -m lessons.l19 --inspect。
"""
import sys

if __name__ == '__main__':
    if '--inspect' in sys.argv:
        # 去掉本入口专用选项，再交给通用的实验记录查看器。
        sys.argv.remove('--inspect')
        from .experiments import main
        main(19)
    else:
        from tiny_lm.train import main
        args = sys.argv[1:]
        if '--out' not in args:
            # 微调另存目录，便于保留预训练权重并比较行为变化。
            args = ['--out', 'artifacts/my_sft', *args]
        main(['--stage', 'sft', *args])  # 加载指定的预训练权重，不重新初始化随机模型。
