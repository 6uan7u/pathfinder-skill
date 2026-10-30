# Pathfinder：第一性原理学习与行动导航 skill

提出一个概念、领域、问题或想做成的事，Pathfinder 会从你已有的基础出发（完全不懂就从零开始），先找到"它为什么存在"，再搭出全局框架、标出主干和弯路、给出路线，然后逐个节点深入讲解并检验理解。它也能拆解你的课程 PPT、PDF、Word 讲义，并生成可交互的知识地图、2D 动画和 3D 场景。

## 目录结构

```
pathfinder-skill/
├── skills/pathfinder/              ← skill 本体（安装时复制这个文件夹）
│   ├── SKILL.md                    工作流：识别模式 → 校准基础 → 第一性原理拆解 → 全局地图 → 逐节点深入 → 沉淀
│   ├── references/
│   │   ├── modes.md                五种模式：概念 / 领域 / 问题 / 材料拆解 / 行动
│   │   ├── pedagogy.md             分层讲解、诊断、检验理解、误解处理、间隔复习、苏格拉底模式
│   │   ├── visualization.md        可视化选型表、map.json 格式、动画/3D 制作规范
│   │   ├── focus.md                注意力与信息筛选：本质公式、瓶颈、最小必要知识、信息源分级、不做清单、一页纸作战图
│   │   ├── materials.md            课件/PDF 拆解流程、考试导向
│   │   └── profile-template.md     跨主题学习者档案模板
│   ├── scripts/
│   │   ├── build_map.py            map.json → 交互式知识地图 HTML（零依赖、离线可用）
│   │   └── extract_material.py     pptx(含备注)/docx/pdf/md/txt/html → 带页码的 Markdown
│   └── assets/templates/
│       ├── knowledge-map.html      知识地图：聚焦作战图 / 思维导图 / 依赖图（点击高亮前置链）/ 路线流水线 / 进度
│       ├── animation-2d.html       2D 讲解动画框架：分步讲解 + 参数滑块 + 播放控制
│       └── scene-3d.html           3D 场景框架（Three.js）：轨道相机 + 标签 + 分步讲解
└── examples/
    ├── fourier-transform/          示例：概念模式——傅里叶变换的知识地图
    └── self-media/                 示例：行动模式——从零做知识类自媒体的一页纸作战图 + 路线
```

## 注意力优先

信息过载时代，Pathfinder 的核心是**替你做减法**，尤其在做自媒体、电商、副业这类"行动"目标时：

- **本质公式**：把目标拆成几个相乘的变量（如 电商利润 ≈ 流量 × 转化 × 客单价 × 复购 − 成本）
- **瓶颈**：找出当前最拖后腿的那一项，接下来 2-4 周只解决它
- **最小必要知识**：只给走出第一步所需的 3-5 条，其余"做到那一步再学"
- **不做清单**：明确现在不该看、不该做的事，以及什么时候再考虑
- **信息源分级**：一手数据 > 官方 > 有可验证成绩的实践者 > 系统资料 > 二手解读 > 营销内容
- **反馈回路**：一个领先指标 + 一个结果指标 + 每周 15 分钟复盘 + 提前写好的止损/转向条件

第一次回复是一屏能看完的作战图，而不是一篇长攻略。之后说"复盘"并带上数据，它会重新判断瓶颈。

## 安装

这个 skill 遵循开放的 Agent Skills 格式（一个带 `SKILL.md` 的文件夹），Claude Code、Codex 等支持 skills 的 agent 都能用。

### 方式一：一条命令安装（推荐，需要 Node.js）

```bash
npx skills add Blossom-stark/pathfinder-skill
```

这里用的是开源的 [skills](https://github.com/vercel-labs/skills) 命令行工具，按提示选择要装到哪个 agent。以后要更新，重新运行这条命令即可。

### 方式二：Claude Code 插件市场

在 Claude Code 里依次输入：

```
/plugin marketplace add Blossom-stark/pathfinder-skill
/plugin install pathfinder@pathfinder-skill
```

### 方式三：手动复制

```bash
git clone https://github.com/Blossom-stark/pathfinder-skill.git
```

然后把 `skills/pathfinder` 文件夹复制到对应 agent 的 skills 目录：

| Agent | 全局目录 | 项目目录 |
|---|---|---|
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| Codex CLI | `~/.codex/skills/` | `.codex/skills/` |
| 其他支持 Agent Skills 的工具 | 见该工具文档 | 见该工具文档 |

### 方式四：Claude 网页版 / 桌面版

下载本仓库（Code → Download ZIP）并解压，把其中的 `skills/pathfinder` 文件夹单独压缩成 zip，然后在 Claude 的设置中找到 Skills 并上传这个 zip。

### 不支持 skills 的 agent

让它读取 `skills/pathfinder/SKILL.md` 并按其中的说明工作即可，脚本和模板的路径都相对于这个文件夹。

### 可选依赖

需要 Python 3.8+。提取 PDF 需要任一解析库（pptx/docx 不需要任何依赖）：

```bash
pip install pypdf
```

## 使用

直接说就行，不需要特定命令：

- "我想从零学傅里叶变换，我只懂三角函数"
- "帮我把这份《机器学习》第三讲的 PPT 拆解一下，下周要考试"
- "为什么 Transformer 要用多头注意力？"
- "我想做一个独立游戏，完全没经验，怎么不走弯路？"
- "帮我画一张量子计算的知识框架图"
- "我想做电商但信息太多了，不知道该看什么，最核心的是什么？"

学习过程中可以随时说：继续、讲浅点/讲深点、举个例子、画出来、考考我、我懂了、跳过、进度、总结、复习、复盘、只说最重要的。

学习数据保存在当前工作区的 `learning/<主题>/`（map.json、map.html、notes.md、visuals/），学习者档案保存在 `~/.pathfinder/profile.md`（不同 agent 共享同一份），下次继续时会自动读取。

## 设计来源

整合了以下项目的思路（只借鉴思路，未复制代码）：

- [Sigma](https://claudemarketplaces.com/skills/sanyuan0704/code-review-expert/sigma)：Bloom 2-Sigma 一对一辅导、先诊断、掌握门槛、误解追踪、学习者档案、间隔复习
- [Mr. Ranedeer AI Tutor](https://github.com/JushBJJ/Mr.-Ranedeer-AI-Tutor)：深度分级、讲解风格与节奏的个性化、自然语言命令
- [learnmap-skill](https://skills.cat/u/lwbscu)：从材料生成课程、地图优先
- [School Skills for Claude Code](https://sharedcontext.ai/plugins/external/Jellypod-Inc/school-skills-for-claude-code)：苏格拉底式辅导与概念图

在此基础上新增：第一性原理拆解（从"它解决的问题"讲起）、弯路清单、"行动"模式（不止学习）、带先修链高亮的零依赖交互地图、可复用的 2D/3D 讲解动画框架、课件页码映射。

## 许可证

[MIT](LICENSE)
