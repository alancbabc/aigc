---
name: Genre
description: 通用题材知识库。为故事大纲、角色设计、场景设计和分镜设计提供 AI 友好的题材规则、气质边界和常见模式。
trigger: 需要识别题材、设定题材语气、约束角色行为边界或统一视觉风格时调用
---

# Genre 题材知识库

## 适用对象

- `writer/story-outline`
- `writer/character-profile`
- `writer/script-writing`
- `art/character-three-view`
- `art/scene-design`

## 适用场景

- 匹配项目题材
- 限定故事气质和语气
- 约束角色原型和关系模式
- 提炼视觉风格与世界规则
- 判断“像不像这个类型”

## 影响字段

- `outline.json -> genre`
- `outline.json -> subgenre`
- `outline.json -> visual_style`
- `outline.json -> core_theme`
- `characters.json -> archetype`
- `characters.json -> costume`
- `script.json -> tone`
- `scene_design.json -> style`

## Use This Knowledge For

Genre 不只是给故事贴标签，它主要负责回答：

- 这个项目到底属于什么题材？
- 这个题材默认允许什么样的冲突和人物行为？
- 这个题材通常长什么样、怎么说话、怎么推进？
- 当前剧情和角色是否偏离了题材气质？

## Core Rules

1. 先确定题材，再确定结构和角色原型。
2. 题材不只是美术风格，也约束冲突类型、情绪走向和角色行为边界。
3. 如果一个故事的冲突方式、人物选择和视觉气质都不符合题材，观感就会“不像”。
4. 视觉风格可以混搭，但题材核心规则不能随意漂移。
5. 题材越明确，OpenClaw 越容易稳定地产出不平淡的内容。

## Decision Heuristics

### 什么时候优先从 Genre 决策

优先从 Genre 提炼规则，当你需要：
- 选择故事整体语气
- 选择角色原型
- 判断允许的冲突方式
- 给美术和镜头统一风格

### 题材决定什么

优先由 Genre 决定：
- `tone`
- `world_rules`
- `conflict_defaults`
- `character_archetypes`
- `visual_keywords`
- `setting_defaults`

不要让 Genre 直接替代：
- 具体三幕结构
- 每场戏的 scene engine
- 具体转场方式

## Pattern Library

| Genre | Typical Tone | Conflict Defaults | Character Defaults | Visual Defaults |
|------|---------------|-------------------|--------------------|-----------------|
| `wuxia` | honor, romance, sacrifice, righteousness | sect conflict, revenge, loyalty vs desire | young hero, master, assassin, wandering knight, loyal companion | martial arts mood, classical architecture, rivers and lakes atmosphere |
| `sci-fi` | wonder, control, fear, progress, alienation | human vs system, technology risk, exploration, survival | scientist, pilot, outsider, AI partner, authority figure | futuristic spaces, cold light, interface design, technological scale |
| `urban` | realism, pressure, intimacy, ambition | class pressure, family conflict, work-life tension, relationship fracture | ordinary worker, entrepreneur, struggling youth, parent, lover | city night, apartments, offices, street realism |
| `ancient-romance` | longing, fate, ritual, separation, reunion | family pressure, court order, status barrier, promise vs duty | noble lady, scholar, prince, maid, guard, confidante | classical costume, ritual spaces, elegant courtyards, seasonal atmosphere |
| `fantasy-adventure` | wonder, destiny, trial, discovery | quest, awakening, prophecy, world threat | chosen one, guide, rival, magical companion, guardian | magical landscape, ancient ruins, creature presence, mythic scale |

## Genre Extraction Targets

当调用本知识库时，至少先提炼这些中间决策：

- `genre_label`
- `subgenre`
- `tone`
- `world_rules`
- `conflict_defaults`
- `character_archetypes`
- `visual_keywords`

推荐中间结果示例：

```json
{
  "genre_label": "wuxia",
  "subgenre": "classical revenge wuxia",
  "tone": "tragic, restrained, righteous",
  "world_rules": [
    "jianghu relationships matter more than formal law",
    "martial skill carries social weight"
  ],
  "conflict_defaults": [
    "loyalty vs desire",
    "sect conflict",
    "revenge vs mercy"
  ],
  "character_archetypes": [
    "young hero",
    "wandering swordswoman",
    "fallen master"
  ],
  "visual_keywords": [
    "bamboo forest",
    "inn at dusk",
    "mountain mist",
    "sword glint"
  ]
}
```

## Anti-Patterns

- 题材名义上是 A，实际冲突和人物全是 B
- 角色讲话、穿着、行为脱离题材边界
- 视觉上混得很花，但世界规则没有统一
- 题材只停留在表面道具，没进入冲突核心
- 所有题材都写成一种通用“AI故事味”

## How To Diagnose “Doesn’t Feel Like The Genre”

如果内容“不像这个类型”，优先检查：

1. 核心冲突是不是这个题材常见的冲突？
2. 主角和配角是不是题材内常见原型？
3. 视觉意象有没有稳定重复？
4. 世界规则有没有影响角色选择？
5. 角色行为是否违背题材气质？

## Files To Read

优先阅读这些文件：

- `wuxia.md`
- `sci-fi.md`
- `urban.md`
- `ancient-romance.md`
- `fantasy-adventure.md`

机器友好索引：
- `genre-patterns.json`

## Usage Rule

1. 先定题材，再定结构。
2. 先提炼题材决策字段，再产出 outline / characters / scene design。
3. 不直接照抄题材文件原文，而是把规则转成当前项目的结构化约束。
