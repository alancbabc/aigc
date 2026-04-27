# AIGC Skill Collection

这是一套围绕 AIGC 影视创作流程组织的技能系统，按 **workflow / domain / knowledge / prompts / execution** 分层。

README 负责说明：

- 这个仓库有哪些层
- 每一层负责什么
- 进入仓库后按什么顺序定位入口
- 环境、契约和仓库卫生的统一要求

README 不负责重复各个 leaf skill 的详细规则。

## 系统分层

- `workflows/`：多阶段入口；负责编排、阶段依赖、产物链路、hard gates
- `writer/`：写作域；负责大纲、角色、剧本、新闻双主播解说写作
- `art/`：美术域；负责角色三视图、场景参考、关键帧图像
- `director/`：导演域；负责分镜、转场、试拍、新闻 clip 规划
- `generation/`：执行层；负责图像、视频、语音、OCR/解析
- `_knowledge/`：知识层；提供题材、叙事、摄影、风格等规则
- `_prompts/`：prompt 层；提供模板与模型专用写法

## 入口规则

1. 多阶段任务进入 `workflows/`
2. 单点写作任务进入 `writer/`
3. 单点视觉设计任务进入 `art/`
4. 单点镜头或 clip 规划任务进入 `director/`
5. 单点模型执行任务进入 `generation/`

## 仓库入口顺序

按以下顺序定位入口：

1. `SKILL.md`
2. `docs/_index.md`
3. `ROUTING.md`
4. 对应 workflow 或 domain 的 `SKILL.md`

如果任务已经明确属于某个 workflow 或 domain，直接进入对应入口，不在 README 内停留。

## 常用入口

### Workflows

- `workflows/film-production/`
- `workflows/short-drama-production/`
- `workflows/news-commentary/`
- `workflows/mv-production/`

### Domain Entrances

- `writer/`
- `art/`
- `director/`
- `generation/`

### Shared Layers

- `_knowledge/`
- `_prompts/`
- `ROUTING.md`

## 全局规则

1. 多阶段任务必须走 workflow，不在根入口或 README 中手工拼接阶段。
2. 单点任务必须进入对应 domain 或 leaf skill，不把聚合层当作最终执行层。
3. 标准 workflow 中，进入 `generation/*` 的 prompt 使用英文，除非对应 leaf skill 明确另行规定。
4. 重要产物生成前先读取相关 `_knowledge/`；prompt 写作阶段再读取 `_prompts/`。
5. 聚合层文档只定义入口、边界和路由，不重复 leaf skill 的细节规则。

## 环境与依赖

### 安装依赖

```powershell
pip install -r requirements.txt
```

### 配置环境变量

复制 `.env.example`，再填入所需密钥和环境变量。

```powershell
$env:AIGC_GITEE_API_KEY="your_api_key"
```

可执行工具通过环境变量读取配置，不在仓库中写入真实密钥。

## 接口契约

- 每个核心 skill 目录放置自己的 `.example.json` 和 `.schema.json`
- workflow 间传递的 JSON 产物保持固定字段
- 样例与 schema 与所属 skill 一起维护

## 当前状态

当前仓库已完成第一轮标准化：

- 移除明文密钥示例
- 统一 generation 配置读取方式
- 补充根目录说明、依赖清单、环境变量模板与 `.gitignore`
- 增加 `docs/SKILL_TEMPLATE.md` 作为后续补充规范的模板
- 收紧聚合层 `SKILL.md`，统一为入口 / 边界 / 路由文档

## 仓库卫生

- 不提交 `__pycache__/`、`*.pyc`、`.env`、生成图片和本地运行产物
- Windows 环境下如果误生成名为 `nul` 的异常文件，立即删除，不保留在仓库中
- 新增脚本或调试产物前，确认 `.gitignore` 已覆盖
