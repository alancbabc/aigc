---
name: ltx23-video
description: LTX-2 视频生成能力，支持两种模式：音频驱动视频生成（自建服务）与高质量图文生成视频（Gitee API）。
trigger: 需要用音频或图像生成视频时调用。
---

# LTX-2 视频生成

## 概述

提供两个独立的视频生成入口：

| 模式 | 脚本 | 后端 | 用途 |
|------|------|------|------|
| audio_to_video | `generate_a2v.sh` | 自建服务 `10.0.180.14:8000` | 音频驱动、数字人、口播视频，支持音频+图像+文本组合输入 |
| image_to_video | `generate_hq_gitee.sh` | Gitee API | 图像+文本生成视频 |

## 脚本

### 1. generate_a2v.sh — 音频驱动视频

**后端**：自建服务 `http://10.0.180.14:8000`

**输入**：
- 必填：音频文件（`.wav` 或 `.mp3`）
- 必填：prompt（文本描述）
- 可选：参考图像（用于定义角色或场景）

**用法**：

```bash
# 纯音频
bash scripts/generate_a2v.sh \
  -a /path/to/audio.wav \
  -p "A man speaking to the camera" \
  -o output.mp4

# 音频 + 参考图
bash scripts/generate_a2v.sh \
  -a /path/to/audio.wav \
  -p "A man speaking to the camera" \
  --images /path/to/character.png \
  -o output.mp4

# 多图
bash scripts/generate_a2v.sh \
  -a /path/to/audio.wav \
  -p "A man speaking to the camera" \
  --images "img1.png,img2.png" \
  -o output.mp4
```

**默认参数**：1536×1024、24fps、121 帧、30 推理步数、5 秒

**实现说明**：
- `generate_a2v.sh` 现在不依赖本地 Python 解释器来计算帧数或解析返回 JSON，适合当前仓库的 bash/Windows 混合环境直接调用。
- 这可以避免 `WindowsApps/python.exe` 这类代理入口导致脚本在提交请求前提前退出。

**API 端点**：
- 提交：`POST {BASE_URL}/submit`
- 状态：`GET {BASE_URL}/status/{task_id}`
- 下载：`GET {BASE_URL}/download/{task_id}`
- 状态值：`submitted` → `queued` → `running` → `done`

**环境变量**：`LTX23_BASE_URL`（默认 `http://10.0.180.14:8000`）

---

### 2. generate_hq_gitee.sh — 高质量图文生成

**后端**：Gitee API `https://ai.gitee.com`

**输入**：
- 必填：参考图像
- 必填：prompt（文本描述）
- 可选：视频时长、分辨率、推理步数等

**用法**：

```bash
# 设置 token
export GITEE_API_TOKEN="your_token"

# 基本调用
bash scripts/generate_hq_gitee.sh \
  -p "A cinematic portrait shot" \
  -i /path/to/image.png \
  -o output.mp4

# 自定义参数（2秒视频）
bash scripts/generate_hq_gitee.sh \
  -p "A man says hello" \
  -i character.png \
  -o output.mp4 \
  -n 49 -f 24 -s 8 \
  --token "your_token"
```

**默认参数**：512×640、24fps、63 帧、8 推理步数

**注意**：分辨率必须是 64 的倍数

**API 端点**：
- 提交：`POST https://ai.gitee.com/v1/async/videos/image-to-video`
- 状态：`GET https://ai.gitee.com/api/v1/task/{task_id}`
- 下载：成功时返回 `output.file_url`

**环境变量**：`GITEE_API_TOKEN`

## 规则

- 音频格式必须为 `.wav` 或 `.mp3`
- 图像格式必须为 `.png`
- 视频帧数必须满足 `8n + 1` 格式
- 必须等待任务完成后再下载结果
- 不主动改写用户 prompt
- 优先使用仓库内当前版本的 `generate_a2v.sh`，不要回退到旧的 Python 依赖版脚本

## 目录结构

```
ltx23-video/
├── SKILL.md                 # 说明文档
└── scripts/
    ├── generate_a2v.sh      # 音频驱动视频（自建服务）
    └── generate_hq_gitee.sh # 高质量图文生成（Gitee API）
```

## 更新日志

- 2026-03-31: 修复 `generate_a2v.sh` 在 bash/Windows 混合环境下对本地 Python 的硬依赖，改为 Python-free 帧数计算与响应解析，并成功用 `source_male.wav` 完成一次 audio_to_video 调用
- 2026-03-30: 整理为两个独立脚本，audio 用自建服务，HQ 用 Gitee API
- 2026-03-30: 新增 `generate_hq_gitee.sh`，支持 Gitee API 调用
- 2026-03-30: 确认 audio_to_video 支持组合输入（音频+图像+文本）
- 2026-03-30: 新增 cURL 脚本封装
- 2026-03-26: 初始创建
