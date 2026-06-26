# VidFetch — Batch Video Downloader / 批量视频下载器

Paste multiple video URLs, auto-fetch titles and formats, download video+audio in parallel and merge to MP4 — all with a few clicks.

粘贴多个视频网址，自动获取标题和格式，按预设画质并行下载视频+音频并合并为 MP4。

Built with [yt-dlp](https://github.com/yt-dlp/yt-dlp) + [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter).

---

## Features / 功能

- **Batch input** — Paste URLs separated by newlines, spaces, or even concatenated; auto-detects all `http(s)://` links
  批量输入 — 换行、空格、紧挨着粘贴均可，自动识别所有网址

- **Auto-fetch** — Titles and formats are fetched in the background as soon as URLs are added to the queue
  自动获取 — 网址添加到队列后后台自动拉取视频标题和全部可用格式

- **Format preview** — Click any queue item to instantly see all available formats (resolution, codec, bitrate, size)
  格式预览 — 点击队列任意项，下方自动展示全部格式详情

- **Quality presets** — Best quality / 1080p / 720p / audio-only, one-click switch
  画质预设 — 最高画质+音质 / 1080p / 720p / 仅音频，一键切换

- **Parallel downloads** — Choose 1-6 concurrent downloads, controlled via `threading.Semaphore`
  并行下载 — 可选 1-6 个同时下载，Semaphore 控制并发

- **Real-time progress** — Per-item speed & ETA, plus an overall progress bar
  实时进度 — 每项独立显示速度和预估剩余时间，总进度条汇总

- **Cookies support** — Paste browser cookies for authenticated/ members-only content
  Cookies 支持 — 粘贴浏览器 Cookies 下载需要登录的内容

- **Right-click context menu** — Remove, retry, or copy URL from the queue
  右键菜单 — 从队列移除、重试失败项、复制网址

## Installation / 安装

### Dependencies / 依赖

```bash
pip install customtkinter yt-dlp pywinstyles
```

### FFmpeg / FFmpeg（必需）

Required for merging video+audio into MP4. Download and add to system PATH, or place alongside `vidfetch.py`.

合并视频+音频为 MP4 必需。下载后加入系统 PATH，或放在 vidfetch.py 同目录下。

- Download: https://ffmpeg.org/download.html
- Windows: `winget install ffmpeg`

### Run / 运行

```bash
cd VidFetch
python vidfetch.py
```

## Usage / 使用

1. **Paste URLs** — Paste multiple video URLs into the left text area (any format works)
   粘贴网址 — 把多个视频网址粘贴到左侧文本框（换行、空格、紧挨着都行）

2. **Choose preset** — Select quality preference (default: Best Quality)
   选择预设 — 选画质偏好（默认"最高画质+音质"即可）

3. **Add to queue** — Click "➕ Add to Queue"; titles and formats auto-fetch in background
   添加到队列 — 点"➕ 添加到队列"，后台自动获取标题和格式

4. **Start download** — Click "▶ Start Download", pick a save directory; parallel downloads begin
   开始下载 — 点"▶ 开始下载"，选保存目录，开始并行下载

5. **Monitor progress** — Queue table updates in real time; overall progress bar tracks completion
   查看进度 — 队列表格实时更新，总进度条显示整体进度

> **Tip**: Test with a single URL first to verify network and FFmpeg are working.
> **提示**: 首次使用建议先放 1 个网址测试，确认网络和 FFmpeg 正常。

## Quality Presets / 画质预设

| Preset / 预设 | yt-dlp Format String / 格式串 | Description / 说明 |
|------|-------------|------|
| 🎯 Best Quality / 最高画质+音质 | `bestvideo+bestaudio/best` | Highest bitrate video + highest bitrate audio, merged / 最高码率视频+最高码率音频，合并 |
| 📺 1080p + Best Audio / 1080p + 最佳音质 | `bestvideo[height<=1080]+bestaudio/best[height<=1080]` | Video capped at 1080p / 视频封顶 1080p |
| 📺 720p + Best Audio / 720p + 最佳音质 | `bestvideo[height<=720]+bestaudio/best[height<=720]` | Video capped at 720p / 视频封顶 720p |
| 🎵 Audio Only / 仅最高音频 | `bestaudio/best` | Audio only, no video / 只要音频，不下载视频 |

## Concurrency Guide / 并发建议

| Slots / 数量 | Recommendation / 建议 |
|---|---|
| 1-2 | Stable; for rate-limited sites / 稳定，适合限速严格的网站 |
| 3 | Default; fast and reliable / 默认，快且稳 |
| 4-6 | Faster with good bandwidth, but may trigger rate limits / 网速好时更快，但可能触发限流 |

## Project Structure / 项目结构

```
VidFetch/
├── vidfetch.py    # Main application / 主程序
├── ui_utils.py    # UI utilities: themes, treeview styling, popup menus / UI 工具模块
├── vidfetch.ico   # Application icon / 应用图标
└── README.md
```

## Tech Stack / 技术栈

| Component / 组件 | Purpose / 用途 |
|---|---|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Format extraction & download engine / 视频格式解析和下载引擎 |
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | Modern desktop UI framework / 现代桌面 UI 框架 |
| [pywinstyles](https://github.com/Akascape/py-window-styles) | Windows 11 title bar Mica effect / Windows 11 标题栏效果 |
| `threading.Semaphore` | Concurrent download control / 并发下载控制 |
| `ttk.Treeview` | Format table & queue table / 格式表格和队列表格 |

## License / 许可证

MIT
