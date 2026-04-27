# MV-LRC-Workflow

音乐视频生成工作流 - 从 LRC 格式歌词到分镜 Prompt。

## 快速开始

### 1. 准备输入文件

```
project/
├── song.lrc        # LRC 格式歌词文件
└── song.mp3        # 歌曲音频文件
```

### 2. 运行 Stage 1: LRC 解析

```bash
python scripts/build_song_structure.py path/to/song.lrc -o song-structure.json -t "歌曲标题" -a "艺术家"
```

### 3. 运行 Stage 6: 分镜生成

```bash
python scripts/build_mv_storyboard.py song-structure.json -o storyboard.json -t mixed
```

## LRC 格式

### 支持的格式

```text
[ti: 歌曲标题]
[ar: 艺术家]

[00:00.00](Intro)
[00:15.00](Verse 1)
[00:30.50]第一句歌词
[00:34.20]第二句歌词
[01:00.00](Chorus)
```

### 格式规则

| 模式 | 示例 | 说明 |
|------|------|------|
| 元数据 | `[ti: 标题]` `[ar: 艺术家]` | 歌曲信息 |
| 分段 | `[00:00.00](Intro)` | 分段开始 |
| 歌词 | `[00:30.50]歌词内容` | 带时间戳的歌词 |

## Stage 说明

| Stage | 脚本 | 输入 | 输出 |
|-------|------|------|------|
| 1 | `build_song_structure.py` | LRC | `song-structure.json` |
| 6 | `build_mv_storyboard.py` | song-structure.json | `storyboard.json` |

## 输出示例

### song-structure.json

```json
{
  "sections": [
    {
      "section_id": "intro",
      "section_type": "intro",
      "start_time": 0.0,
      "end_time": 15.5,
      "lyrics_lines": []
    },
    {
      "section_id": "verse_1",
      "section_type": "verse",
      "start_time": 15.5,
      "end_time": 60.0,
      "lyrics_lines": ["回忆像一部老电影", "画面渐渐变得清晰"]
    }
  ]
}
```

### storyboard.json

```json
{
  "shots": [
    {
      "shot_id": "shot_001",
      "section_ref": "intro",
      "start_time": 0.0,
      "end_time": 5.0,
      "camera": "slow_push",
      "action": "establishing shot"
    }
  ]
}
```

## 完整 Pipeline

```bash
# Stage 1: LRC 解析
python scripts/build_song_structure.py input.lrc -o song-structure.json -t "Title" -a "Artist"

# Stage 2-5: (via Writer/Art skills)

# Stage 6: Storyboard
python scripts/build_mv_storyboard.py song-structure.json -o storyboard.json

# Stage 7-8: (via Art skill)

# Stage 9-12: (via Generation skill)

# Stage 13: Final
python scripts/assemble_mv.py video-plan.json --audio song.mp3 --output output.mp4
```

## 示例文件

参考 `examples/input/sample.lrc` 了解完整 LRC 格式。

## 依赖

- Python 3.8+
- json, re (标准库)