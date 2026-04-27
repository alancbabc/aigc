---
name: Actor
description: 通用角色知识库。为角色设计、站位关系、姿态语言和表演线索提供 AI 友好的角色决策规则。
trigger: 需要设计角色原型、关系表达、姿态语言或镜头中的人物呈现方式时调用
---

# Actor 角色知识库

## 适用对象

- `writer/character-profile`
- `director/storyboard`
- `director/test-shoots`
- `art/character-three-view`
- `art/keyframe-generation`

## 适用场景

- 提炼角色原型与行为气质
- 设计角色关系和关系信号
- 设计人物站位、姿态和情绪外显方式
- 给角色外观和镜头表现提供稳定锚点

## 影响字段

- `characters.json -> character_type`
- `characters.json -> personality`
- `characters.json -> relationships`
- `characters.json -> states[].description`
- `storyboard.json -> scenes[].shots[].composition`
- `storyboard.json -> scenes[].shots[].characters[]`
- `test-shoots.json -> shot_prompt`
- `test-shoots.json -> frames[].prompt`

## Use This Knowledge For

Actor 不只是“怎么站、怎么演”，它主要负责回答：

- 这个角色是什么原型？
- 这个角色在关系里占什么位置？
- 这个角色平时怎么出现、怎么表达情绪？
- 观众应该如何一眼识别这个角色？
- 镜头里怎样放置人物才符合关系和权力结构？

## Core Rules

1. 每个主要角色都应该有清晰原型，但不能只剩标签。
2. 每个主要角色至少要有一个稳定外显锚点：
   - 习惯动作
   - 典型站姿
   - 说话方式
   - 配饰或服装信号
3. 关系不能只写“朋友/敌人”，必须能被动作、距离、站位或视线表达出来。
4. 情绪表达要符合角色性格，不是所有角色都用同一种外放方式。
5. 角色设计应优先服务故事功能，再服务美术装饰。

## Decision Heuristics

### 什么时候优先从 Actor 决策

优先从 Actor 提炼规则，当你需要：
- 设计主角、配角、反派的区分方式
- 决定角色如何外显性格
- 决定关系如何在镜头中表现
- 决定角色在提示词里哪些要素必须稳定保留

### Actor 决定什么

优先由 Actor 决定：
- `role_archetype`
- `relationship_signal`
- `body_language`
- `emotion_expression_mode`
- `costume_anchor`
- `habit_action`

不要让 Actor 直接替代：
- 题材语气
- 故事整体结构
- 镜头技术规则

## Pattern Library

### Role Archetypes

| Archetype | Use When | Typical Signals | Output Impact |
|----------|----------|-----------------|---------------|
| `lead-hero` | 需要观众长期跟随的主角 | 识别度高、目标明确、镜头占比稳定 | `character_type`, `goal`, `states[].description` |
| `support-ally` | 需要陪衬、辅助、对照主角 | 靠近主角、关系明确、反应丰富 | `relationships`, `composition`, `group staging` |
| `rival` | 需要竞争、映照或持续张力 | 对视、对峙、镜像动作、距离变化 | `relationships`, `body_language`, `composition` |
| `antagonist` | 需要压力源和冲突发动机 | 控制感、压迫感、识别性动作 | `character_type`, `emotion_expression_mode`, `staging` |
| `mentor` | 需要知识、秩序或传承 | 稳定、克制、中心性或高位感 | `body_language`, `relationship_signal` |
| `wild-card` | 需要制造不确定性 | 不规则行为、难预测、风格强 | `habit_action`, `mood shift`, `scene tension` |

### Relationship Signals

| Relationship | Typical Distance / Staging | Signal |
|-------------|----------------------------|--------|
| trust | side-by-side, low defensive posture | cooperation, emotional safety |
| conflict | face-off, visible distance, blocking tension | confrontation, unresolved friction |
| protection | one character slightly forward or shielding another | hierarchy, care, danger |
| dependence | follow-position, visual reliance | imbalance, emotional attachment |
| alienation | physical gap, avoided eye contact, offset composition | emotional distance |
| power imbalance | one centered/high, one offset/lower | authority vs weakness |

### Emotion Expression Modes

| Mode | Use When | External Signal |
|------|----------|-----------------|
| restrained | 内敛角色、压抑情绪 | small gestures, held posture, minimal face change |
| direct | 外向角色、关系正面冲突 | open gestures, direct gaze, body lean |
| defensive | 脆弱、怀疑、防备 | folded arms, turned body, lowered head |
| aggressive | 进攻、威胁、压迫 | forward lean, invasion of space, strong eye line |
| dissociated | 麻木、受创、空心感 | low response, slow movement, detached gaze |

## Actor Extraction Targets

当调用本知识库时，至少先提炼这些中间决策：

- `role_archetype`
- `relationship_signal`
- `body_language`
- `emotion_expression_mode`
- `costume_anchor`
- `habit_action`

推荐中间结果示例：

```json
{
  "role_archetype": "lead-hero",
  "relationship_signal": "protective but emotionally distant",
  "body_language": "upright posture, restrained movement, controlled gaze",
  "emotion_expression_mode": "restrained",
  "costume_anchor": "dark long coat with a worn shoulder strap",
  "habit_action": "touches the pendant before making a difficult decision"
}
```

## Anti-Patterns

- 角色只有设定词，没有外显行为
- 所有人物情绪表达方式都一样
- 关系只写在文案里，镜头里看不出来
- 角色外观和行为没有稳定锚点
- 配角只是功能说明，没有可识别性

## How To Diagnose Weak Characters

如果角色立不住，优先检查：

1. 是否有可识别原型？
2. 是否有稳定外显锚点？
3. 是否有清楚的关系表达方式？
4. 情绪表达是否符合角色性格？
5. 镜头里能不能一眼看出谁重要、谁在压制谁、谁在依赖谁？

## Files To Read

优先阅读：
- `actor-patterns.json`

当前 `Actor` 总入口已经汇总了大部分通用规则，后续如需细分，可继续拆成：
- `archetypes.md`
- `relationship-signals.md`
- `body-language.md`

机器友好索引：
- `actor-patterns.json`

## Usage Rule

1. 先定角色功能，再定角色原型。
2. 先提炼角色决策字段，再生成档案、三视图和分镜站位。
3. 不直接照抄知识原文，而是把规则转成当前角色的外显设计与关系表达。
