# 版本与离线下载

课程版本记录在 `code/visuals/reading_site/release.json`，对应同名 Git 标签 `v<版本>`。正文、代码、网页实验与电子书使用同一版本，便于对照学习与复现。

从 [Releases](https://github.com/DavidDingXu/hello-llm/releases) 选择版本，按需下载：

| 附件 | 用途 |
| --- | --- |
| `hello-llm-v<版本>-zh-CN.pdf` | 固定分页，适合电脑阅读与打印 |
| `hello-llm-v<版本>-zh-CN.epub` | 可调整字号，适合手机与电子阅读器 |
| `SHA256SUMS.txt` | 核对下载文件是否完整 |

代码、文章和网站文件随同名标签的 **Source code** 包提供；PDF、EPUB 可直接离线阅读。需要在本机打开学习站，见[本地阅读与构建](BUILD.md)。配套课程视频见 [B 站视频目录](VIDEOS.md)。

核对某个附件的 SHA-256：

```bash
# macOS
shasum -a 256 下载的文件
```

```powershell
# Windows PowerShell
Get-FileHash 下载的文件 -Algorithm SHA256
```

将结果与 `SHA256SUMS.txt` 对应条目比较。历史版本请使用同名标签的代码和附件；修订发布为新版本，保留原有标签与附件。各版本变化见[变更记录](../CHANGELOG.md)。
