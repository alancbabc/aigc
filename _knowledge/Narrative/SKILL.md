---
name: Narrative
description: 通用叙事知识库。为故事大纲、剧本编写和分镜设计提供 AI 友好的结构规则、场景模式和节奏决策启发。
trigger: 需要选择故事结构、场景推进方式、信息揭示策略或节奏控制方案时调用
---

# Narrative 叙事知识库

## 适用对象

- `writer/story-outline`
- `writer/script-writing`
- `director/storyboard`
- `director/transition`

## 适用场景

- 选择整体故事结构
- 设计 scene-level 推进方式
- 控制信息揭示与反转节奏
- 判断某个 scene 的叙事功能
- 检查故事是否“平”“散”“没有推进”

## 影响字段

- `outline.json -> structure`
- `outline.json -> narrative_focus`
- `outline.json -> scenes[].function`
- `script.json -> scenes[].event`
- `script.json -> scenes[].duration`
- `storyboard.json -> scenes[].narrative_type`
- `storyboard.json -> scenes[].summary`

## Use This Knowledge For

Narrative 不直接替你写剧情，它负责回答这些问题：

- 这个故事应该用什么结构推进？
- 这一场戏为什么存在？
- 当前 scene 应该是冲突场、转折场、说明场还是压缩场？
- 什么时候该提早抛出信息，什么时候该延迟揭示？
- 为什么当前版本会显得平？

## Core Rules

1. 每个故事必须有明确的推进引擎，而不只是事件堆叠。
2. 每个重要 scene 必须有功能：推进冲突、揭示信息、改变关系、抬升风险、准备反转。
3. 如果一个 scene 结束后世界状态没有变化，它大概率是弱 scene。
4. 解释不能长期替代冲突，说明性 scene 必须尽量短。
5. 反转必须改变观众理解，而不只是补一条信息。
6. 节奏变慢时，优先检查目标、障碍、风险和结果，而不是先加对白。

## Decision Heuristics

### 什么时候选 Story-Level 结构

优先使用 `Story-Level` 手法，当你需要：
- 组织完整故事走向
- 规划中点、低谷、高潮
- 控制较长时长内容
- 为 outline 定义清晰的大段推进

默认优先：
- `three-act-structure`

可选扩展：
- `heros-journey`

### 什么时候选 Scene-Level 手法

优先使用 `Scene-Level` 手法，当你需要：
- 写单场戏
- 判断一个 scene 该怎么推进
- 选择 flashback、montage、summary-scene 等表达方式

默认优先：
- `standard-scene`

可选扩展：
- `summary-scene`
- `transition-scene`
- `flashback`
- `flash-forward`
- `montage-structure`
- `progress-montage`
- `routine-loop`
- `season-transition`

## Pattern Library

### Story-Level Patterns

| Pattern | Use When | Output Impact | Avoid When |
|--------|----------|---------------|------------|
| `three-act-structure` | 需要稳定完整的起承转合 | `outline.structure`, `key_events`, `payoff order` | 极短片段、纯概念广告 |
| `heros-journey` | 主角有明显成长或试炼过程 | `character arc`, `trial sequence`, `return change` | 群像叙事、单事件短片 |

### Scene-Level Patterns

| Pattern | Use When | Output Impact | Avoid When |
|--------|----------|---------------|------------|
| `standard-scene` | 需要明确目标-障碍-结果 | `scene.event`, `duration`, `narrative_type` | 只想快速概括时间流逝 |
| `summary-scene` | 需要压缩时间或重复行为 | `event compression`, `shortened scene count` | 关键冲突必须现场发生 |
| `transition-scene` | 需要平稳换场或关系过渡 | `scene bridge`, `lower narrative weight` | 应该直接进入冲突时 |
| `flashback` | 过去信息能重新解释当下 | `reveal strategy`, `emotion shift` | 只是补背景资料时 |
| `flash-forward` | 需要制造预期或命运感 | `future hint`, `suspense setup` | 会削弱当前情节紧张感时 |
| `montage-structure` | 需要快速累积变化或训练过程 | `compressed progression` | 关键关系冲突需要对打时 |
| `progress-montage` | 需要展示成长、准备、升级 | `visible progress beats` | 过程本身缺少变化时 |
| `routine-loop` | 需要用重复建立状态后再打破 | `pattern break payoff` | 节奏已经偏慢时 |
| `season-transition` | 需要强时间流逝感 | `time shift`, `visual bridge` | 场景本身应保留现场张力时 |

## Narrative Extraction Targets

当 writer skill 调用本知识库时，至少应该先提炼这些中间决策：

- `structure_pattern`
- `scene_engine`
- `reveal_strategy`
- `rhythm_goal`
- `payoff_pattern`

推荐中间结果示例：

```json
{
  "structure_pattern": "three-act-structure",
  "scene_engine": "standard-scene",
  "reveal_strategy": "delay key identity until midpoint",
  "rhythm_goal": "steady escalation with a visible midpoint shift",
  "payoff_pattern": "plant early emotional promise, pay it off in the final confrontation"
}
```

## Anti-Patterns

- 只有设定，没有推进
- scene 只在重复上一场的信息
- 冲突很弱，但解释很多
- 反转没有改变关系或风险
- 所有场景都用同一种推进方式
- 为了“有内容”硬加无功能 scene

## How To Diagnose A Flat Story

如果故事发平，优先检查：

1. 主角当前想要什么，是否足够明确？
2. 当前障碍是否真实存在，而不是口头存在？
3. 每一场戏的结果是否改变了局面？
4. 信息揭示是否太早、太散、太平均？
5. 中点或关键转折是否真正抬高了风险？

## Files To Read

优先阅读这些文件：

- `three-act-structure.md`
- `heros-journey.md`
- `standard-scene.md`
- `summary-scene.md`
- `transition-scene.md`
- `flashback.md`
- `flash-forward.md`
- `montage-structure.md`
- `progress-montage.md`
- `routine-loop.md`
- `season-transition.md`

机器友好索引：
- `narrative-patterns.json`

## Usage Rule

1. 先选结构，再写事件。
2. 先定义场景功能，再写对白。
3. 先提炼决策字段，再产出 outline / script / storyboard。
4. 不直接照抄知识文件原文，而是把规则转成当前项目的结构化决策。
