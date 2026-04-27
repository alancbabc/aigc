---
name: qwen-image-local
description: 基于本地服务的 Qwen Image 图像生成能力，支持文生图与图生图编辑两种模式。
trigger: 需要通过本地 Qwen Image 服务生成或编辑静态图像时调用。
---

# Qwen Image Local 本地图像生成

## 概述

这是一个基于本地服务的 Qwen Image 执行 skill。

它支持两个入口：

| 模式 | pipeline_name | 用途 |
|------|---------------|------|
| text_to_image | `qwen_image` | 纯文生图 |
| image_edit | `qwen_image_edit` | 参考图编辑 / 图生图 |

该 skill 对应的服务端接口风格与 `ltx23-video` 的本地服务模式一致：先 submit，再轮询 status，最后 download。

## 输入

- 必填：`prompt`
- 必填：输出路径
- text_to_image 常用参数：`width`、`height`、`num_inference_steps`
- image_edit 额外必填：至少 1 张参考图 `images[]`
- 可选：`negative_prompt`、`seed`
- 可选：`base_url`，默认从环境变量读取

## 输出

- 主产物：生成图像文件（通常为 `png`）
- done condition：成功提交任务、轮询到 `done`、并将下载结果保存到本地路径

## 后端

- 默认服务地址：`http://10.42.1.1:9000`
- 环境变量：`QWEN_IMAGE_LOCAL_BASE_URL`

## API 端点

- 提交：`POST {BASE_URL}/submit`
- 状态：`GET {BASE_URL}/status/{task_id}`
- 下载：`GET {BASE_URL}/download/{task_id}`
- 状态值：`submitted` → `queued` → `running` → `done`

## 脚本

### generate_qwen_image_local.sh

位置：`scripts/generate_qwen_image_local.sh`

支持：

- 文生图：不传 `--images`
- 图像编辑：传 `--images img1.png[,img2.png,...]`

### 用法

```bash
# 文生图
bash scripts/generate_qwen_image_local.sh \
  --prompt "a girl with a red hat" \
  --width 1328 \
  --height 1328 \
  --output outputs/case-text.png

# 图生图编辑
bash scripts/generate_qwen_image_local.sh \
  --prompt "a girl with a red hat" \
  --images refs/case1.png \
  --output outputs/case-edit.png

# 多图编辑
bash scripts/generate_qwen_image_local.sh \
  --prompt "a cinematic portrait" \
  --images "refs/a.png,refs/b.jpg" \
  --steps 40 \
  --output outputs/case-multi.png
```

## 规则

- 不主动改写用户 prompt
- 如果传入 `images[]`，自动走 `qwen_image_edit`
- 如果不传 `images[]`，自动走 `qwen_image`
- 参考图仅允许 `.png` / `.jpg` / `.jpeg`
- 如果未显式提供宽高，默认使用 `1328x1328`
- 必须等待任务完成后再下载结果
- 下载失败可有限重试，但不能静默吞掉最终失败

## 工作流程

1. 接收 prompt、尺寸、可选参考图和输出路径
2. 选择 `qwen_image` 或 `qwen_image_edit`
3. 向本地服务提交 multipart 表单
4. 轮询任务状态直到 `done`
5. 下载结果并保存为本地图像文件

## 契约与产物

- 示例：`qwen-image-local.example.json`
- Schema：`qwen-image-local.schema.json`
- 该 contract 描述请求参数、本地服务下载行为和最终图像产物路径

## 目录结构

```
qwen-image-local/
├── qwen-image-local.example.json
├── qwen-image-local.schema.json
├── SKILL.md
└── scripts/
    ├── generate_qwen_image_local.py
    └── generate_qwen_image_local.sh
```

## 更新日志

- 2026-04-02: 从 `C:\Users\jyfa\Desktop\test_qwen_image.py` 整理为 generation skill，统一为本地服务技能结构
