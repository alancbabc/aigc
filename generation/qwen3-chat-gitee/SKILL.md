---
name: qwen3-chat-gitee
description: Gitee Serverless Qwen3-32B 文本对话（非流式 POST /v1/messages）。
trigger: 需要在 Gitee 上调用 Qwen3 做多轮或非流式文本生成时调用。
---

# Qwen3 Chat（Gitee Serverless）

## 概述

- **端点**：`POST {AIGC_GITEE_BASE_URL}/messages`（默认 `https://ai.gitee.com/v1/messages`）
- **鉴权**：`Authorization: Bearer $AIGC_GITEE_API_KEY`
- **默认模型**：`Qwen3-32B`，可用环境变量 `AIGC_QWEN3_MODEL` 覆盖
- **本脚本仅支持非流式**：请求体强制 `stream: false`（流式需另行解析 SSE）

## 环境变量

| 变量 | 说明 |
|------|------|
| `AIGC_GITEE_API_KEY` | 必填（若仅配置了 `GITEE_API_TOKEN`，脚本会做同名兼容） |
| `AIGC_GITEE_BASE_URL` | 可选，默认 `https://ai.gitee.com/v1` |
| `AIGC_QWEN3_MODEL` | 可选，默认 `Qwen3-32B` |

脚本会尝试加载仓库根下的 `aigc/.env`（与 MV 流水线等脚本一致）。

## 脚本

路径：[`scripts/qwen3_chat.py`](scripts/qwen3_chat.py)

MV 流水线中「歌词段落划分」也可用专用脚本（本目录提供 HTTP 客户端 `client.py` 供其复用）：

- [`workflows/mv-production/scripts/infer_sections_qwen3.py`](../../workflows/mv-production/scripts/infer_sections_qwen3.py) — 读 `parse_lyrics.py` 产出的 lyrics-timing JSON，要求模型按 **`contracts/song-sections-llm/song-sections-llm.schema.json`** 仅返回一段 JSON。
- [`workflows/mv-production/scripts/infer_global_visual_style_qwen3.py`](../../workflows/mv-production/scripts/infer_global_visual_style_qwen3.py) — Stage 2：读 **`lyrics-timing.json`** + 段落上下文（**`song-sections-llm.json`** 或 legacy **`song-structure.json`**），输出 **`contracts/mv-global-visual-style/mv-global-visual-style.schema.json`** 形状的 `mv-global-visual-style.json`（含英文 `global_style_suffix`）。

```bash
cd aigc/generation/qwen3-chat-gitee/scripts

# 仅生成请求 JSON（不写密钥也可）
python qwen3_chat.py --prompt "用一句话问好" --dry-run

# 实际调用（需已配置 AIGC_GITEE_API_KEY）
python qwen3_chat.py --prompt "用一句话问好"

# 只打印助手回复正文
python qwen3_chat.py --prompt "1+1=?" --plain

# 使用自定义 body（参见 qwen3-chat-gitee.example.json）
python qwen3_chat.py --request ../qwen3-chat-gitee.example.json
```

## 响应解析

支持两种顶层形态：

1. **OpenAI 风格**：`choices[0].message.content`（字符串或结构化块数组），或 `choices[0].text`。
2. **Gitee `/messages` 消息体**：顶层 `role` / `type: message`，`content` 为 `{ "type": "text", "text": "..." }[]`，脚本拼接所有文本块。

非 `--plain` 时输出：`assistant_text`、`usage`、`model`、`id`、完整 `raw`。

## cURL 示例（非流式）

```bash
curl "https://ai.gitee.com/v1/messages" \
  --request POST \
  --header "Content-Type: application/json" \
  --header "Authorization: Bearer $AIGC_GITEE_API_KEY" \
  --data '{
    "model": "Qwen3-32B",
    "stream": false,
    "max_tokens": 256,
    "temperature": 0.7,
    "top_p": 0.9,
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

## 合约与示例

- [`qwen3-chat-gitee.schema.json`](qwen3-chat-gitee.schema.json)
- [`qwen3-chat-gitee.example.json`](qwen3-chat-gitee.example.json)

## 注意

- 若接口返回扫码/占位类 JSON（非 `choices`），需按 Gitee 控制台完成授权后再调本接口。
- 批量调用请自行加间隔，遵守平台限流。
