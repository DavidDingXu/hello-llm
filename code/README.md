# 手写小模型，看懂大模型：配套代码

这里包含20讲实验入口、模型组件、参考数据与运行记录。先按[开始运行](../docs/GETTING_STARTED.md)准备环境，再根据下表阅读和修改对应实现。

## 从逐讲实验到完整项目

`lessons/lNN.py` 是运行入口，负责启动本讲实验。真正要阅读、修改的计算在下表的“实现”列；`lessons/experiments.py` 组织小算例与记录输出。

最终模型在 `tiny_lm/`：文字编码与数据构造 → 注意力、位置旋转和前馈网络 → `TransformerBlock` → `TinyLM` → 预训练、监督微调与生成。前几讲的标量手算用来核对原理，后续用张量批量执行相同计算。

| 部分 | 读哪些文件 |
| --- | --- |
| 文字与训练题 | [tokenizer.py](tiny_lm/tokenizer.py)、[data.py](tiny_lm/data.py)、[losses.py](tiny_lm/losses.py) |
| 完整网络 | [model.py](tiny_lm/model.py)，向下调用[模型块](tiny_lm/layers.py)、[注意力](tiny_lm/attention.py)和[位置旋转](tiny_lm/rope.py) |
| 训练与微调 | [train.py](tiny_lm/train.py)：共用训练步骤，分别构造预训练与答案目标 |
| 保存与生成 | [checkpoint.py](tiny_lm/checkpoint.py)、[generate.py](tiny_lm/generate.py) |
| 正确性与记录 | `checks/`、`artifacts/` |

每讲先读对应实现，再运行小实验。第16讲把组件装成完整模型；第17—19讲沿用同一套模型代码完成训练、生成和微调。

| 讲次 | 实现 | 运行入口 |
| --- | --- | --- |
| 01 | [scalar.py · neuron](tiny_lm/scalar.py#L22) | [l01.py](lessons/l01.py) |
| 02 | [scalar.py · linear](tiny_lm/scalar.py#L27) | [l02.py](lessons/l02.py) |
| 03 | [manual_mlp.py · forward](tiny_lm/manual_mlp.py#L10) | [l03.py](lessons/l03.py) |
| 04 | [experiments.py · lesson04](lessons/experiments.py#L50) | [l04.py](lessons/l04.py) |
| 05 | [manual_mlp.py · backward](tiny_lm/manual_mlp.py#L22) | [l05.py](lessons/l05.py) |
| 06 | [tensor_mlp.py · TensorMLP](tiny_lm/tensor_mlp.py#L9) | [l06.py](lessons/l06.py) |
| 07 | [tokenizer.py · CharTokenizer](tiny_lm/tokenizer.py#L8) · [experiments.py · lesson07](lessons/experiments.py#L113) | [l07.py](lessons/l07.py) |
| 08 | [baseline.py · CharBaseline](tiny_lm/baseline.py#L8) · [experiments.py · lesson08](lessons/experiments.py#L126) | [l08.py](lessons/l08.py) |
| 09 | [data.py · make_pretrain_batch](tiny_lm/data.py#L69) · [losses.py · token_loss](tiny_lm/losses.py#L9) | [l09.py](lessons/l09.py) |
| 10 | [attention.py · attention_2d](tiny_lm/attention.py#L30) | [l10.py](lessons/l10.py) |
| 11 | [attention.py · attention_2d](tiny_lm/attention.py#L30) | [l11.py](lessons/l11.py) |
| 12 | [attention.py · split_heads](tiny_lm/attention.py#L15) · [attention.py · CausalSelfAttention](tiny_lm/attention.py#L49) | [l12.py](lessons/l12.py) |
| 13 | [rope.py · apply_rope](tiny_lm/rope.py#L9) | [l13.py](lessons/l13.py) |
| 14 | [layers.py · SwiGLU](tiny_lm/layers.py#L33) | [l14.py](lessons/l14.py) |
| 15 | [layers.py · RMSNorm](tiny_lm/layers.py#L14) · [layers.py · TransformerBlock](tiny_lm/layers.py#L51) | [l15.py](lessons/l15.py) |
| 16 | [model.py · TinyLM](tiny_lm/model.py#L39) | [l16.py](lessons/l16.py) |
| 17 | [train.py · train_step](tiny_lm/train.py#L30) · [train.py · run_pretrain](tiny_lm/train.py#L122) | [l17.py](lessons/l17.py) |
| 18 | [generate.py · generate](tiny_lm/generate.py#L11) | [l18.py](lessons/l18.py) |
| 19 | [data.py · make_sft_batch](tiny_lm/data.py#L82) · [train.py · run_sft](tiny_lm/train.py#L171) | [l19.py](lessons/l19.py) |
| 20 | [experiments.py · lesson20](lessons/experiments.py#L340) | [l20.py](lessons/l20.py) |

## 运行逐讲实验

在本`code`目录运行。第01–05讲仅依赖Python标准库：

```bash
python -m lessons.l01
python -m lessons.l05
```

第06讲起需要PyTorch与NumPy，下面的依赖文件会一起安装。锁定依赖要求Python3.12及以上，复现推荐Python3.12；支持的平台与环境准备见[开始运行](../docs/GETTING_STARTED.md)。模型使用CPU：

Windows / Linux 请先按运行指南安装 CPU 版 PyTorch，再执行下面的依赖安装，避免下载课程不需要的 CUDA 组件。

```bash
python -m pip install -r requirements.txt
python -m lessons.l06
python -m lessons.l09
python -m lessons.l16
python -m lessons.l17 --inspect
python -m lessons.l18 --checkpoint artifacts/first_run/pretrain.pt --prompt '早上，小丁喜欢' --greedy
python -m lessons.l19 --inspect
python -m lessons.l20
```

macOS可用`python3`，Windows可用`py`。可先以`python -m venv .venv`建立环境；macOS直接调用`.venv/bin/python`，Windows PowerShell调用`.\.venv\Scripts\python.exe`，不必修改执行策略。本仓库的参考实验在 macOS 运行，具体环境与覆盖范围见[实验记录](EXPERIMENTS.md)。

01–20均有对应`lessons.lNN`入口。02–16、20默认把记录写入`artifacts/lessons/lNN.json`；第06讲实际训练XOR500步，第09讲训练字符基线1000步，均可用`--steps`改次数。17、19的`--inspect`读取原实验；去掉该选项才重新训练。18逐步生成且不更新参数。

想逐步检查中间计算，在同一条命令后加 `--verbose`，终端会显示关键源码行和本次变量。加 `--step` 则在教学观察点暂停，按回车继续，输入 `c` 后连续运行：

```bash
python -m lessons.l01 --verbose
python -m lessons.l05 --step
python -m lessons.l18 --greedy --verbose
```

日志标为“执行前”时，高亮的那行还没有执行；后面的变量变化和“返回值已算出”来自实际计算。日志只展开当前讲次的关键函数和部分调用，长张量显示形状与数值摘录，完整实验结果仍保存在 JSON 中。普通运行方式和计算结果不变。逐步模式包含人工停留，运行耗时不能用作训练速度比较。

17、19若使用 `--inspect`，只是查看已存记录；要观察真实训练过程，应执行训练入口，并使用新的输出目录。训练期间每50步会实时打印训练损失和留出损失；`--verbose` 还能观察一次实际更新中的损失、梯度和参数变化。

从随机参数走完整个项目：

```bash
python -m tiny_lm.train --out artifacts/my_run
python -m lessons.l18 --checkpoint artifacts/my_run/pretrain.pt --prompt '早上，小丁喜欢' --greedy
```

第一条命令依次完成数据准备、预训练、问答微调和三阶段生成对照。`my_run/`会得到`initial.pt`、`pretrain.pt`、`sft.pt`及相应日志；第二条单独加载其中的预训练权重做续写。每份权重都含词表与模型配置，可以独立重载。

若想从已有预训练权重单独重做微调：

```bash
python -m lessons.l19 --checkpoint artifacts/my_run/pretrain.pt --out artifacts/my_sft
```

`artifacts/first_run/`保存原始证据。完整训练命令省略`--out`时默认写入`artifacts/my_run/`；17、19独立入口默认分别写入`my_pretrain/`、`my_sft/`。重复训练要另选目录，才能同时保留多次结果。

## 模型与数据

79项字符词表，最长32项输入，宽度64，2块、每块2头、前馈宽128，总参数92,352。采用因果注意力、RoPE、SwiGLU、RMSNorm与Pre-Norm残差；线性层无偏置，输入输出参数不共享。

自制语料包含8个人物、水果与颜色，预训练256条训练/64条留出，问答24条训练/8条留出。按完整句式划分，人物事实相同。词表、清单与JSONL在`data/`；数据生成器在`tiny_lm/data.py`。具体成功和失败见[运行记录](EXPERIMENTS.md)。

原留出还含训练正文未见字符，不能单独隔离句式因素。`python -m lessons.validation_probe`可复现一组全字符已见的新组合补查；它是在看到原成绩后追加的检查。独立改数据时，请修改`tiny_lm/data.py`中的`FACTS`或模板；新训练按这些规则保存本次运行目录的`data/`快照，不再覆盖仓库根数据。课程微调入口沿用所加载预训练运行的快照；修改事实以后应启动新的完整训练。

## 独立练习与微调排错

第19讲固定比较原学习率、小学习率和12条问答加4条原正文，保存三个种子的全部结果：

```bash
python -m lessons.retention_experiment --inspect
python -m lessons.retention_experiment --out artifacts/my_retention.json
```

第20讲的数据与待完成函数在`exercises/`。先完成`transfer_task.py`的三个函数，再验收与训练；参考解法是`transfer_solution.py`。验收会用其他小字符集合检查函数，避免把79项词表或具体编号写死。

```bash
python -m lessons.transfer_challenge --module exercises.transfer_task
python -m lessons.transfer_challenge --module exercises.transfer_task --train --out artifacts/my_transfer
```

待完成文件第一次运行会指出尚未实现的函数。自己的训练目录包含`data.json`、`model.pt`和`report.json`；重复运行另选新目录。参考报告在`artifacts/transfer_challenge.json`，保留熟悉句式成功和留出句式漏颜色、额外续写的结果。参考记录可按相同种子重跑，不把结构检查通过说成新句式全部学会。

## 核对代码与文章

```bash
python -m unittest discover -s checks -v
```

安装网站与制图依赖后，还可以核对全部正文代码、本地资源与阅读页：

```bash
python -m pip install -r requirements-visuals.txt
python visuals/build_reading.py
python visuals/build_reading.py --check
python visuals/check_articles.py
```

检查覆盖手算、数据、模型、快照、回放、微调对照与独立迁移；完整仓库同时包含正文与阅读页检查。安装根目录 requirements-site.txt 后运行全部检查，避免跳过网站验证。

查看训练全过程：[在线回放](https://daviddingxu.github.io/hello-llm/chapters/20-full-workflow/training-replay.html)。页面展示首步真实计算、原日志曲线与三份权重的生成差别。首步在内存重放，原检查点保持不变。

```bash
# 读取作者保存的实验，导出真实回放数据。
python -m lessons.training_replay --out artifacts/training_replay.json
# 读取自己完成的全流程实验；使用该运行目录内经摘要核验的数据快照。
python -m lessons.training_replay --run artifacts/my_run --out artifacts/my_replay.json
```

## 完整教材与网站

模型、正文、图解和实验均在完整教材仓库内。上一级 `chapters/` 是正文源，PDF、EPUB 从同版 [Release](https://github.com/DavidDingXu/hello-llm/releases) 下载。网站构建使用 `python visuals/build_reading.py`；本地阅读使用 `python visuals/serve_reading.py --port 8878`。完整仓库的构建说明见根目录 `docs/BUILD.md`。

贡献与构建方法见 [CONTRIBUTING.md](../CONTRIBUTING.md) 和 [构建说明](../docs/BUILD.md)。

## 关注与交流

关注公众号「好好用 AI」，交流学习中的问题与实践心得。

<img src="assets/wechat-official-account.jpg" alt="好好用 AI 公众号二维码" width="200">

代码问题与勘误请优先提交 [Issue](https://github.com/DavidDingXu/hello-llm/issues)，方便复现和跟进。
