---
name: Style Library
description: 验证过的风格 prompt 模板。生成关键帧/图像/视频时读取此库获取风格参考。
trigger: 生成图像/视频时，读取此库获取风格 prompt
---

# Style Library 风格提示词库

> ⚠️ **铁则**：所有 prompt 必须使用纯英文

---

## 风格选择规则

**判断流程（优先级从高到低）：**

```
1. 用户明确指定风格？ → 直接使用指定风格
2. 项目类型是动画短片？ → 动画风格库 (迪士尼/追光/Ghibli/水墨)
3. 项目类型是真人/实拍？ → 电影质感/复古/赛博
4. 查看 visual_style 字段？ → 使用对应风格
5. 查看 references 参考作品？ → 匹配风格
6. 均无 → 询问用户
```

**按项目类型推荐：**

| 项目类型 | 推荐风格 |
|----------|----------|
| 动画短片 / 儿童片 | 迪士尼/皮克斯、宫崎骏/新海诚、中国2D水墨 |
| 3D动画电影 / 古装动画 | 追光中国风 |
| 真人短片 / 电影感 | 电影质感 |
| 年代戏 / 怀旧 | 复古年代 |
| 科幻 / 未来 | 赛博朋克 |
| 中国风 / 艺术 | 中国2D水墨 |

**风格映射示例：**
- "我要宫崎骏风格的" → Ghibli style
- "电影感镜头" → cinematic, movie quality
- "80年代复古风" → vintage, retro, 1980s aesthetic

---

## 1. 迪士尼/皮克斯风格 (Disney/Pixar Style)

**Core Token**：`Disney 3D, Pixar style`

**增强词**（可选，酌情添加）：
- warm and cute, bright colors, soft lighting
- smooth textures, high detail

**适用**：儿童片、家庭片、动画短片

**示例**：
```
a cute 8-year-old Chinese girl, Disney 3D, Pixar style, warm and cute, bright color, soft lighting, round friendly shapes, big expressive eyes, pink dress, white background
```

---

## 2. 追光动画中国风3D (Light Chaser Chinese 3D)

**Core Token**：`Light Chaser animation, Chinese 3D style, CGI, animated movie`

**增强词**（可选）：
- 3D CGI animation, computer generated
- ancient Chinese costume, ornate details
- rich colors, golden accents, premium quality
- Toon shading, cel-shaded look (可选添加)

**适用**：中国古装、神话传说、历史故事

**示例**：
```
a young Chinese warrior, Light Chaser, Chinese 3D, CG movie, ancient Chinese costume, red and gold colors, ornate embroidery, silk cape, sword at waist, confident stance, cinematic lighting
```

---

## 3. 宫崎骏/新海诚风格 (Miyazaki/Makoto Shinkai Style)

**Core Token**：`Ghibli style, hand-drawn 2D`

**增强词**（可选）：
- soft colors, delicate light, dreamy atmosphere
- emotional and poetic, watercolor texture

**适用**：青春、爱情、治愈、文艺题材

**示例**：
```
a small town at sunset, Ghibli style, hand-drawn 2D, soft warm colors, golden hour light, delicate clouds, whimsical atmosphere, traditional houses, green hills, poetic mood
```

---

## 4. 中国2D彩色水墨 (Chinese Color Ink Wash)

**Core Token**：`Chinese ink wash, 2D animation`

**增强词**（可选）：
- vibrant colors, watercolor texture
- poetic and elegant, dreamy atmosphere

**适用**：中国风、艺术短片、诗词意境

**示例（场景）**：
```
ancient Chinese courtyard in spring, Chinese ink wash, 2D animation, pink cherry blossoms, soft green bamboo, golden morning light, traditional architecture, poetic and elegant, dreamy atmosphere
```

**示例（角色）**：
```
a young Chinese girl in traditional dress, Chinese ink wash, 2D animation, soft pink and emerald colors, delicate brush strokes, elegant and poetic, dreamy, traditional Chinese aesthetics
```

---

## 5. 电影质感 (Cinematic)

**Core Token**：`cinematic, movie quality, film grain`

**增强词**（可选）：
- cinematic lighting, dramatic shadows
- shallow depth of field, anamorphic lens
- film grain, color grading

**适用**：真人短片、电影感视频

**示例**：
```
a lone warrior at sunset, cinematic, movie quality, dramatic lighting, shallow depth of field, film grain, warm color grading, epic landscape
```

---

## 6. 复古年代 (Vintage/Retro)

**Core Token**：`vintage, retro, retro aesthetic`

**增强词**（可选）：
- 1980s / 1990s / 1970s aesthetic
- film grain, muted colors
- nostalgic mood, worn textures

**适用**：年代戏、怀旧风、复古短片

**示例**：
```
a young woman in a neon-lit street, vintage, retro, 1980s aesthetic, film grain, muted colors, nostalgic mood, rain-soaked streets
```

---

## 7. 赛博朋克 (Cyberpunk)

**Core Token**：`cyberpunk, neon lights, futuristic, video game character, game style`

**增强词**（可选）：
- video game art, game ready asset
- neon city, rain and mist
- holographic ads, LED lights
- dark atmosphere, high contrast
- cel-shaded (可选添加卡通感)

**适用**：科幻、未来题材、赛博朋克短片

**示例**：
```
a futuristic street in neon rain, cyberpunk, neon lights, futuristic city, rain and mist, holographic advertisements, LED signs, dark atmosphere, high contrast
```

---

## 更新日志

- 2026-03-16: 精简为 Core Token + 可选增强词
- 2026-03-16: 新增电影质感、复古年代、赛博朋克三种风格
- 2026-03-16: 新增风格选择规则（按项目类型/用户指定判断）