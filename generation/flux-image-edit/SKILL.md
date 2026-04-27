---
name: flux-image-edit
description: FLUX.2-klein-9B 图生图能力，支持 1 到 3 张参考图用于关键帧与角色一致性生成。
trigger: 需要基于参考图进行图生图或关键帧生成时调用。
---

# FLUX Image Edit 模型使用说明

## 概述

FLUX.2-klein-9B 是 Gitee AI 的图生图（Image-to-Image）模型，用于生成关键帧图像。

> ⚠️ **铁则**：所有 prompt 必须使用**纯英文**，禁止任何中文

## 输入

- 必填：英文 prompt、1-3 张参考图、输出尺寸
- 可选执行参数：`task_types`、`model`、`num_inference_steps`、`guidance_scale`
- 可选上游来源：`art/character-three-view/`、`art/keyframe-generation/`、`director/storyboard/`、`director/test-shoots/`

## 输出

- 主产物：编辑后或生成后的图像文件
- 用于关键帧生成、角色一致性保持和图像迭代的静态图像结果
- 如果接口响应的 JSON 包含图像数据（通常为 `b64_json`，多图场景可表现为 `data[i].b64_json`），必须先逐张解码为用户可直接查看的 `png` / `jpg` 文件
- done condition：成功基于参考图生成至少一张符合 prompt 与一致性约束的图像

## 依赖

### Knowledge Dependencies

通常不主动规划镜头或角色，只负责根据参考图和 prompt 做一致性编辑。

可选扫描：
- `_prompts/PromptTemplates/Style/`：统一风格 token
- `_knowledge/Actor/`：理解角色姿态词
- `_knowledge/VisualEnvironment/`：理解环境词汇

使用原则：
1. 角色身份、一致性和场景信息优先来自参考图。
2. 知识库只用于理解 prompt 中的专业词，不替代上游场景和角色设计。
3. 多图时必须以 `from image 1/2/3` 为最高优先级约束。

### 工具与外部依赖

- API：`https://ai.gitee.com/v1/images/edits`
- 环境变量：`AIGC_GITEE_API_KEY`
- 可选环境变量：`AIGC_GITEE_BASE_URL`
- 调用方式：cURL

## 规则

- 所有 prompt 必须使用纯英文
- 多图时 prompt 中必须使用 `from image 1/2/3` 明确指定每张图的用途
- 角色身份、风格和场景信息优先来自参考图，不擅自改写上游设计
- 批量请求必须串行发送，并在请求之间等待 3-5 秒

### API 端点

```
https://ai.gitee.com/v1/images/edits
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

1. 接收英文 prompt、参考图和目标尺寸
2. 根据单图或多图场景组织 `task_types` 与 prompt 引用关系
3. 通过 cURL multipart 表单调用 Gitee 图生图接口生成结果
4. 如果响应的 JSON 包含图像数据（通常为 `b64_json`，多图场景可表现为 `data[i].b64_json`），先逐张解码为 `png` / `jpg` 文件
5. 保存输出图像并交给下游关键帧 review 或一致性检查

## 示例

```text
输入：2 张角色参考图 + 英文 prompt + 1024x576
处理：按 `from image 1/2` 规则调用图生图接口
输出：保留角色一致性的关键帧图像
```

### 使用方法

### cURL（唯一保留调用方式）

```bash
curl -s https://ai.gitee.com/v1/images/edits \
  -X POST \
  -H "Authorization: Bearer $AIGC_GITEE_API_KEY" \
  -F "prompt=Your English prompt" \
  -F "image=@/path/to/image.png" \
  -F "task_types=id" \
  -F "task_types=style" \
  -F "model=FLUX.2-klein-9B" \
  -F "size=1024x576" \
  -F "num_inference_steps=4" \
  -F "guidance_scale=1"
```

返回结果中会包含生成图像数据；如需保存产物，可按运行环境自行处理响应内容。

结果处理：
- 如果返回 JSON 中包含图像数据（通常为 `b64_json`，多图场景可表现为 `data[i].b64_json`），需要先逐张做 base64 解码，再保存为 `png` 或 `jpg`
- 只有解码后的图片文件才应直接交给用户查看或用于下游关键帧 review

## 参数说明

| 参数 | 说明 | 默认值 | 用户必须提供 |
|------|------|--------|--------------|
| prompt | 英文提示词 | - | ✅ 是 |
| image | 参考图片路径（支持1-3张） | - | ✅ 是 |
| size | 输出尺寸 | 1024x576 | ✅ 是 |
| task_types | 任务类型 | id, style | ❌ 否 |
| model | 模型名称 | FLUX.2-klein-9B | ❌ 否 |
| num_inference_steps | 推理步数 | 4 | ❌ 否 |
| guidance_scale | 引导强度 | 1 | ❌ 否 |

**用户只需提供 prompt、image、size，其他参数使用默认值。**

### 多图参考规则 ⚠️ 重要

- **支持1-3张参考图**
- **Prompt中必须用 `from image 1`, `from image 2`, `from image 3` 明确指定每张图的用途**
- 图片顺序对应 prompt 中的 image 1/2/3

**示例**（3张图）：
```bash
# 参考图顺序：角色1 → 角色2 → 场景
-F "image=@character1.png" \
-F "image=@character2.png" \
-F "image=@scene.png"

# Prompt 必须指出每张图
prompt="The woman from image 1 and the man from image 2 are talking in the room from image 3, ..."
```

### task_types 说明

- `id`: 保持角色身份一致性
- `style`: 匹配风格

**推荐**：同时使用 `id` + `style`

## 重要注意事项

1. **每次只提交一个请求**，不要并发
2. **必须使用纯英文 prompt**
3. **支持多图参考**：在 cURL 中通过多个 `-F "image=@..."` 传入多张图片

### ⚠️ 速率限制

- **Gitee API 短时间内不能发送大量请求**
- **必须一个个发送**，每个请求之间等待几秒
- 建议：每个请求后等待 **3-5秒** 再发下一个

## 契约与产物

- 主产物：图像文件（如 `output.png`、`output-0.jpg`）
- 如果接口响应的 JSON 包含图像数据（通常为 `b64_json`，多图场景可表现为 `data[i].b64_json`），解码后的 `png` / `jpg` 文件才是最终交付产物
- 示例：`flux-image-edit.example.json`
- Schema：`flux-image-edit.schema.json`
- 该 contract 描述参考图输入、任务类型、响应解码要求和最终交付文件路径，不直接内嵌二进制图像内容

## 目录结构

```
flux-image-edit/
├── batch_gen.sh           # 批量生成辅助脚本
├── flux-image-edit.example.json
├── flux-image-edit.schema.json
├── config.py              # API 配置
└── SKILL.md               # 说明文档
```

## 更新日志

- 2026-03-12: 更新为官方代码示例
- 2026-03-25: 对齐仓库统一模板，补齐输入/输出/依赖/规则/工作流程/契约与产物/示例骨架
