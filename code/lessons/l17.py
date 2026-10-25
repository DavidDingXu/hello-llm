"""第17讲：从随机参数开始预训练，或查看已保存的原实验。

训练实现在 tiny_lm/train.py 的 run_pretrain/train_step；数据构造在
tiny_lm/data.py。--inspect 调用 experiments.lesson17 读取日志，
去掉该选项才开始新训练。运行：python -m lessons.l17 --inspect。
"""
import sys

if __name__ == '__main__':
    if '--inspect' in sys.argv:
        # 后续通用实验参数解析器不认识这个选项，因此先把它取走。
        sys.argv.remove('--inspect')
        from .experiments import main
        main(17)
    else:
        from tiny_lm.train import main
        args = sys.argv[1:]
        if '--out' not in args:
            # 新训练输出单独保存，保留artifacts/first_run中的原实验供对照。
            args = ['--out', 'artifacts/my_pretrain', *args]
        main(['--stage', 'pretrain', *args])  # 复用完整工程的训练入口，只运行预训练阶段。
