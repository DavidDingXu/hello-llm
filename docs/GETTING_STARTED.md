# 开始运行

[English](GETTING_STARTED.en.md)

第 01—05 讲只依赖 Python 标准库。第 06 讲起使用 PyTorch 与 NumPy，锁定依赖要求 **Python 3.12 或更高版本**，复现实验推荐使用 **Python 3.12**。整个课程使用 CPU，不需要 GPU 或模型 API 密钥。

只想先体验，可以[运行一个神经元](https://daviddingxu.github.io/hello-llm/course/01.html#python-lab)，也可以[直接训练完整小模型](https://daviddingxu.github.io/hello-llm/course/20.html#training-lab)，无需安装或登录，首次运行需要联网。

## 获取项目

```bash
git clone https://github.com/DavidDingXu/hello-llm.git
cd hello-llm/code
```

也可以下载 GitHub 的 ZIP，解压后进入 `code/`。下面的命令都在这个目录执行。

## 跑通第一个神经元

macOS / Linux：

```bash
python3 -m lessons.l01
```

Windows PowerShell：

```powershell
py -m lessons.l01
```

主算例的输入为 `[2, 1]`、权重为 `[1, 3]`、偏置为 `-1`，输出是 **4**。终端随后会展示改输入、改偏置的结果；配合[第一讲](../chapters/01-neuron/README.md)核对每一步。

## 安装环境，让模型续写

下面创建独立环境、安装完整依赖，并加载随课程提供的预训练权重。安装与运行都直接使用同一个虚拟环境解释器，无需修改 PowerShell 的执行策略。

这组固定版本提供 macOS Apple 芯片、Windows x64 和 Linux x64/ARM64 安装包；Linux 需要 glibc 2.28 或更新版本。Intel Mac 没有本课程所用 PyTorch 2.9.1 的官方安装包，可先使用网页实验；前五讲的标准库代码仍可直接运行。

macOS（Apple 芯片）：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m lessons.l18 --checkpoint artifacts/first_run/pretrain.pt --prompt "早上，小丁喜欢" --greedy
```

Linux：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m lessons.l18 --checkpoint artifacts/first_run/pretrain.pt --prompt "早上，小丁喜欢" --greedy
```

Windows PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m lessons.l18 --checkpoint artifacts/first_run/pretrain.pt --prompt "早上，小丁喜欢" --greedy
```

Windows / Linux 先按 [PyTorch 官方 CPU 安装方式](https://pytorch.org/get-started/previous-versions/#v291)安装 PyTorch，再安装其余依赖，避免为本课程下载 CUDA 依赖。

参考实验会续写 **“红色的苹果。”**。这一步使用已训练好的 92,352 参数模型。熟悉提示成功不代表能回答任意问题；[实验记录](../code/EXPERIMENTS.md)保留数据、环境与失败输出。

其他讲次使用相同解释器，例如 macOS / Linux 的 `.venv/bin/python -m lessons.l06`，或 Windows 的 `.\.venv\Scripts\python.exe -m lessons.l06`。

## 从随机参数开始训练

macOS / Linux：

```bash
.venv/bin/python -m tiny_lm.train --out artifacts/quickstart_run
```

Windows PowerShell：

```powershell
.\.venv\Scripts\python.exe -m tiny_lm.train --out artifacts/quickstart_run
```

命令依次准备数据、预训练、问答微调并生成对照。结果写入指定目录，包含权重、训练日志与数据快照。这次体验保存在 `artifacts/quickstart_run`；第17—19讲的逐讲实验另用 `artifacts/my_run`。重复实验时换一个目录，避免把不同轮次的权重和日志混在一起。

## 常见问题

- **提示找不到 `lessons`**：确认当前目录为 `hello-llm/code`，并用 `-m lessons.lXX` 运行。
- **安装了依赖仍提示缺包**：检查是否仍在使用 `.venv` 内的解释器，安装与运行必须对应。
- **提示找不到 Python 3.12**：先安装 Python 3.12，重新打开终端后再创建虚拟环境。macOS / Linux 用 `python3.12 --version`、Windows 用 `py -3.12 --version` 核对。
- **安装时提示没有匹配的 NumPy 或 PyTorch 版本**：先核对 Python 版本和系统架构；不要把系统自带的旧 Python 环境用于第 06 讲之后的固定依赖。
- **提示出现词表以外的字符**：当前模型使用字符词表，任意中文输入不一定受支持。先使用教程提示，词表迁移见第 20 讲。
- **结果与书中不同**：先核对 Release、依赖、数据快照、种子和生成策略，再比较训练与留出结果。

更多逐讲入口、步进日志与检查方法见[代码指南](../code/README.md)。对某一步计算有疑问，可以[提出学习问题](https://github.com/DavidDingXu/hello-llm/issues/new?template=question.yml)。
