---
name: Camera Prompt Phrases
description: 镜头语言的 prompt 可用词表和组合模板。用于把 Camera 知识库里的专业概念转换成模型更容易理解的写法。
trigger: 需要把景别、视角、运镜、构图写进 prompt 时调用。
---

# Camera Prompt Phrases

> ⚠️ 推荐优先从 `_knowledge/Camera/` 选择概念，再到这里取 prompt 写法。

## 景别 Shot Type

| 概念 | 推荐写法 | 备注 |
|------|----------|------|
| 远景 | `wide shot`, `wide establishing shot` | 建立环境时优先 |
| 全景 | `full shot`, `wide shot` | 含人物全身与环境 |
| 中景 | `medium shot` | 对话和常规动作稳定 |
| 近景 | `close-up` | 情绪和反应 |
| 特写 | `extreme close-up` | 细节或情绪顶点 |
| 过肩镜头 | `over-the-shoulder shot` | 对话关系常用 |

## 视角 Camera Angle

| 概念 | 推荐写法 | 慎用写法 |
|------|----------|----------|
| 平视 | `eye-level view`, `eye-level shot` | |
| 俯视 | `high-angle shot`, `camera looking down` | `top view` |
| 仰视 | `low-angle shot`, `camera looking up` | |
| 鸟瞰 | `bird's-eye view`, `overhead view` | |
| 倾斜 | `dutch angle` | |
| 第一人称 | `point-of-view shot`, `POV shot` | |

## 运镜 Camera Movement

| 概念 | 推荐写法 | 备注 |
|------|----------|------|
| 固定 | `static shot`, `locked camera` | 最稳 |
| 推 | `slow dolly in`, `camera pushes in` | 情绪聚焦 |
| 拉 | `dolly out`, `camera pulls back` | 揭示环境 |
| 横摇 | `pan left`, `pan right`, `slow pan` | |
| 纵移 | `tilt up`, `tilt down` | |
| 跟随 | `tracking shot`, `camera follows the subject` | |
| 环绕 | `camera circles around the subject`, `orbit shot` | |
| 手持 | `handheld camera`, `subtle handheld movement` | 不要过强晃动 |
| 升降 | `crane shot`, `camera rises up`, `camera descends` | |

## 构图 Composition

| 概念 | 推荐写法 |
|------|----------|
| 三分法 | `rule of thirds composition` |
| 居中 | `centered composition` |
| 对称 | `symmetrical composition` |
| 引导线 | `leading lines` |
| 留白 | `negative space composition` |
| 前景构图 | `foreground framing` |

## 常见组合模板

### Storyboard / test-shoots

```text
[shot_type], [camera_angle], [camera_movement], [composition], [subject], [environment], [lighting], [mood]
```

### Scene design

```text
[shot_type], [camera_angle], [composition], empty scene, no people, [environment], [lighting], [mood]
```

### Keyframe generation

```text
[style], [shot_type], [camera_angle], [subject appearance], [action], [environment], [lighting], [mood]
```

## 使用建议

1. 每个 prompt 最多保留 1 个景别、1 个主视角、1 个主运镜，避免冲突。
2. 高角度和鸟瞰不要混用，除非明确需要从高处俯拍。
3. 手持、环绕、推拉等动态词最好配合动作场景使用。
4. 如果模型经常误解，用更具体的短语替代抽象术语。
