# News Commentary Contracts

这个目录按阶段/模块收纳 `news-commentary` workflow 的 JSON contract。

## 结构约定

- 每个模块一个子目录
- 尽量同时提供：
  - `*.schema.json`：字段约束
  - `*.example.json`：最小可读示例
- builtin 模板与执行脚本不放在这里：
  - 模板保留在 `../builtin-anchor-templates/`
  - 脚本保留在 `../scripts/`

## 模块索引

- `anchors/`
- `article-analysis/`
- `article-review/`
- `audio-timeline/`
- `clip-plan/`
- `ltx-prompt-package/`
- `render-plan/`
- `script/`
- `script-segment/`
- `script-skeleton/`
- `script-review/`
- `tts-plan/`
- `series-profile/`
- `source-visual-assets/`
- `user-requirements/`
- `visual-assets/`

## 常用读取顺序

如果你是第一次接这个 workflow，按下面顺序读：

1. `user-requirements/`
2. `article-analysis/`
3. `anchors/`
4. `script-skeleton/`
5. `script-segment/`
6. `script/`
7. `tts-plan/`
8. `audio-timeline/`
9. `clip-plan/`
10. `render-plan/`

## 说明

- `article-review/` 与 `script-review/` 当前主要提供 schema，用于 review 产物约束。
- `user-requirements/` 额外包含 `user-requirements.builtin.example.json`，用于 builtin 模板默认路径示例。
- `tts-plan/` 与 `audio-timeline/` 现在承担 script → audio 的稳定回溯链路，便于在 TTS 超时后回拆对应 script line 并局部重生成音频。
- `tts-plan/` 是预合成规划文件，负责切分、估时和 entry 追踪，不承诺真实 `audio_path`。
- `audio-timeline/` 是实际音频结果文件，负责真实 `audio_path`、真实 `duration_seconds` 和后续 Stage 9 / 10 的音频消费。
- `clip-plan/` 可在早期临时读取 `tts-plan/` 做预分组，但 `render-plan/` 应只消费来自 `audio-timeline/` 的真实音频路径和时长。
- `script-skeleton/` 与 `script-segment/` 用于 Stage 5 的小文件中间产物链，避免小模型一次性写完整 `script.json` 时出现输出截断或续写失稳。
- Stage 5 的显式 merge 执行器为：`../scripts/merge_script_stage5.py`，用于把 `script-skeleton.json` 与 `script-segments/*.json` 合并成最终 `script.json`。

## 解释责任

这个目录只负责列出 contract 本身，不在这里重复展开所有业务规则。

- 与 Stage 5 / 6 写作链直接相关的 contract，由 `writer/news-commentary-writing` 解释和消费：
  - `article-analysis/`
  - `script-skeleton/`
  - `script-segment/`
  - `script/`
  - `script-review/`
- 与 Stage 9 / 10 视觉绑定和渲染消费直接相关的 contract，由 `director/news-commentary-clip-planning` 解释和消费：
  - `source-visual-assets/`
  - `audio-timeline/`
  - `clip-plan/`
  - `render-plan/`

如果你在主 workflow 中只需要知道阶段依赖与产物链路，回到 `../SKILL.md`；
如果你需要知道字段该如何用于写作或视觉路由，则进入对应的 Writer / Director 子技能。
