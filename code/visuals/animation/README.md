# 图解与动画源工程

课程图形由源码生成。输入用蓝色、参数用紫色、输出用青色；静态图、步进实验和机制动画共享计算数据。

## 安装与预览

在本目录运行；Node.js 版本须符合 `package.json` 中的 `engines`：

```bash
npm ci
npm run lint
npx remotion studio --no-open
```

`NeuronFigure` 和 `CourseFigure` 为静态图，`NeuronFlow` 和 `CourseProcess` 为机制动画。无需安装这些制图依赖即可运行课程代码或阅读网站。

## 生成首讲素材

从 `code/` 运行 `node visuals/build_lesson01.mjs`，核对数值并更新 SVG、离线交互页及 `src/lesson01.json`。计算与场景源是 `src/neuron.mjs`；数据来自 `artifacts/lesson01.json`。

回到本目录导出 PNG 和 MP4：

```bash
node scripts/render_assets.mjs
```

可加 `--only-flow` 只生成完整流程图与动画，或加 `--only-network` 只生成网络结构图。视频为 14 秒无声机制演示。

## 生成其他章节素材

从 `code/` 运行 `python visuals/build_course_demos.py`，更新交互页与 `course-scenes.json`，然后在本目录执行：

```bash
node scripts/render_course.mjs --only-stills
node scripts/render_course.mjs --only-motion 12 13
```

可在参数末尾指定讲次。第 12、13 讲的几何运动由 `src/mechanisms.mjs` 按帧生成。PNG、GIF 和 MP4 共用场景；改数时修改数据或生成器，不手改导出的图片。

动画编码需要 FFmpeg。Remotion 首次运行可能下载浏览器；中间帧保存在系统临时目录。中文字体使用本机可用的 Hiragino Sans GB、微软雅黑或 Noto Sans CJK SC，不随项目分发系统字体。

[网站与书籍构建](../../../docs/BUILD.md)另有说明。Remotion 自身的授权条件见其[官方许可说明](https://www.remotion.dev/docs/license)。
