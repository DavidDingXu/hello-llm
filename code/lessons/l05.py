"""第05讲的运行入口。

本讲实现：tiny_lm/manual_mlp.py::backward。
数值例子：lessons/experiments.py 的 lesson05 函数。
在项目根目录运行 python -m lessons.l05，打印结果并保存JSON记录。
"""
from .experiments import main

if __name__ == "__main__":
    # 讲次决定运行哪组输入；通用main负责解析输出位置和导出记录。
    main(5)
