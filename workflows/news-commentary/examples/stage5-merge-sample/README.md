# Stage 5 Merge Sample

这个目录提供 `merge_script_stage5.py` 的最小可复用输入样例。

用途：

- 演示 `script-skeleton.json` 与 `script-segments/*.json` 的目录结构
- 作为 Stage 5 merge 的手工验证输入
- 作为后续自动化测试或 fixture 的起点

样例链路：

1. `script-skeleton.json`
2. `script-segments/*.json`
3. `python ../../scripts/merge_script_stage5.py --skeleton ./script-skeleton.json --segments-dir ./script-segments --output ./script.json`
4. `node ../../scripts/build_tts_plan.mjs --script ./script.json --output ./audio/tts-plan.json`

这个目录是正式示例目录，不是临时 `tmp` 产物目录。
