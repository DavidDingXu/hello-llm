# Run your first experiment

[简体中文](GETTING_STARTED.md)

Lessons 01–05 use only the Python standard library. For the full course, use **Python 3.12** with the pinned PyTorch and NumPy dependencies. NumPy in this release requires Python 3.12 or newer. No GPU, model API key or paid service is needed.

You can also [edit Python in the browser](https://daviddingxu.github.io/hello-llm/course/01.en.html#python-lab) or [train the complete small model](https://daviddingxu.github.io/hello-llm/course/20.en.html#training-lab) without installation or an account. The first load requires an internet connection.

## Get the project

```bash
git clone https://github.com/DavidDingXu/hello-llm.git
cd hello-llm/code
python -m lessons.l01
```

Alternatively, download the repository ZIP and open its `code` directory. Run all commands below there. Use `python3` on macOS/Linux or `py` on Windows if `python` is unavailable. The first example computes **4** from inputs `[2, 1]`, weights `[1, 3]` and bias `-1`.

## Install the full environment

The pinned PyTorch release provides wheels for Apple silicon Macs, Windows x64 and Linux x64/ARM64; Linux requires glibc 2.28 or newer. Intel Macs can run the first five lessons or use the browser experiments; PyTorch 2.9.1 does not provide an official Intel Mac wheel.

**macOS, Apple silicon:**

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

**Linux:**

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r requirements.txt
```

**Windows PowerShell:**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Windows and Linux use the [official CPU installation](https://pytorch.org/get-started/previous-versions/#v291) to avoid downloading CUDA dependencies that this course does not need. Calling the environment’s Python directly also avoids changing PowerShell execution policy.

## Generate text and train your own model

macOS/Linux:

```bash
.venv/bin/python -m lessons.l18 --checkpoint artifacts/first_run/pretrain.pt --prompt "早上，小丁喜欢" --greedy
.venv/bin/python -m tiny_lm.train --out artifacts/quickstart_run
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m lessons.l18 --checkpoint artifacts/first_run/pretrain.pt --prompt "早上，小丁喜欢" --greedy
.\.venv\Scripts\python.exe -m tiny_lm.train --out artifacts/quickstart_run
```

The first command uses the supplied pretrained weights and continues with **“红色的苹果。”**. The second starts from random weights, runs pretraining and fine-tuning, then saves checkpoints, logs, data snapshots and output comparisons. This quick start uses `artifacts/quickstart_run`; lessons 17–19 use `artifacts/my_run` separately. Use a new output directory for each repeated run. The English chapters retain the original Chinese training strings so you can reproduce the same examples.

## If you get stuck

- **Python 3.12 not found:** install Python 3.12 and reopen your terminal. Check `python3.12 --version` or `py -3.12 --version`.
- **No module named `lessons`:** enter the repository’s `code` directory and use `-m lessons.lNN`.
- **A dependency is still missing:** install and run with the same virtual environment interpreter.
- **No matching package version:** check Python version and system architecture against the supported platforms above.
- **Unknown characters:** first use the supplied prompts; this small character vocabulary does not support arbitrary Chinese text. Lesson 20 covers building a new vocabulary.
- **Different results:** compare the release tag, data snapshot, seed, settings and generation method. Exact long training trajectories can differ across environments.

Continue with the [English chapter index](COURSE.en.md). English questions and corrections are welcome in [Issues](https://github.com/DavidDingXu/hello-llm/issues/new/choose); include the chapter, version, command and relevant output.
