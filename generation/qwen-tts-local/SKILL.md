---
name: qwen-tts-local
description: 基于本地服务的 Qwen TTS 语音合成能力，支持指定音色与按描述设计音色两种模式。
trigger: 需要通过本地 Qwen TTS 服务把文本合成为语音时调用。
---

# Qwen TTS Local 本地语音合成

## 概述

这是一个基于本地服务的 Qwen TTS 执行 skill。

它支持两个入口：

| 模式 | pipeline_name | 用途 |
|------|---------------|------|
| custom_voice | `qwen_tts_customvoice` | 使用预置说话人音色合成 |
| voice_design | `qwen_tts_voicedesign` | 根据描述设计音色再合成 |

该 skill 的公开调用方式与 `ltx23-video` 一样，优先使用 bash 脚本，而不是 `python ...`。
内部为了确保中文文本在 Windows + bash 环境下稳定按 UTF-8 提交，提交阶段使用 Node transport helper 发送 multipart 请求。

## 输入

- 必填：`text`
- 可选：`language`
- 可选：`speaker`，传入时自动走 `qwen_tts_customvoice`
- 可选：`instruct`，用于风格描述或语气描述
- 必填：输出路径 `output`

## 输出

- 主产物：音频文件，通常为 `wav`
- done condition：成功提交任务、轮询到 `done`、并将结果下载到本地路径

## 后端

- 默认服务地址：`http://10.42.1.2:9200`
- 环境变量：`QWEN_TTS_LOCAL_BASE_URL`

## API 端点

- 提交：`POST {BASE_URL}/submit`
- 状态：`GET {BASE_URL}/status/{task_id}`
- 下载：`GET {BASE_URL}/download/{task_id}`
- 状态值：`submitted` → `queued` → `running` → `done`

## 脚本

### generate_qwen_tts_local.sh

位置：`scripts/generate_qwen_tts_local.sh`

内部 UTF-8 提交器：`scripts/submit_qwen_tts_local.mjs`

### 用法

```bash
# 使用预置音色
bash scripts/generate_qwen_tts_local.sh \
  --text "你是谁，你从哪里来？" \
  --language auto \
  --speaker Vivian \
  --instruct "清脆开心的声音" \
  --output outputs/qwen_tts_vivian.wav

# 仅使用描述设计音色
bash scripts/generate_qwen_tts_local.sh \
  --text "你是谁，你从哪里来？" \
  --language auto \
  --instruct "年轻男性开心的声音" \
  --output outputs/qwen_tts_designed.wav
```

## 规则

- 不主动改写用户文本
- 如果传入 `speaker`，自动走 `qwen_tts_customvoice`
- 如果未传入 `speaker`，自动走 `qwen_tts_voicedesign`
- `language` 默认使用 `auto`
- 中文文本提交通过 Node transport helper 构造 UTF-8 multipart，避免 bash + curl 在当前环境下污染字符编码
- 必须等待任务完成后再下载结果
- 下载失败可有限重试，但不能静默吞掉最终失败

## 预置说话人

- `Vivian`
- `Serena`
- `Uncle_Fu`
- `Dylan`
- `Eric`
- `Ryan`
- `Aiden`
- `Ono_Anna`
- `Sohee`

## 语言

- `auto`
- `chinese`
- `english`
- `french`
- `german`
- `italian`
- `japanese`
- `korean`
- `portuguese`
- `russian`
- `spanish`

## 工作流程

1. 接收 text、language、speaker、instruct 和输出路径
2. 根据是否传入 `speaker` 选择 pipeline
3. 向本地服务提交表单
4. 轮询任务状态直到 `done`
5. 下载结果并保存为本地音频文件

## 契约与产物

- 示例：`qwen-tts-local.example.json`
- Schema：`qwen-tts-local.schema.json`
- 该 contract 描述输入文本、可选音色/语言/描述，以及最终音频产物路径

## 目录结构

```text
qwen-tts-local/
├── qwen-tts-local.example.json
├── qwen-tts-local.schema.json
├── SKILL.md
└── scripts/
    ├── generate_qwen_tts_local.sh
    └── submit_qwen_tts_local.mjs
```

## 更新日志

- 2026-04-02: 默认服务地址更新为 `http://10.42.1.2:9200`
- 2026-04-02: 从 `C:\Users\jyfa\Desktop\test_qwen_tts.py` 整理为 generation skill，并改为 shell-based 本地服务调用
