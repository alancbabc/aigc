---
name: flux-text-to-image
description: FLUX.2-klein-9B 文生图能力，适合英文 prompt 的静态图像生成。
trigger: 需要使用英文 prompt 生成静态图像时调用。
---

# FLUX Text-to-Image 文生图模型

## 概述

FLUX.2-klein-9B 文生图模型，英文 prompt 效果更好。

> ⚠️ **铁则**：所有 prompt 必须使用**纯英文**，禁止任何中文

## 输入

- 必填：英文 prompt
- 常用执行参数：`size`、输出路径
- 可选执行参数：`model`、`num_inference_steps`、`guidance_scale`
- 可选上游来源：`art/character-three-view/`、`art/scene-design/`、`director/storyboard/`、`director/test-shoots/`

## 输出

- 主产物：生成图像文件（如 `output.png` / `output.jpg`）
- 用于下游 review、筛选或继续加工的静态图像结果
- 如果接口响应的 JSON 包含图像数据（通常为 `b64_json`，多图场景可表现为 `data[i].b64_json`），必须先逐张解码为用户可直接查看的 `png` / `jpg` 文件
- done condition：成功返回并保存至少一张符合 prompt 意图的图像

## 依赖

### Knowledge Dependencies

通常不主动决定创作规则，主要执行上游传入的英文 prompt。

可选扫描：
- `_prompts/PromptTemplates/Style/`：补充风格 token
- `_knowledge/FamousDirectors/`：用户指定导演风格但 prompt 未充分展开时
- `_knowledge/VisualEnvironment/`：补全环境术语理解

使用原则：
1. 不替代 Writer / Art / Director 的创作判断。
2. 只在 prompt 缺少必要风格词时做轻量补全。
3. 输出质量优先依赖 prompt 完整度和尺寸选择。

### 工具与外部依赖

- API：`https://ai.gitee.com/v1/images/generations`
- 环境变量：`AIGC_GITEE_API_KEY`
- 可选环境变量：`AIGC_GITEE_BASE_URL`
- 调用方式：cURL

## 规则

- 所有 prompt 必须使用纯英文
- 优先执行上游已确认的 prompt，不擅自重写创作意图
- 批量生成时必须串行发送请求，并在请求之间等待 3-5 秒
- 尺寸选择以用户需求为准，未指定时使用文档中的推荐默认值

### API 端点

```
https://ai.gitee.com/v1/images/generations
```

### 配置

- 环境变量：`AIGC_GITEE_API_KEY`
- 可选环境变量：`AIGC_GITEE_BASE_URL`

### 尺寸

⚠️ **尺寸无限制，以用户需求为准**

常见尺寸：
- 1920x1080 (16:9 HD)
- 2048x1152 (2K)
- 1024x1024 (1:1 正方)
- 1024x576 (横屏)
- 768x1024 (竖屏)

## 工作流程

1. 接收上游整理好的英文 prompt 与可选尺寸参数
2. 根据目标画幅与质量要求选择执行参数
3. 使用 cURL 调用 Gitee 图像生成接口生成图像
4. 如果响应的 JSON 包含图像数据（通常为 `b64_json`，多图场景可表现为 `data[i].b64_json`），先逐张解码为 `png` / `jpg` 文件
5. 保存输出图像并交给下游 review / 筛选

## 示例

```text
输入：来自 storyboard 的英文 prompt + 768x1024
处理：调用 FLUX.2-klein-9B 文生图接口生成图像
输出：可继续 review 的静态图像文件
```

### 使用方法

### cURL（唯一保留调用方式）

```bash
curl -s https://ai.gitee.com/v1/images/generations \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AIGC_GITEE_API_KEY" \
  -d '{
    "prompt": "Ghibli style, hand-drawn 2D, a young boy, white t-shirt, full body, front view, pure white background",
    "model": "FLUX.2-klein-9B",
    "size": "768x1024",
    "num_inference_steps": 4,
    "guidance_scale": 1
  }' --max-time 120
```

参数：
- `prompt`: 提示词（英文）
- `model`: 模型名称（默认 `FLUX.2-klein-9B`）
- `size`: 图片尺寸（默认可按场景指定）
- `num_inference_steps`: 推理步数（默认 4）
- `guidance_scale`: Guidance scale（默认 1）

结果处理：
- 如果返回 JSON 中包含图像数据（通常为 `b64_json`，多图场景可表现为 `data[i].b64_json`），需要先逐张做 base64 解码，再保存为 `png` 或 `jpg`
- 只有解码后的图片文件才应直接交给用户查看或用于下游 review
- 不应将原始 JSON 响应直接当作 `output.png` 交付

## 契约与产物

- 主产物：图像文件（如 `output.png`、`output-0.jpg`）
- 如果接口响应的 JSON 包含图像数据（通常为 `b64_json`，多图场景可表现为 `data[i].b64_json`），解码后的 `png` / `jpg` 文件才是最终交付产物
- 示例：`flux-text-to-image.example.json`
- Schema：`flux-text-to-image.schema.json`
- 该 contract 描述请求参数、响应解码要求和最终交付文件路径，不直接内嵌二进制图像内容

## 速率限制

⚠️ Gitee API 有速率限制：
- 必须逐个生成
- 每个请求后等待 **3-5 秒**
- 建议生成后等待，避免 429 错误

## 目录结构（可选）

```text
flux-text-to-image/
├── flux-text-to-image.example.json
├── flux-text-to-image.schema.json
├── config.py              # API 配置
└── SKILL.md               # 说明文档
```

## 更新日志

- 2026-03-25: 对齐仓库统一模板，补齐输入/输出/依赖/规则/工作流程/契约与产物/示例骨架
