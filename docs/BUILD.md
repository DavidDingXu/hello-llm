# 本地阅读与构建

建议 Python 3.12。以下命令从仓库根目录执行；macOS 可用 `python3`，Windows 可用 `py`。

```bash
python -m pip install -r requirements-site.txt
python code/visuals/build_reading.py
python code/visuals/serve_reading.py --port 8878
```

打开 `http://127.0.0.1:8878/`。无需 Node.js 即可阅读网站。

## 配套视频

阅读页在标题下提供视频入口，展开后加载 B 站播放器，可直接在本页播放。需要更高清晰度时，点击“在 B 站高清观看”打开原视频。页面不自动播放，收起视频区时停止播放。视频为中文讲解，内嵌中文字幕，英文页面标明音轨语言。

`code/visuals/reading_site/videos.json` 维护章节与 B 站视频的对应关系。课程成片由 B 站提供，仓库只保留阅读页所需的封面；视频目录见[配套视频](../docs/VIDEOS.md)。离线文档可以阅读图文，观看课程视频需要联网。

## 浏览器 Python 实验

01—05 讲使用 Pyodide 314.0.7，在读者点击运行后才从 jsDelivr 加载运行时。计算在浏览器的独立 Worker 中执行，无需账号或服务器；首次加载需要网络。离线站点仍可阅读正文与逐步演示。双击 HTML 打开的页面可查看代码；要执行 Python，请打开在线实验，或通过本地 HTTP 阅读服务打开站点并联网加载运行时。

示例在 `code/visuals/browser_labs.py` 中维护，运算实现来自 `tiny_lm/scalar.py` 和 `tiny_lm/manual_mlp.py`。网站构建自动生成 `python-modules.json`，不另行维护算法副本。代码编辑器支持标准库和这几个课程模块，不支持 `import torch`；需要修改完整 PyTorch 源码时，按[运行指南](GETTING_STARTED.md)执行。完整模型的网页训练入口见下一节。

运行时加载上限 45 秒，执行上限 8 秒；停止或超时会终止 Worker，下次运行可重新启动。输出最多显示 50,000 字符。可编辑示例只在读者点击运行时执行，不从分享链接自动加载或执行代码。修改此功能时应检查首次加载、改数重跑、Python 报错、停止、超时恢复与窄屏排版。

正文 Python 代码块和可编辑实验均显示独立行号；编辑时增删行会实时更新，复制、下载与执行仍使用代码原文。代码编辑区使用本地 Python 语法高亮，跟随浅色、深色主题。Tab 缩进、Shift+Tab 反缩进，Enter 继续缩进；按 Esc 后再按 Tab 离开编辑区。原始 textarea 保存实际代码，复制、下载与执行均使用纯文本；高亮不可用时仍可编辑。

## 完整模型的网页训练

第 17、19、20 讲分别提供完整预训练、从课程预训练权重开始的问答微调，以及同一个模型连续完成两个阶段的实验。默认使用全部数据、92,352 个参数、批量 16、长度 32；预训练 1000 步、学习率 0.003，微调 300 步、学习率 0.001。AdamW、梯度裁剪、初始权重、答案掩码和种子 42 的逐批抽样顺序均来自课程代码。快速实验单独标明使用四条样本。

训练面板先展示实际使用的短句和问答。展开样本区后，可逐条查看全部训练与验证数据，并编辑现有训练样本；快速实验只显示本次使用的四条训练题和四条验证题。修改只保存在当前页面，刷新会恢复课程原样。

网页仍使用课程的79项词表与32项输入长度，每条文本最多31个字符（问答合计，另留BOS位置）。编辑后重新构造错位标签、EOS、右侧填充和答案掩码；未知字符、过长或空样本会在训练前报出具体原因，不截断内容。验证题只读，复制验证题到训练集也会被拦住。修改事实后，原验证答案可能不再适用，页面会说明评分仍以原答案为准。默认不修改样本时，批次抽样与课程原实验相同。

下载的实验记录附有本次使用的训练与验证样本、改动列表及原始数据摘要，比较两次运行时也显示修改过的样本数。“恢复课程样本”只还原学习材料；“重置参数与结果”还原训练设置并清空显示，不丢弃样本编辑。训练中的数据编辑不可用，防止显示材料与实际运行不一致。

读者可以修改步数和学习率，观察训练与验证损失、四个固定提示的生成变化，并比较同一页面的上次完整结果。微调结束还会逐题检查 24 条训练问法和 8 条留出问法，只有答案完整匹配且生成 EOS 才计为答对。验证集不参与更新；预训练和微调的评分目标不同，因此分阶段画图。生成达到长度上限时会标明，避免把尚未写完误判为错误结束。停止保留已显示的结果，再次开始会从该实验的初始权重重训，不恢复优化器状态。

网页训练采用从原始 PyTorch 模型导出的前向与反向图，通过 ONNX Runtime Web 1.30.0 的 WebAssembly CPU 后端计算梯度，JavaScript 执行同规则的 AdamW 更新。每次训练都实际更新参数；静态网站不需要服务端 Python 或账号。运行时只在点击开始后从 jsDelivr 加载。加载上限 45 秒、训练上限 5 分钟；较慢设备可减少步数。双击离线 HTML 时提供在线入口，本地 HTTP 服务下可运行，首次加载仍需要网络。

网页训练的初值和微调起点分别读取课程保存的 `artifacts/first_run/initial.pt` 与 `pretrain.pt`，以固定实验起点。配置和数学规则一致不代表跨运行时逐位一致。导出检查分别核对预训练和 SFT 批次的前向、损失及全部梯度；测试也使用 PyTorch 核对相同梯度下的 JavaScript 优化器更新。长期训练会放大浮点差异，最终损失和部分生成文字可能明显不同。网页展示本次实测结果，正文保留指定 PyTorch 环境的原始记录。研究具体数值或修改模型结构时，以配套 PyTorch 源码重新运行。

导出资源随源码版本保存，普通网站构建无需安装导出依赖。修改模型、训练配置、分词或课程数据后，需要用 Python 3.12 和 PyTorch 2.9.1 重新导出：

```bash
python -m pip install -r code/requirements-browser-training.txt
python code/visuals/export_browser_training.py
python code/visuals/export_browser_training.py --check
python code/visuals/build_reading.py
```

导出器清除图内机器路径，保存源文件与资源摘要，网站和 Release 构建检查同步状态。修改功能后需检查完整两阶段训练、单独微调、改数重跑、结果下载、停止与重置、网络失败后重试，以及中英文窄屏排版。

## 内容与媒体适配

- 技术正文唯一源：`chapters/*/README.md` 与 `README.en.md`。
- 网站：桌面优先 `images/web/*.svg`，手机使用原图。安全留白分栏保持图中全部元素；连续计算图的网页概览另行编排，点击后打开完整数值图。
- 电子书：从同版 [Release](RELEASE.md) 下载；发现问题时注明章节和页码，正文勘误会同步到后续版本。
- 网站由正文生成，不直接修补生成的 HTML。

重新生成网页配图需要 Node.js 和 Playwright：

```bash
npm install --no-save --package-lock=false playwright@1.62.1
npx playwright install chromium
node code/visuals/build_web_figures.cjs
python code/visuals/web_overviews.py
python code/visuals/build_reading.py
```

概览只用于无法安全分栏的连续计算图；通用分栏优先保留完整数值。顺序不能互换。网站与电子书使用不同排版，不把所有图强制拉成同一比例。

## 版本与离线阅读

`code/visuals/reading_site/release.json` 记录当前课程版本。PDF、EPUB 按同名版本提供，下载与校验方法见[发行说明](RELEASE.md)。

## 检查

```bash
python -m pip install -r code/requirements.txt
cd code
python -m unittest discover -s checks -v
python visuals/build_reading.py --check
```

检查覆盖模型、数据、逐讲实验和阅读站。重建网页后再检查配图、交互和窄屏阅读效果。

已安装 Playwright 并启动本地阅读服务时，可从仓库根目录运行共享交互回归，检查整图适配、缩放、退出焦点及展开实验后保留原参数：

```bash
node code/checks/check_reader_interactions.cjs http://127.0.0.1:8878/
```

## 重建图解与交互实验

以下命令从 `code/` 目录执行。首先运行对应逐讲实验生成 JSON，然后：

```bash
node visuals/build_lesson01.mjs
python visuals/intro_figures.py
python visuals/model_xray.py
python visuals/reader_figures.py
python visuals/loss_surface.py
python -m lessons.training_replay
python visuals/training_replay.py
python visuals/make_plots.py
python visuals/figures_02_06.py
python visuals/figures_07_13.py
python visuals/figures_14_20.py
python visuals/reference_figures.py
python visuals/build_course_demos.py
python visuals/build_reading.py
python visuals/serve_reading.py --port 8874
```

预览地址为`http://127.0.0.1:8874/index.html`。收到页面请求时自动同步Markdown和最新生成样式，响应禁用缓存。双击本地HTML也可阅读，但修改正文后应先重新生成。

阅读页提供本篇定位目录、答案与选读折叠、配图放大及原尺寸查看。源稿中的`details`保留完整内容，由`md_in_html`一起渲染内部公式、表格和代码。发布到不支持折叠的平台时应展开这些内容，保留完整答案与代码；不能把收起显示误当成可删除的正文。

PNG和MP4/GIF渲染需要Node.js、Remotion与FFmpeg：

```bash
npm --prefix visuals/animation ci
npm --prefix visuals/animation run lint
node visuals/animation/scripts/render_assets.mjs
node visuals/animation/scripts/render_course.mjs
```

只更新静态图可加`--only-stills`，只更新动画可加`--only-motion`，末尾可指定讲次，如`10 12`。中文字体采用本机Hiragino Sans GB、微软雅黑或Noto Sans CJK SC，不附带系统字体。图源与演示共享数值，生成的图片不单独改数字。

只渲染专栏介绍的两张静态图可运行`node visuals/animation/scripts/render_course.mjs --only-stills --intro`。第04讲的静态损失曲面由`loss_surface.py`生成；三维交互页使用下面的独立构建入口，不会被静态制图或旧的英文演示翻译流程覆盖。

第05、09、12、13、16、20讲的补充图由`reader_figures.py`生成SVG，再用`node visuals/animation/scripts/render_course.mjs --only-stills 05 09 12 13 16 20`渲染PNG。第13讲回算同一组K/V的换序；第16讲另用同一预训练权重，比较不同人名前文下“欢”的表示和候选分布；第20讲引用其图片目录中的交换事实对照图，其数值来自`artifacts/transfer_check.json`。`model_xray.py`检查保存的前向与预训练权重一致后，生成第16讲的离线模型解剖台；正文热力图与64项乘加图共用同一份数据入口。制图过程只读记录，不重新训练或覆盖权重。

第 04、07、12、13、16 讲提供本地打包的 Three.js 实验：

| 讲次 | 展示内容 | 数值来源与边界 |
| --- | --- | --- |
| 04 | 两个参数与损失曲面，比较单独/共同更新及学习率 | `l04.json`；曲线采样表示两次更新之间的损失，只有端点是实际更新 |
| 07 | 从参数表选行，再排成 `[B,T,D]` | `l07.json` 的四项手算表；改变编号不更新参数，不把坐标解释成语义方向 |
| 12 | 拆分特征轴、交换轴、合头 | `l12.json` 的 12 个数；仅重排，不执行投影或注意力计算 |
| 13 | 两对坐标按不同频率旋转，比较共同平移与只移 K | 先核对 `l13.json`，再按课程公式计算四维例子；V 不旋转 |
| 16 | 查表、两个模型块、归一化、候选分数 | `model_xray.load_data()` 核对同一预训练权重与保存记录；切换视图不重新训练 |

五个实验均在展开时才加载本地脚本，离线 HTML 不依赖 CDN。默认固定视角，自由旋转需主动开启；不支持 WebGL 时，数值、选择与核对仍可操作。320×568 的窄屏及较矮桌面保留主操作与当前结果，长索引表和说明在标明的局部区域滚动。普通 SVG 逐步演示支持聚焦当前步骤、全图、缩放；手机和较矮窗口直接在本页打开大窗口，大屏仍可原地展开。关闭实验会恢复阅读焦点。

修改三维实验后，从仓库根目录运行。先激活已安装课程 Python 依赖的环境（第 16 讲构建需要 PyTorch），并使用 Node.js 20 或以上：

```bash
python -m pip install -r code/requirements.txt
npm --prefix code/visuals/tensor3d ci
npm --prefix code/visuals/tensor3d test
npm --prefix code/visuals/tensor3d run build
python code/visuals/build_reading.py
python code/visuals/build_reading.py --check
```

`npm run build` 内部使用当前环境的 `python` 执行第 16 讲生成器，适用于 macOS / Windows 的 Python 虚拟环境。单独重建可运行 `surface-build.mjs`、`embedding-build.mjs`、`build.mjs`、`rope-build.mjs`，或 `python code/visuals/model3d.py`。脚本均按自身路径定位资源。

五个生成的 JavaScript 包与 Three.js MIT 许可随站点保存，普通网站构建无需安装 Node.js。每次修改需核对数学值、选择及键盘操作、视角恢复、窄屏、深色、减少动态效果与离线打开。公众号、知乎、PDF、EPUB 从原 Markdown 和静态图生成，实验仅作为补充链接；不能用交互画布替换推导、答案或代码。

## 部署学习站

站点为已生成的静态文件，可以直接使用 GitHub Pages 的分支发布方式，无需增加服务器。

1. 按[发行说明](RELEASE.md)发布与源码相同版本的电子书附件。
2. 重新生成并检查阅读页，将包含 `index.html`、`.nojekyll`、文章和站点资源的版本提交到 `main`。
3. 在仓库 **Settings → Pages → Build and deployment** 中，将 Source 设为 **Deploy from a branch**，选择 **main / (root)** 并保存。
4. 部署完成后，核对首页、`course/` 文章地址、旧链接跳转、英文页面、网页实验、视频及 PDF/EPUB 下载。完整课程视频在 B 站观看，电子书从同版 Release 下载；文章中的短动画随站点提供。完整课程成片和 `dist/` 不加入 Git。

启用分支发布后，`main` 的后续推送会更新网站；先核对版本和附件，再推送对应页面。配置细节见 [GitHub Pages 官方说明](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)。

## 可选的公开权重观察

这个扩展实验用于观察公开模型的真实前向，不是完成主线课程的前提：

```bash
python -m pip install -r requirements-reference.txt
python -m visuals.download_reference
python -m visuals.inspect_reference --use-downloaded
```

首次下载Qwen官方约1.5GB权重，放在系统临时目录；文件逐项校验。记录包含真实注意力、各层切片、缓存增长与不更新参数的检查。具体版本和口径见[运行记录](../code/EXPERIMENTS.md)。公开仓库保留小型记录，不上传第三方权重。

