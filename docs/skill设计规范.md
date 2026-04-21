摘要：在人工智能飞速发展的今天，如何让大语言模型真正理解你的业务需求、遵循你的工作规范？Skills（技能）系统给出了答案。本文将深入解析Skills的核心原理、开发规范、实战案例和最佳实践，带你从零开始构建属于自己的AI能力扩展系统。无论你是开发者、产品经理还是团队管理者，都能从中获得实用价值。

一、引言：为什么我们需要Skills？
AI助手的”能力瓶颈”
想象一下这样的场景：你正在使用一个强大的大语言模型助手，它知识渊博、反应迅速，但在处理你的具体工作时却总是”差点意思”：

每次让它写技术文档，你都要重新说明公司的格式规范
让它审查代码，它不知道你们团队的命名约定
生成报告时，它不了解你们业务的数据结构和分析维度
这就是通用大模型的典型困境：能力强大但缺乏领域专业性。

用更技术化的语言来说：Agent Skills 是一套模块化的能力扩展系统，它通过结构化的文件（主要是 Markdown 格式的 SKILL.md）来增强 AI Agent 的能力边界。每个 Skill 封装了特定任务的指令、元数据和可选的辅助资源（如脚本、模板、参考文档等），使得 Agent 能在特定场景下表现出远超通用模型的专业水平。



Skills：AI的”岗位培训手册”
Skills（技能）系统正是为了解决这个问题而生。简单来说：

Skills就是把”某类事情应该怎么专业做”这件事，封装成一个可复用、可自动触发的能力模块。
我们可以用一个生动的比喻来理解：

角色	普通Prompt	Rule/记忆	MCP/Tools	Skills
AI类比	刚毕业的聪明实习生	贴着行为守则的工位	装满软件的电脑	🎁 岗位培训大礼包
内容	每次从头教怎么做	态度和格式规范	外部工具调用能力	PDF+流程图+SOP+话术模板+常用脚本
触发	手动描述	全局生效	按需调用	自动匹配 + 手动命令
Skills带来的核心价值
专业化：将通用模型转变为领域专家
可复用：创建一次，无限次自动使用
组合性：多个Skills协同完成复杂工作流
高效率：渐进式加载，大幅节省Token成本
易维护：修改一个文件，全局生效
二、Skills核心概念与工作原理
什么是Skills？
Skills是模块化能力系统，用于扩展大语言模型（如Claude）的功能。每个Skill打包了：

指令（Instructions）：清晰的工作流程和最佳实践
元数据（Metadata）：描述、触发条件、权限配置
可选资源（Resources）：脚本、模板、参考文档
当用户请求与Skill描述匹配时，模型会自动加载并使用该Skill。

Skills的工作流程
┌─────────────────────────────────────┐
│  1. 启动阶段：加载元数据                │
│  • 读取所有Skills的name和description │
│  • 仅消耗~100 tokens/Skill           │
│  • 用于自动触发判断                    │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  2. 匹配阶段：判断是否需要激活          │
│  • 分析用户请求意图                   │
│  • 匹配Skill的description和关键词    │
│  • 支持手动触发：/skill-name命令      │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  3. 激活阶段：加载完整指令             │
│  • 读取SKILL.md主体内容              │
│  • 通常<5000 tokens                 │
│  • 注入当前上下文执行                  │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  4. 执行阶段：按需加载资源             │
│  • 通过bash命令读取参考文件           │
│  • 执行预定义的脚本                   │
│  • 内容不直接加载到上下文窗口           │
└─────────────────────────────────────┘
渐进式披露（Progressive Disclosure）
这是Skills最核心的设计理念，也是其高效的关键：

层级	内容类型	加载时机	Token消耗	示例内容
Level 1	元数据	启动时始终加载	~100 tokens	name, description, allowed-tools
Level 2	指令	Skill触发时加载	<5000 tokens	工作流程、最佳实践、输出格式
Level 3+	资源/代码	按需通过bash加载	实际无限	参考文档、模板、可执行脚本
这种设计带来了两个关键优势：

低启动成本：可以安装数百个Skills而不会显著增加上下文负担
按需扩展：只有真正需要时，才加载详细内容
Skills文件结构与配置详解
最小可行Skill结构
my-skill/
└── SKILL.md    # 唯一必需文件
推荐的完整结构
my-skill/
├── SKILL.md              # 核心：元数据+指令（必需）
├── reference.md          # 详细文档：配置说明、API参考
├── README.md             # 人类可读的说明文档
├── examples/             # 示例输出和使用场景
│   ├── good-example.md
│   └── bad-example.md
├── references/           # 参考资料：规范、规则、禁用词
│   ├── naming-convention.md
│   └── security-rules.md
└── scripts/              # 可执行脚本（需开启code execution）
    ├── validate.py
    └── generate_report.sh
三、SKILL.md文件详解
SKILL.md是Skill的核心，采用YAML Frontmatter + Markdown正文的格式。文件的开头必须包含 YAML 格式的元数据，用三个短横线 --- 包裹。这是 Skill 被系统识别和索引的关键。

```markdown
---
name: project-health
description: Analyze project health including code quality, dependencies, git status, and generate visual HTML report. Use when user asks to "check project health", "analyze codebase", "run diagnostics", or "generate project report".
argument-hint: [directory] [--fix] [--open]
disable-model-invocation: false
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash(git *), Bash(npm *), Bash(pip *), Bash(python *)
model: sonnet
context: fork
agent: Explore
---

# Project Health Analyzer

## 使用场景
当需要评估代码库健康状况时使用，例如：
- 提交代码前快速检查
- 接手新项目时的快速了解
- 定期代码质量巡检

## 执行步骤
1. 检测项目类型（Node/Python/Go等）
2. 扫描文件结构和代码统计
3. 检查Git状态和提交历史
4. 分析依赖包版本和安全性
5. 计算健康评分（0-100）
6. 生成可视化报告

## 输出格式
- 先输出简要摘要
- 再展示详细分析结果
- 最后提供可操作建议
Frontmatter字段完整说明
字段	类型	必需	说明	示例
name	string	✅	Skill唯一标识，也是斜杠命令名	project-health
description	string	✅	功能描述+触发关键词，决定自动触发	Analyze project health... Use when...
argument-hint	string	❌	参数提示，用于自动补全	[directory] [--fix] [--open]
disable-model-invocation	boolean	❌	是否禁用自动触发	false
user-invocable	boolean	❌	是否在/命令菜单中显示	true
allowed-tools	string	❌	预批准的工具白名单	Read, Grep, Bash(git *)
model	string	❌	使用的模型版本	sonnet / haiku / opus
context	string	❌	执行上下文模式	fork（隔离）/ main（主上下文）
agent	string	❌	子代理类型	Explore / Plan / general-purpose
license	string	❌	许可证信息	Apache-2.0
compatibility	string	❌	环境与依赖说明	Requires Python 3.8+
metadata	object	❌	自定义扩展元数据	{"author": "team-a", "version": "1.2"}
字段编写最佳实践
✅ description字段：决定自动触发率的关键
# ✅ 好的写法：包含功能+典型用户表述
description: >-
  Analyze project health including code quality, dependencies, git status.
  Use when user asks to "check project health", "analyze codebase", 
  "run diagnostics", "generate project report", or "audit dependencies"

# ❌ 不好的写法：过于模糊
description: Analyze stuff
✅ allowed-tools：遵循最小权限原则
# ✅ 精确授权：只允许必要的命令
allowed-tools: Read, Grep, Glob, Bash(git status), Bash(git log -1)

# ❌ 过度授权：可能带来安全风险
allowed-tools: Bash(*)
✅ argument-hint：提升用户体验
# 清晰的参数提示
argument-hint: [directory] [--fix] [--open] [--detailed]

# 用户看到的效果：
# /project-health [directory] [--fix] [--open] [--detailed]
⚡ 渐进式披露：Skills的高效加载机制
为什么需要渐进式披露？
大语言模型的上下文窗口是有限的（通常8K-200K tokens），如果每次对话都加载所有Skills的完整内容：

❌ 上下文迅速耗尽，无法处理用户请求
❌ 响应速度变慢，体验下降
❌ 成本大幅增加
渐进式披露通过”按需加载”解决了这个问题。

三级加载机制详解
Level 1：元数据（启动时加载）
# 每个Skill只加载这部分，约100 tokens
---
name: code-review-expert
description: Professional code review with security checks and best practices
allowed-tools: Read, Grep
---
作用：

让模型知道有哪些Skills可用
用于自动触发判断
几乎不占用上下文空间
Level 2：指令（触发时加载）
# 当用户请求匹配时，加载SKILL.md正文

# Code Review Expert

## 核心原则
- 先理解代码意图，再审查实现
- 优先指出安全问题，再提优化建议
- 每个建议附带修改示例

## 审查清单
1. [安全] SQL注入、XSS、敏感信息泄露
2. [性能] 循环优化、缓存使用、数据库查询
3. [可维护性] 命名规范、函数长度、注释质量
4. [测试] 边界条件、异常处理、覆盖率

## 输出格式
### 🔴 严重问题
### 🟡 改进建议  
### 🟢 优秀实践
作用：

提供具体的工作流程和指导
确保输出的一致性和专业性
通常控制在5000 tokens以内
Level 3：资源（按需通过bash加载）
## 参考规范

如需查看详细的编码规范，执行：
```bash
cat "<!--MATH_PH_1-->{CLAUDE_SKILL_DIR}/examples/good-pattern.tsx"
**关键特点**：
- 通过bash命令读取文件，内容不直接进入上下文
- 模型"看到"的是文件内容，但Token不计入主上下文
- 理论上可以引用任意大小的参考材料
```

### 渐进式披露的实战效果

假设你安装了50个Skills：

| 方案 | 启动开销 | 触发开销 | 总上下文占用 |
|------|---------|---------|-------------|
| 传统Prompt | 50 × 2000 = 100K tokens | - | ❌ 直接超限 |
| Skills机制 | 50 × 100 = 5K tokens | 1 × 3K = 3K tokens | ✅ 仅8K tokens |

这就是为什么你可以"安装很多Skills而无上下文惩罚"。

---

## <a id="实战教程"></a>🛠️ 实战教程：创建你的第一个Skill

### 环境准备

Skills主要支持以下客户端：

| 工具 | 技能路径 | 特点 |
|------|---------|------|
| Claude Code | `~/.claude/skills/` | 官方标准，生态最全 |
| Cursor | `~/.cursor/skills/` | 代码开发友好 |
| Trae / OpenCode | 配置项设置 | 国内用户较多 |
| VS Code插件 | 插件配置 | 正在快速跟进 |

本文以Claude Code为例。

### Step 1：创建Skill目录

```bash
# 个人全局Skills（所有项目可用）
mkdir -p ~/.claude/skills/python-naming-standard

# 或项目级Skills（仅当前项目）
mkdir -p ./my-project/.claude/skills/python-naming-standard
四、Skills 的技术架构
4.1 文件结构
一个标准的 Skill 本质上是一个文件夹，其核心是一个 SKILL.md 文件。完整的文件结构如下：

my-skill/
├── SKILL.md          # [必需] 核心指令文件
├── scripts/          # [可选] 可执行脚本
│   ├── processor.py
│   ├── validator.js
│   └── setup.sh
├── references/       # [可选] 参考资料
│   ├── style-guide.md
│   └── api-spec.json
└── assets/           # [可选] 静态资源
    ├── template.html
    └── config.yaml
```
各目录的职责：

SKILL.md：唯一必需的文件，包含 YAML 元数据头和 Markdown 格式的指令正文。
scripts/：存放可执行脚本，支持 Python、JavaScript、Bash 等语言。当 SKILL.md 中的指令引用脚本时，Agent 会在运行时通过 Bash 执行。
references/：存放参考文档、模板、规范说明等。Agent 按需读取，不会在初始化时全部加载。
assets/：存放静态资源文件，如模板、配置文件、示例数据等。

4.2 渐进式披露机制（Progressive Disclosure）
这是 Skills 系统最核心的设计理念，也是它区别于普通 Prompt 的关键技术点。整个机制分为三个层级：

Level 1：元数据层（约 100 Token）

Agent 启动时，只会读取每个 Skill 的 YAML 头部信息——即 name 和 description 字段。这就像你浏览书架时只看书脊上的书名和简介，不需要翻开每一本书。

---
name: python-code-reviewer
description: 当用户要求审查 Python 代码时，按照 PEP 8 规范和团队内部标准进行全面检查，输出结构化审查报告。
---
Level 2：指令层（建议控制在 5000 Token 以内）

当 Agent 判断当前任务与某个 Skill 相关时（基于用户输入与 description 的语义匹配），才会读取 SKILL.md 的完整正文。这包含详细的操作步骤、规则约束和输出格式要求。

Level 3：资源层（按需加载，不占初始上下文）

只有当指令中明确引用了某个脚本或参考文件时，Agent 才会通过工具调用（如 Bash、Read）去加载对应资源。脚本的执行结果通过标准输出返回，不会把整个脚本内容注入到上下文中。

这种三层结构的好处显而易见：如果你的项目中配置了 20 个 Skills，启动时只消耗约 2000 Token（20 x 100），而不是把 20 个完整 Skill 全部加载（可能需要 100,000+ Token）。这对于 Token 成本和响应速度都有巨大的优化作用。

4.3 技能发现与激活流程
理解了渐进式披露后，我们来看完整的工作流程：

```
用户输入任务
    ↓
Agent 遍历所有 Skill 的 name + description（Level 1）
    ↓
语义匹配：找到最相关的 Skill
    ↓
加载 SKILL.md 完整正文（Level 2）
    ↓
按照指令执行任务
    ↓
[按需] 调用 scripts/ 或读取 references/（Level 3）
    ↓
输出结果
```

这里有一个关键点：Skill 的激活完全依赖于 description 字段的质量。如果描述写得模糊或不够具体，Agent 可能无法正确匹配到对应的 Skill。这也是后面最佳实践中我们会重点讨论的内容。

4.4 Skills.md 编写技巧
原则一：只教 AI 不知道的

大模型本身已经具备了广泛的通用知识。你的 Skill 不需要教它”什么是 Python”或”如何使用 Git”，而应该聚焦于你特有的业务规则、团队规范、领域知识等信息。

<!-- 反面示例：解释基础知识，完全没必要 -->
## 什么是代码审查
代码审查是一种软件质量保证的方法...

<!-- 正面示例：直接给出特定规范 -->
## 审查标准
1. 所有公共函数必须包含类型注解
2. 单个函数不超过 50 行
3. 循环嵌套不超过 3 层
4. 所有 API 端点必须有速率限制
原则二：使用祈使句，步骤清晰

指令应该像操作手册一样，直接告诉 Agent 要做什么。使用有编号的步骤，让执行流程一目了然。

## 执行步骤

1. 读取用户提供的代码文件
2. 检查是否存在以下安全隐患：
   - SQL 注入风险
   - XSS 攻击向量
   - 硬编码的密钥或密码
3. 对每个发现的问题，按以下格式输出：
   - **位置**：文件名:行号
   - **严重级别**：Critical / Warning / Info
   - **问题描述**：一句话说明
   - **修复建议**：提供具体的修改方案
4. 在报告末尾给出总体评分（1-10）和改进优先级排序
原则三：提供具体示例（Few-Shot）

抽象的规则远不如一个具体的例子有效。在 SKILL.md 中应尽量提供输入/输出示例。

## 输出格式示例

### 输入
```python
def get_user(id):
    query = f"SELECT * FROM users WHERE id = {id}"
    return db.execute(query)
```
### 期望输出
...
原则四：明确边界和禁止项

告诉 Agent 什么该做、什么不该做，可以有效防止”幻觉”和意外行为。

## 约束条件

- 只审查用户明确指定的文件，不要主动扫描整个项目
- 不要修改任何代码，只输出审查报告
- 如果不确定某个模式是否有安全风险，标记为 "Needs Review" 而不是直接判定
- 不要在报告中包含任何敏感信息的具体值（如发现的密钥内容）
原则五：控制文档长度

SKILL.md 的正文部分建议控制在 500 行以内，理想情况下在 200-300 行。过长的文档会导致：

加载时消耗过多 Token
Agent 可能遗漏中间部分的指令
维护成本增加
如果你的 Skill 确实需要大量参考信息，应该把它们放到 references/ 目录下，在指令中按需引用。

4.5 常见反模式
反模式一：过度解释基础知识

<!-- 不要这样写 -->
## 什么是 REST API
REST (Representational State Transfer) 是一种软件架构风格...
HTTP 方法包括 GET, POST, PUT, DELETE...

<!-- 应该直接写业务相关的内容 -->
## 我们的 API 设计规范
- 所有端点使用 /api/v{version}/ 前缀
- 列表接口统一使用分页，默认 page_size=20
- 错误响应统一使用 RFC 7807 Problem Details 格式
反模式二：包含时效性信息

<!-- 不要这样写 -->
当前最新版本是 React 18.2.0，发布于 2023 年 6 月...

<!-- 应该让 Agent 动态检查 -->
检查项目 package.json 中的 React 版本，据此选择对应的组件写法。
反模式三：SKILL.md 过长

如果你的 SKILL.md 超过 500 行，考虑：

把参考资料移到 references/ 目录
把复杂逻辑封装到 scripts/
拆分为多个更小的 Skill
反模式四：使用平台特定的路径格式

<!-- 不要这样写 -->
读取 scripts\processor.py

<!-- 应该使用正斜杠 -->
读取 scripts/processor.py
```
五、Skills 的存放与管理
5.1 存放位置
Skills 通常有两个级别的存放位置：

个人级（全局生效）：

~/.claude/skills/
├── my-code-style/
│   └── SKILL.md
├── my-git-workflow/
│   └── SKILL.md
└── my-doc-template/
    └── SKILL.md
个人级 Skills 对你所有的项目都生效，适合存放个人偏好和通用规范。其中 .claude 也可以是其他你安装在本地的AI工作台，比如 .qoder 等。

项目级（仅当前项目生效）：

your-project/
├── .claude/skills/
│   ├── project-api-standard/
│   │   └── SKILL.md
│   └── project-test-guide/
│       └── SKILL.md
├── src/
└── package.json
项目级 Skills 跟随项目仓库。适合存放项目特有的规范和流程。

5.2 安装社区 Skills
除了自己编写，你还可以使用社区共享的 Skills。目前主要的获取渠道包括：

GitHub 官方仓库：anthropics/skills 和其他社区仓库
技能市场：如 skills.sh、http://skillsmp.com 等平台
CLI 安装：通过命令行工具快速安装
# 使用 npx 安装社区 Skill
npx skills add <github-repo> --skill <skill-name>

# 例如
npx skills add anthropics/skills --skill code-review
5.3 版本管理建议
项目级 Skills 应纳入 Git 版本管理
在 SKILL.md 的 metadata 中标注版本号
重大变更时更新版本号并记录 Changelog
考虑使用 Git tag 来标记 Skill 的发布版本
六、高级用法
6.1 多 Skill 协作流
在复杂项目中，多个 Skills 可以组成协作流水线。以”规范化编码”流程为例：

需求输入
  ↓
[需求分析师 Skill] → 输出 REQUIREMENT.md
  ↓
[技术架构师 Skill] → 基于需求输出 DESIGN.md
  ↓
[任务规划师 Skill] → 拆解为 TODO.md
  ↓
[规范执行者 Skill] → 按文档编写代码
  ↓
[代码审查员 Skill] → 审查并输出报告
这种”角色链”的设计模式，让每个 Skill 专注于自己的职责，通过文档接口进行协作，实现了复杂工程流程的自动化。

6.2 条件分支执行
在 SKILL.md 中可以设计条件分支逻辑：

## 执行策略

1. 检查项目语言和框架：
   - **如果是 TypeScript 项目**：按照 `references/ts-style.md` 中的规范执行
   - **如果是 Python 项目**：按照 `references/py-style.md` 中的规范执行
   - **如果是 Go 项目**：按照 `references/go-style.md` 中的规范执行
   - **其他语言**：提示用户该 Skill 暂不支持，给出通用建议

2. 检查是否存在项目自定义配置（如 `.eslintrc`、`pyproject.toml`）：
   - **如果存在**：优先使用项目配置，Skill 规范作为补充
   - **如果不存在**：完全使用 Skill 内置规范
6.3 与 MCP 工具配合
Skills 可以在指令中引导 Agent 使用 MCP 工具：

## 数据分析流程

1. 使用 MCP 的数据库查询工具获取原始数据
2. 按照以下规则清洗数据：
   - 去除空值行
   - 日期格式统一为 ISO 8601
   - 金额字段保留两位小数
3. 使用 Python 脚本 `scripts/analyze.py` 进行统计分析
4. 使用 MCP 的图表生成工具输出可视化结果
6.4 动态资源引用
SKILL.md 中可以通过相对路径动态引用资源，Agent 会在需要时按需加载：

## 资源引用

- 编码规范详情请参阅 `references/coding-standard.md`
- API 设计模板请参阅 `references/api-template.yaml`
- 如需执行格式化，运行 `scripts/format.sh <文件路径>`
这种方式确保了上下文的精简——只有被实际引用的资源才会被加载。

本文参考了 Anthropic 官方文档、社区教程和多位开发者的实践经验。如有疏漏，欢迎指正。