# 使用许可

本项目由 DavidDingXu（好好用 AI）维护，提供可查看、学习和复现实验的源码及原创内容。软件与内容均采用限制商业用途的许可，不以 OSI 意义的开源软件发布。

## 适用范围

| 材料 | 许可 |
| --- | --- |
| Python / JavaScript 源码、测试、工作流、配置、导出的模型计算图，以及 HTML 页面中的程序、样式与页面结构 | [PolyForm Noncommercial 1.0.0](LICENSE) |
| 原创说明文字、图解、SVG 插图、配套视频与字幕、实验数据与记录、教学模型检查点 | [CC BY-NC 4.0](LICENSE-CONTENT) |

HTML 页面中的讲解文字和图解属于内容；驱动交互和计算的程序属于软件。文件扩展名不改变这一区分。除有单独标注外，上表适用于本版本实际包含的原创材料；第三方库、模型与引用资料遵循各自许可。

## 怎样使用

按对应许可进行非商业学习、修改、复现和分享，保留作者、来源与许可声明；分享修改后的内容时标明修改。软件分发还须保留 [NOTICE](NOTICE) 中的 Required Notice。

许可不自动覆盖超出条款允许范围的商业用途。商业产品、服务或其他商业利用须先取得权利人的另行授权。PolyForm 对个人用途及特定机构用途有具体规定，CC BY-NC 也有其非商业定义；完整条款为准，不仅按使用者是否为公司判断。许可不限制法律本来允许的使用。

权利人可以继续使用自己的原创作品，也可以另行授予许可。使用本项目不得暗示获得作者背书。

## 第三方材料

- [PyTorch](https://github.com/pytorch/pytorch) 与 [NumPy](https://github.com/numpy/numpy) 通过依赖安装，仍按各自随包许可证使用。本项目的限制不改变这些库的原许可。
- 网页按需加载的 [Pyodide](https://github.com/pyodide/pyodide) 和 [ONNX Runtime Web](https://github.com/microsoft/onnxruntime) 及其依赖继续遵循各自许可证；本项目不重新许可这些运行时。
- `artifacts/reference/` 保存 Qwen3-0.6B 的观察记录与下载校验信息，不包含该模型权重。模型来源为 [Qwen 官方仓库](https://huggingface.co/Qwen/Qwen3-0.6B)；本项目不重新许可第三方模型。
- 第 04、07、12、13、16 讲的三维实验打包了 Three.js 0.186.1，遵循 MIT 许可；原始许可及声明见 `visuals/reading_site/tensor3d-LICENSE.txt`。
- 标注了其他作者或来源的引用材料不因位于本仓库而转为本项目原创内容。

许可证正文分别取自 [PolyForm 官方文本](https://polyformproject.org/licenses/noncommercial/1.0.0)与 [Creative Commons 官方文本](https://creativecommons.org/licenses/by-nc/4.0/legalcode.txt)，未修改其条款。
