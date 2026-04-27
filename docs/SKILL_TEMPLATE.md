---
name: skill-name
description: 一句话说明 skill 的职责、边界和价值。
trigger: 什么时候应该调用这个 skill。
---

# Skill Name

## 作用

- 这个 skill 解决什么问题
- 适用于哪些输入场景
- 不适用于哪些场景

## 输入

- 必填输入
- 可选输入
- 依赖的上游产物
- 需要先确认的关键约束

## 输出

- 主要输出
- 文件产物
- 下游可消费的结构
- 完成标准 / done condition

## 依赖

### 知识依赖

- 依赖的知识库
- 依赖的规则库 / prompt 库

### 工具与外部依赖

- 依赖的脚本、配置、模型、API
- 所需环境变量
- 可选依赖与默认值

## 规则

- 语言约束
- prompt 约束
- 速率限制
- review / 校验要求
- 不能越界处理的内容

## 工作流程

1. 输入如何进入本 skill
2. 如何提取决策 / 组织信息
3. 如何生成或修改目标产物
4. 如何 review / 验收

## 契约与产物

- 主产物：`artifact.json`
- 示例：`artifact.example.json`
- Schema：`artifact.schema.json`
- 校验：`npm run validate:skills`
- 其他目录产物：`outputs/`

如果当前 skill 暂时没有 schema/example，也要明确写出：

- 为什么没有
- 未来准备补到哪里

## 示例

```text
输入 -> 处理 -> 输出
```

## 目录结构（可选）

```text
skill-name/
├── SKILL.md
├── artifact.example.json
├── artifact.schema.json
└── scripts/
```

## 更新日志

- 2026-03-24: 升级为仓库统一标准模板，明确输入/输出/依赖/规则/契约骨架
