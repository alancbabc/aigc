---
name: qwen-image-2512
description: Qwen-Image-2512 文生图能力。模型原生支持中文，但在仓库标准 workflow 中默认使用英文 prompt。
trigger: 需要使用 Qwen-Image-2512 生成静态图像时调用。
---

# Qwen-Image-2512 文生图模型

## 概述

Qwen-Image-2512 是阿里云 Qwen 系列的文生图模型，支持生成高质量图像。

> ⚠️ **铁则**：在本仓库标准 workflow 中，进入 generation 的 prompt 统一使用英文。Qwen-Image-2512 的中文能力仅作为模型原生能力保留，适用于独立实验场景。

## 输入

- 必填：prompt、`size`
- contract 必填字段：`language_mode`（用于明确当前是 workflow 英文模式还是独立中文实验模式）
- 常见仓库用法：workflow 默认英文 prompt；独立实验场景可显式使用中文 prompt
- 可选执行参数：`model`、`num_inference_steps`、`cfg_scale`、`quality`、输出路径
- 可选上游来源：`art/scene-design/`、`director/storyboard/`、`director/test-shoots/`

## 输出

- 主产物：生成图像文件（如 `output.png` / `output.jpg`）
- 用于下游 review、筛选或继续加工的静态图像结果
- 如果接口响应的 JSON 包含图像数据（通常为 `b64_json`，多图场景可表现为 `data[i].b64_json`），必须先逐张解码为用户可直接查看的 `png` / `jpg` 文件
- done condition：成功返回并保存至少一张符合 prompt 意图的图像

## 依赖

### Knowledge Dependencies

通常作为 workflow 中的静态图像生成执行器使用，默认接收英文 prompt。

可选扫描：
- `_knowledge/Genre/`：题材词汇补全
- `_knowledge/FamousDirectors/`：风格参考
- `_prompts/PromptTemplates/Style/`：风格 token

使用原则：
1. 在仓库标准 workflow 中，优先执行上游给定的英文 prompt。
2. 只在独立实验或明确脱离 workflow 时，才考虑使用中文 prompt。
3. 不主动承担镜头设计和叙事设计。

### 工具与外部依赖

- API：`https://ai.gitee.com/v1/images/generations`
- 环境变量：`AIGC_GITEE_API_KEY`
- 可选环境变量：`AIGC_GITEE_BASE_URL`
- 调用方式：cURL

## 规则

- 在仓库标准 workflow 中默认使用英文 prompt
- 仅在独立实验或用户明确要求时使用中文 prompt
- 优先执行上游已经确认的 prompt，不主动承担镜头设计和叙事设计
- 批量生成时必须串行发送请求，并在请求之间等待 3-5 秒

### API 端点

```
https://ai.gitee.com/v1/images/generations
```

### 配置

- 环境变量：`AIGC_GITEE_API_KEY`
- 可选环境变量：`AIGC_GITEE_BASE_URL`

### 可用尺寸

- 1024x1024
- 1024x576 (横屏)
- 768x1024 (竖屏)

## 工作流程

1. 接收 prompt、尺寸和可选模型参数
2. 判断当前任务是否属于仓库标准 workflow 还是独立实验场景，并设置对应的 `language_mode`
3. 使用 cURL 调用 Gitee 文生图接口生成图像
4. 如果响应的 JSON 包含图像数据（通常为 `b64_json`，多图场景可表现为 `data[i].b64_json`），先逐张解码为 `png` / `jpg` 文件
5. 保存输出图像并交给下游 review / 筛选

## 示例

```text
输入：来自 storyboard 的英文 prompt + 1024x1024
处理：调用 Qwen-Image-2512 接口生成静态图像
输出：供后续筛选的图像文件
```

### 使用方法

### cURL（唯一保留调用方式）

```bash
curl -s https://ai.gitee.com/v1/images/generations \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AIGC_GITEE_API_KEY" \
  -d '{
    "prompt": "a cute kitten sitting on the grass",
    "model": "Qwen-Image-2512",
    "size": "1024x1024",
    "num_inference_steps": 4,
    "cfg_scale": 1
  }' --max-time 60
```

返回结果中会包含生成图像数据；如需保存产物，可按运行环境自行处理响应内容。

结果处理：
- 如果返回 JSON 中包含图像数据（通常为 `b64_json`，多图场景可表现为 `data[i].b64_json`），需要先逐张做 base64 解码，再保存为 `png` 或 `jpg`
- 只有解码后的图片文件才应直接交给用户查看或用于下游 review

## 参数说明

| 参数 | 说明 | 默认值 | 用户必须提供 |
|------|------|--------|--------------|
| prompt | 提示词（workflow 默认英文） | - | ✅ 是 |
| size | 输出尺寸 | 1024x1024 | ✅ 是 |
| language_mode | `workflow_english` 或 `standalone_chinese_experiment` | workflow_english | ✅ 是（contract 中） |
| model | 模型名称 | Qwen-Image-2512 | ❌ 否 |
| num_inference_steps | 推理步数 | 4 | ❌ 否 |
| cfg_scale | CFG 引导强度 | 1 | ❌ 否 |
| quality | 质量 | standard | ❌ 否 |

**直接调用 API 时，用户至少需要提供 prompt 和 size；在标准化 contract 中，还需要显式记录 `language_mode`。**

## 契约与产物

- 主产物：图像文件（如 `output.png`、`output.jpg`）
- 如果接口响应的 JSON 包含图像数据（通常为 `b64_json`，多图场景可表现为 `data[i].b64_json`），解码后的 `png` / `jpg` 文件才是最终交付产物
- 示例：`qwen-image-2512.example.json`
- Schema：`qwen-image-2512.schema.json`
- 该 contract 描述 prompt、模型参数、响应解码要求和最终交付文件路径，不直接内嵌二进制图像内容

## 速率限制

- **Gitee API 短时间内不能发送大量请求**
- **必须一个个发送**，每个请求之间等待几秒
- 建议：每个请求后等待 **3-5秒** 再发下一个

## 目录结构

```
qwen-image-2512/
├── qwen-image-2512.example.json
├── qwen-image-2512.schema.json
├── config.py              # API 配置
└── SKILL.md               # 说明文档
```

## 更新日志

- 2026-03-12: 初始创建
- 2026-03-25: 对齐仓库统一模板，补齐输入/输出/依赖/规则/工作流程/契约与产物/示例骨架
