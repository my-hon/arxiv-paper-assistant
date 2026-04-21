# AI论文助手 Skill

一个一站式学术论文处理工具，支持论文搜索、结构化解读、实验复现、语义检索和知识图谱构建。

## ✨ 功能特性

### 📚 论文搜索
- 支持arXiv平台论文搜索
- 多维度检索：关键词、作者、分类、发表日期
- 自动去重和断点续爬
- PDF自动下载和本地存储

### 🔍 论文解读
- 基于大模型的结构化信息提取
- 提取内容包括：核心贡献、研究方法、数据集、结果、局限性
- 支持摘要快速预览和全文深度解读
- 多种输出格式：文本、JSON、Markdown

### 🔬 实验复现
- 自动生成可执行的复现代码
- 自动生成requirements.txt和Dockerfile
- 沙箱环境执行，隔离安全
- 提供详细的复现说明和预期结果

### 🧠 语义检索
- 向量数据库支持的论文语义搜索
- 相似论文智能推荐
- 支持大规模论文库的快速检索

### 📊 知识图谱（开发中）
- 构建论文、作者、机构、方法的关联图谱
- 可视化展示研究领域关系网络

## 🚀 快速开始

### 安装依赖
```bash
pip install arxiv aiohttp pdfplumber langchain langchain-openai chromadb pydantic pydantic-settings loguru
```

### 初始化配置
```bash
paper-assistant init
```
按照提示编辑配置文件 `~/.paper-assistant/.env`，填入你的OpenAI API密钥。

### 开始使用

#### 1. 搜索论文
```bash
# 搜索关键词
paper-assistant search "large language model"

# 指定分类和结果数量
paper-assistant search "computer vision" --categories cs.CV --max-results 20

# 搜索并保存到向量库
paper-assistant search "reinforcement learning" --save
```

#### 2. 解读论文
```bash
# 快速解读（仅用摘要）
paper-assistant interpret 2310.06825

# 完整解读（下载PDF）
paper-assistant interpret 2310.06825 --full

# 输出为Markdown格式
paper-assistant interpret 2310.06825 --output markdown
```

#### 3. 生成复现脚本
```bash
paper-assistant reproduce 2310.06825
```

#### 4. 语义搜索
```bash
paper-assistant search-semantic "chain of thought reasoning"
```

#### 5. 相似论文推荐
```bash
paper-assistant similar 2310.06825
```

#### 6. 查看配置
```bash
paper-assistant config
```

## 📋 系统要求

- Python 3.10+
- pip包管理器
- （可选）Docker引擎（用于复现功能）
- 至少4GB内存（推荐8GB+）

## 🛠️ 安装方法

### 方法1：直接使用（推荐）
将 `paper-assistant/scripts/` 目录添加到PATH环境变量：
```bash
export PATH=$PATH:/path/to/paper-assistant/scripts
```

### 方法2：安装为Python包
```bash
cd paper-assistant
pip install -e .
```

## 📁 目录结构
```
paper-assistant/
├── SKILL.md              # Skill核心定义文件
├── README.md             # 用户使用说明
├── scripts/              # 核心代码
│   ├── cli.py            # 命令行接口
│   ├── config.py         # 配置管理
│   ├── arxiv_crawler.py  # arXiv爬虫
│   ├── paper_interpreter.py # 论文解读
│   ├── vector_store.py   # 向量存储
│   └── reproduction_generator.py # 代码生成
├── references/           # 参考文档
│   ├── configuration.md  # 配置说明
│   └── api-reference.md  # API文档
├── assets/               # 静态资源
│   ├── env.template      # 配置模板
│   └── Dockerfile.template # Docker模板
└── examples/             # 使用示例
```

## 🔧 配置说明

### 核心配置项
| 配置项 | 说明 |
|--------|------|
| `OPENAI_API_KEY` | OpenAI API密钥（必填） |
| `OPENAI_BASE_URL` | API接口地址，可配置为其他兼容服务 |
| `MODEL_NAME` | 使用的大模型名称 |
| `CRAWL_RATE_LIMIT` | arXiv请求间隔（遵守爬虫协议） |

完整配置说明请参考 [references/configuration.md](references/configuration.md)。

## 🌐 兼容国内大模型
本工具支持所有兼容OpenAI接口格式的大模型服务：
- 百度文心一言
- 阿里通义千问
- 讯飞星火
- 智谱AI
- 其他开源模型的API服务

具体配置方法请参考配置说明文档。

## ⚠️ 注意事项

1. **学术版权**：本工具仅用于个人学习和研究用途，请遵守论文版权协议。
2. **爬虫协议**：严格遵守arXiv的robots协议，默认请求间隔1秒。
3. **API费用**：使用大模型会产生API费用，请合理使用。
4. **数据安全**：所有配置和数据仅保存在用户本地，不上传到任何服务器。

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 开发环境设置
```bash
git clone <repository-url>
cd paper-assistant
pip install -r requirements-dev.txt
```

### 代码规范
- 遵循PEP 8规范
- 使用类型注解
- 编写文档字符串
- 提交前运行测试

## 📄 许可证

MIT License

## 📞 联系方式

如有问题或建议，请提交Issue。
