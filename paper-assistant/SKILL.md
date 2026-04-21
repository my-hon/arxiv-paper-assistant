---
name: paper-assistant
description: AI论文助手，支持arXiv论文搜索、结构化解读、实验复现、语义检索和知识图谱构建。使用当用户问"搜索论文"、"解读论文"、"复现论文"、"相似论文推荐"、"论文知识图谱"等关键词。
argument-hint: [command] [paper-id/query] [options]
disable-model-invocation: false
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash(python *), Bash(pip *), Bash(curl *), Bash(docker *)
model: sonnet
context: fork
agent: general-purpose
license: MIT
compatibility: Requires Python 3.10+, Docker (可选)
metadata: {"author": "AI论文团队", "version": "1.0.0", "category": "research"}
---

# AI论文助手 Skill

## 功能概述
一个一站式学术论文处理工具，提供以下核心功能：
- 📚 论文搜索：从arXiv等平台搜索和下载学术论文
- 🔍 论文解读：基于大模型对论文进行结构化信息提取
- 🔬 实验复现：自动生成可执行的复现代码和环境配置
- 🧠 语义检索：向量数据库支持的论文语义搜索和相似推荐
- 📊 知识图谱：构建论文、作者、机构、方法的关联图谱

## 使用场景
当用户需要执行以下任务时使用本Skill：
1. 搜索特定领域的最新研究论文
2. 快速理解论文核心内容和创新点
3. 尝试复现论文中的实验结果
4. 查找相关领域的相似研究
5. 构建领域研究知识图谱

## 执行步骤

### 通用流程
1. 检查用户当前目录是否有配置文件，如无则引导用户初始化配置
2. 根据用户命令调用对应的功能模块
3. 输出结构化的执行结果
4. 提供后续操作建议

### 命令说明

#### 1. 搜索论文
```
/paper-assistant search [query] [options]
```
**参数**：
- `query`：搜索关键词（作者、标题、研究领域等）
- `--max-results N`：返回结果数量（默认10）
- `--categories LIST`：指定分类，如cs.CL,cs.AI（逗号分隔）
- `--save`：保存结果到本地数据库

**执行步骤**：
1. 调用arXiv API执行搜索
2. 解析返回结果，提取论文标题、作者、摘要、发表日期
3. 按相关性排序输出
4. 询问用户是否需要下载PDF或解读某篇论文

#### 2. 解读论文
```
/paper-assistant interpret [paper-id] [options]
```
**参数**：
- `paper-id`：arXiv论文ID，如2310.06825
- `--pdf PATH`：本地PDF文件路径（可选）
- `--full`：完整解读（默认只提取核心信息）
- `--output FORMAT`：输出格式：text/json/markdown（默认text）

**执行步骤**：
1. 检查论文是否已存在本地，如无则自动下载
2. 解析PDF内容，提取文本信息
3. 调用大模型进行结构化解读，提取：
   - 核心贡献和创新点
   - 研究方法和实验设计
   - 使用的数据集和评估指标
   - 主要结论和局限性
4. 按照指定格式输出结果

#### 3. 生成复现脚本
```
/paper-assistant reproduce [paper-id] [options]
```
**参数**：
- `paper-id`：arXiv论文ID
- `--docker`：生成Dockerfile（默认）
- `--venv`：生成虚拟环境配置
- `--run`：自动执行复现脚本

**执行步骤**：
1. 分析论文中的方法描述和实现细节
2. 生成对应的Python代码和依赖配置
3. 创建Dockerfile或requirements.txt
4. 提供运行说明和预期结果对比方法

#### 4. 语义搜索
```
/paper-assistant search-semantic [query] [options]
```
**参数**：
- `query`：搜索文本
- `--limit N`：返回结果数量（默认5）
- `--threshold FLOAT`：相似度阈值（默认0.7）

**执行步骤**：
1. 将查询文本转换为向量嵌入
2. 在向量数据库中检索相似论文
3. 按相似度排序输出结果
4. 提供论文摘要和下载链接

#### 5. 相似论文推荐
```
/paper-assistant similar [paper-id] [options]
```
**参数**：
- `paper-id`：arXiv论文ID
- `--limit N`：推荐数量（默认10）

#### 6. 知识图谱生成
```
/paper-assistant graph [paper-id] [options]
```
**参数**：
- `paper-id`：arXiv论文ID
- `--depth N`：扩展深度（默认2）
- `--output PATH`：导出HTML图谱路径

### 配置管理
#### 初始化配置
```
/paper-assistant init
```
引导用户配置：
- OpenAI API密钥
- 基础URL和模型名称
- 存储路径和缓存策略

#### 查看配置
```
/paper-assistant config
```
显示当前配置信息（隐藏敏感字段）

## 输出格式规范

### 搜索结果格式
```
📚 搜索结果（共N篇）
---
1. **论文标题** (arXiv:XXXX.XXXXX)
   📝 作者：作者1, 作者2, 作者3
   📅 发表日期：YYYY-MM-DD
   🔍 分类：cs.CL, cs.AI
   📄 摘要：简要摘要内容...
   🔗 链接：https://arxiv.org/abs/XXXX.XXXXX
```

### 解读结果格式
```
🔍 论文解读：[论文标题] (arXiv:XXXX.XXXXX)
---
## 🎯 核心贡献
1. 贡献点1
2. 贡献点2

## 🛠️ 研究方法
- 方法1：描述
- 方法2：描述

## 📊 实验结果
- 数据集：数据集名称
- 评估指标：指标1: X, 指标2: Y
- 主要结论：结论描述

## ⚠️ 局限性
1. 局限性1
2. 局限性2

## 💡 相关研究推荐
- 推荐论文1
- 推荐论文2
```

### 复现脚本格式
```
🔬 复现脚本生成成功！
---
📁 生成的文件：
- reproduction/XXXX.XXXXX/
  ├── main.py          # 主执行脚本
  ├── requirements.txt # 依赖配置
  ├── Dockerfile       # Docker配置
  └── README.md        # 使用说明

🚀 运行方式：
# 方法1：Docker运行
docker build -t reproduce-XXXX . && docker run reproduce-XXXX

# 方法2：本地运行
pip install -r requirements.txt
python main.py
```

## 约束条件
1. 尊重学术版权，仅用于个人研究用途
2. 严格遵守arXiv的爬虫协议，请求频率不超过1次/秒
3. 大模型调用消耗API配额，提醒用户合理使用
4. 复现功能需要Docker环境支持，如无则提示用户
5. 不存储用户的API密钥，配置信息仅保存在用户本地

## 依赖检查
首次使用时自动检查以下依赖：
- Python 3.10+
- pip包管理器
- 必需Python包：arxiv, aiohttp, pdfplumber, langchain, openai, chromadb
- （可选）Docker引擎

如依赖缺失，自动提示安装命令。

## 参考资源
- 配置说明详见：`references/configuration.md`
- API接口文档：`references/api-reference.md`
- 使用示例：`examples/`目录
