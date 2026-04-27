---
name: mineru25-ocr
description: Gitee AI MinerU2.5 文档 OCR / 解析能力，支持 PDF 与图片输入转 Markdown，并可开启表格、公式和版面解析。
trigger: 需要把 PDF 或图片做 OCR、版面解析或转成 Markdown 时调用。
---

# Gitee AI MinerU2.5 文档 OCR / 解析

## 概述

MinerU2.5 是 Gitee AI 提供的异步文档解析模型，适合把 PDF、PNG、JPG 等本地文件上传到接口后进行 OCR、版面分析、表格 / 公式解析，并输出 Markdown。

> ⚠️ **用途**：论文、报告、扫描文档、课件、截图、拍照图片等材料的 OCR 提取与结构化 Markdown 产出

## 输入

- 必填：本地文件路径（支持 `pdf`、`png`、`jpg`、`jpeg` 等文档或图片输入）
- 必填：模型名（默认 `MinerU2.5`）
- 必填：是否启用 OCR（默认 `true`）
- 可选：是否返回图像 base64、是否开启公式解析、是否开启表格解析
- 可选：版面模型（默认 `doclayout_yolo`）
- 可选：输出格式（当前默认 `md`）
- 可选上游来源：`writer/`、`academic-deep-research` 产物、外部 PDF / 讲义 / 资料包、截图与拍照图片

## 输出

- 主产物：Markdown 文件（推荐作为标准交付物）
- 可选伴随产物：原始任务状态 JSON、图像抽取结果、附带的图片资源
- 用于下游摘要、PPT、知识提取、资料整理的结构化文档文本
- done condition：成功获得完整 Markdown 结果，且可直接被后续 skill 或人工阅读

## 依赖

### Knowledge Dependencies

该 skill 属于执行层，负责把文档解析成结构化文本，不主动重写原文结论。

可选扫描：
- `academic-deep-research`：当 OCR 结果要继续进入研究整理流程时
- `source-to-ppt`：当 OCR 结果要继续转成演示文稿时
- `minimax-pdf`：当需要把解析后的内容重新排版为高质量 PDF 时

使用原则：
1. 优先保留原文结构，不擅自润色或改写术语。
2. 扫描版 PDF、图片型 PDF、拍照图片默认开启 OCR。
3. 表格、公式、版面信息是提取质量增强项，不替代人工校对。

### 工具与外部依赖

- API：`https://ai.gitee.com/v1/async/documents/parse`
- 环境变量：`AIGC_GITEE_API_KEY`
- 可选环境变量：`AIGC_GITEE_BASE_URL`
- 可选环境变量：`AIGC_GITEE_TASK_BASE_URL`
- 调用方式：cURL multipart 表单，异步任务，需轮询状态

## 规则

- 每次只提交一个文档解析请求，不并发轰炸接口
- 文档输入必须是本地可读文件路径
- 默认输出 Markdown，不把原始响应 JSON 直接当作最终交付物
- 如果接口返回的是下载 URL，必须先下载并保存为本地文件再交付
- 如果接口只返回任务状态而未直接给出 Markdown 文件，需要保留状态 JSON 供人工排查

### API 端点

```
提交：https://ai.gitee.com/v1/async/documents/parse
状态：https://ai.gitee.com/api/v1/task/{task_id}
```

> 注：提交端点来自用户提供的官方调用示例；状态查询沿用 Gitee 其他异步任务接口的一致模式，脚本中做了宽松兼容处理。

### 配置

- 环境变量：`AIGC_GITEE_API_KEY`
- 可选环境变量：`AIGC_GITEE_BASE_URL`
- 可选环境变量：`AIGC_GITEE_TASK_BASE_URL`

## 工作流程

1. 接收本地 PDF 或图片路径与可选解析参数
2. 读取环境变量中的 Gitee API token
3. 通过 multipart 表单向异步文档解析接口提交任务
4. 提取 `task_id` 并轮询任务状态
5. 在任务完成后优先查找 Markdown 结果下载地址；若无下载地址，则尝试从响应中提取 Markdown 文本
6. 将 Markdown 保存为本地文件，并保留一份原始状态 JSON 便于排查

## 示例

```text
输入：一份本地 PDF 或图片 + 开启 OCR / 表格 / 公式解析
处理：调用 MinerU2.5 异步文档解析接口提交任务并轮询状态
输出：可直接阅读或继续加工的 Markdown 文件
```

### cURL（原始调用示例）

```bash
curl https://ai.gitee.com/v1/async/documents/parse \
  -X POST \
  -H "Authorization: Bearer $AIGC_GITEE_API_KEY" \
  -F "file=@path/to/file.pdf" \
  -F "model=MinerU2.5" \
  -F "is_ocr=true" \
  -F "include_image_base64=true" \
  -F "formula_enable=true" \
  -F "table_enable=true" \
  -F "layout_model=doclayout_yolo" \
  -F "output_format=md"
```

### 脚本调用

```bash
bash scripts/parse_document.sh \
  -f ./document.pdf \
  -o outputs/mineru25-ocr/document.md

# 图片输入同样支持
bash scripts/parse_document.sh \
  -f ./page-photo.png \
  -o outputs/mineru25-ocr/page-photo.md
```

## 参数说明

| 参数 | 说明 | 默认值 | 用户必须提供 |
|------|------|--------|--------------|
| file_path | 待解析文件路径（PDF 或图片） | - | ✅ 是 |
| model | 模型名称 | MinerU2.5 | ❌ 否 |
| is_ocr | 是否启用 OCR | true | ❌ 否 |
| include_image_base64 | 是否返回图片 base64 | true | ❌ 否 |
| formula_enable | 是否启用公式解析 | true | ❌ 否 |
| table_enable | 是否启用表格解析 | true | ❌ 否 |
| layout_model | 版面模型 | doclayout_yolo | ❌ 否 |
| output_format | 输出格式 | md | ❌ 否 |

## 契约与产物

- 主产物：Markdown 文件（如 `outputs/mineru25-ocr/document.md`）
- 辅助产物：任务状态 JSON（如 `outputs/mineru25-ocr/document.status.json`）
- 示例：`mineru25-ocr.example.json`
- Schema：`mineru25-ocr.schema.json`
- 该 contract 描述输入文件（PDF 或图片）、异步任务处理方式和最终 Markdown 交付路径，不直接把远端临时 URL 作为最终产物

## 速率限制

⚠️ **Gitee API 短时间内不能发送大量请求**
- 必须一个个发送
- 每个请求后等待 3-5 秒
- 状态轮询间隔建议 5 秒

## 目录结构

```text
mineru25-ocr/
├── mineru25-ocr.example.json
├── mineru25-ocr.schema.json
├── config.py
├── SKILL.md
└── scripts/
    └── parse_document.sh
```

## 更新日志

- 2026-03-31: 初始创建，新增 Gitee AI MinerU2.5 文档 OCR / 解析技能
