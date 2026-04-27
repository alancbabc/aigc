# Prompt Map

`_prompts` 是共享提示词资产层，负责提供可以直接拼接到 prompt 中的模板、短语和模型适配写法。

## 与 `_knowledge` 的分工

- `_knowledge/`：解释概念、适用场景、专业规则
- `_prompts/`：提供可直接使用的 prompt 写法和模板组合

## 目录分层

- `PromptTemplates/`: 通用 prompt 模板和可复用短语
- `ModelGuides/`: 面向具体模型的提示词优化指南

## 当前推荐入口

### 风格类

- `_prompts/PromptTemplates/Style/`

### 镜头语言类

- `_prompts/PromptTemplates/Camera/`

### 视频模型类

- `_prompts/ModelGuides/LTX-Video/`

## 新增模型指南的放置规则

如果以后新增特定模型的 prompt 优化指南，统一放在：

```text
_prompts/ModelGuides/<Model-Name>/
```

例如：
- `_prompts/ModelGuides/LTX-Video/`
- `_prompts/ModelGuides/Runway-Gen/`
- `_prompts/ModelGuides/Kling/`
- `_prompts/ModelGuides/Pika/`

## 使用原则

1. 先去 `_knowledge` 选概念，再来 `_prompts` 取写法。
2. `_prompts` 只提供模型友好的表达，不负责定义专业概念。
3. 同一个概念若有多个写法，优先选择更稳定、歧义更小的短语。
