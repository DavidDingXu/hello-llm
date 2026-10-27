<h1 align="center">Hello LLM</h1>
<p align="center"><strong>Build a Small Model, Understand Large Models</strong></p>
<p align="center">20 lessons · 23 videos · Train in your browser</p>
<p align="center">
  <a href="https://daviddingxu.github.io/hello-llm/index.en.html"><img src="assets/read-online.en.svg" alt="Read online" width="216" height="52"></a>
  <a href="https://daviddingxu.github.io/hello-llm/index.en.html#downloads"><img src="assets/download-book.en.svg" alt="Download PDF / EPUB · Chinese editions" width="216" height="52"></a>
</p>
<p align="center">
  <a href="https://github.com/DavidDingXu/hello-llm/stargazers"><img src="https://img.shields.io/github/stars/DavidDingXu/hello-llm?style=flat&amp;logo=github&amp;label=Stars&amp;color=2f7d4a" alt="GitHub Stars"></a>
  <a href="https://github.com/DavidDingXu/hello-llm/forks"><img src="https://img.shields.io/github/forks/DavidDingXu/hello-llm?style=flat&amp;logo=github&amp;label=Forks&amp;color=2f7d4a" alt="GitHub Forks"></a>
  <a href="LICENSING.md"><img src="https://img.shields.io/badge/License-Non--commercial-2f7d4a?style=flat" alt="License: Non-commercial"></a>
</p>
<p align="center"><a href="README.md">简体中文</a></p>

## From one neuron to a model that generates text

An original course by **好好用 AI / DavidDingXu**. Follow one **92,352-parameter** language model through neurons, gradients, attention, pretraining, generation and supervised fine-tuning.

No prior Python or deep learning knowledge is required to start with the diagrams and browser experiments. All code runs on a CPU. Each lesson includes diagrams, code and exercises. Companion videos have Chinese audio and captions; PDF and EPUB downloads are Chinese editions.

**Try it:** [Edit and run a neuron](https://daviddingxu.github.io/hello-llm/course/01.en.html#python-lab) · [Train the model in your browser](https://daviddingxu.github.io/hello-llm/course/20.en.html#training-lab)

## Course contents

Start with the [introduction](chapters/intro/README.en.md) or [opening lesson](chapters/00-introduction/README.en.md).

### Make a numerical network learn

| Lesson | The question you will answer | Video · Chinese |
| :--- | :--- | :--- |
| 01 | [Neurons: What Does a Model Calculate Before It Writes the Next Character?](chapters/01-neuron/README.en.md) | [6:19](https://daviddingxu.github.io/hello-llm/course/01.en.html#lesson-video) |
| 02 | [Vectors and Matrices: Do Two Outputs Require Two Copies of the Code?](chapters/02-vectors-and-matrices/README.en.md) | [5:13](https://daviddingxu.github.io/hello-llm/course/02.en.html#lesson-video) |
| 03 | [Nonlinearity: Why Can Multiply-and-Add Not Express Four Simple Rules?](chapters/03-nonlinearity/README.en.md) | [4:30](https://daviddingxu.github.io/hello-llm/course/03.en.html#lesson-video) |
| 04 | [Gradients: Why Can an Update in the Right Direction Make Things Worse?](chapters/04-gradients/README.en.md) | [5:14](https://daviddingxu.github.io/hello-llm/course/04.en.html#lesson-video) |
| 05 | [Backpropagation: Must We Test All 9 Parameters One by One?](chapters/05-backpropagation/README.en.md) | [5:44](https://daviddingxu.github.io/hello-llm/course/05.en.html#lesson-video) |
| 06 | [The Training Loop: What Happens to Four Predictions After 500 Updates?](chapters/06-training-loop/README.en.md) | [5:31](https://daviddingxu.github.io/hello-llm/course/06.en.html#lesson-video) |

### Turn text into training examples

| Lesson | The question you will answer | Video · Chinese |
| :--- | :--- | :--- |
| 07 | [Embedding: How Does Text Become a Network Input?](chapters/07-embeddings/README.en.md) | [4:23](https://daviddingxu.github.io/hello-llm/course/07.en.html#lesson-video) |
| 08 | [Softmax: How Do Scores Become Next-Character Probabilities?](chapters/08-softmax/README.en.md) | [4:41](https://daviddingxu.github.io/hello-llm/course/08.en.html#lesson-video) |
| 09 | [Training Targets: How Does a Sentence Become a Learnable Task?](chapters/09-training-targets/README.en.md) | [4:32](https://daviddingxu.github.io/hello-llm/course/09.en.html#lesson-video) |

### Read context and assemble the model

| Lesson | The question you will answer | Video · Chinese |
| :--- | :--- | :--- |
| 10 | [Attention: How Does Predicting the Next Character Read Earlier Text?](chapters/10-attention/README.en.md) | [4:37](https://daviddingxu.github.io/hello-llm/course/10.en.html#lesson-video) |
| 11 | [Causal Masks: Why Is Parallel Training Not Peeking at the Answer?](chapters/11-causal-mask/README.en.md) | [4:09](https://daviddingxu.github.io/hello-llm/course/11.en.html#lesson-video) |
| 12 | [Multi-Head Attention: Where Does Each Head Read?](chapters/12-multi-head-attention/README.en.md) | [4:16](https://daviddingxu.github.io/hello-llm/course/12.en.html#lesson-video) |
| 13 | [RoPE: How Does the Model Know the Order?](chapters/13-rope/README.en.md) | [4:58](https://daviddingxu.github.io/hello-llm/course/13.en.html#lesson-video) |
| 14 | [SwiGLU: What Happens After Reading the Prefix?](chapters/14-swiglu/README.en.md) | [4:01](https://daviddingxu.github.io/hello-llm/course/14.en.html#lesson-video) |
| 15 | [Residual Connections and RMSNorm: Why Keep a Direct Path?](chapters/15-residual-and-rmsnorm/README.en.md) | [4:26](https://daviddingxu.github.io/hello-llm/course/15.en.html#lesson-video) |
| 16 | [The Complete Model: Follow the Character “欢” Through Every Step](chapters/16-transformer/README.en.md) | [4:42](https://daviddingxu.github.io/hello-llm/course/16.en.html#lesson-video) |

### Pretrain, generate and fine-tune

| Lesson | The question you will answer | Video · Chinese |
| :--- | :--- | :--- |
| 17 | [Pretraining: Why Can New Questions Get Worse as Training Questions Improve?](chapters/17-pretraining/README.en.md) | [5:39](https://daviddingxu.github.io/hello-llm/course/17.en.html#lesson-video) |
| 18 | [Generation: How Many Choices Does One Sentence Take?](chapters/18-generation/README.en.md) | [4:50](https://daviddingxu.github.io/hello-llm/course/18.en.html#lesson-video) |
| 19 | [Supervised Fine-Tuning: Why Can It Continue Text but Still Fail to Answer?](chapters/19-fine-tuning/README.en.md) | [6:21](https://daviddingxu.github.io/hello-llm/course/19.en.html#lesson-video) |
| 20 | [The Full Workflow: Connect Pretraining, Fine-Tuning, and Generation](chapters/20-full-workflow/README.en.md) | [6:29](https://daviddingxu.github.io/hello-llm/course/20.en.html#lesson-video) |

Finish with [closing thoughts](chapters/end/README.en.md). Runnable entries are in the [chapter and code index](docs/COURSE.en.md).

## Resources

[Run the code](docs/GETTING_STARTED.en.md) · [Video course](docs/VIDEOS.md) · [Experiment records](code/EXPERIMENTS.md)

## Contribute

Questions, corrections and translation reviews are welcome: [open an issue](https://github.com/DavidDingXu/hello-llm/issues/new/choose) or read the [contribution guide](CONTRIBUTING.md). Local reading and website maintenance are covered in the [build guide](docs/BUILD.md). Star the project if it helps you learn.

Maintained by **DavidDingXu / 好好用 AI**.

## License

Software: [PolyForm Noncommercial 1.0.0](LICENSE). Original text, figures, videos and data: [CC BY-NC 4.0](LICENSE-CONTENT). Both restrict commercial use; see [LICENSING.md](LICENSING.md).

## Links

[LINUX DO](https://linux.do/)
