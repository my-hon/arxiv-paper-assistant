# AI论文搜集解读复现系统

一个一站式的学术论文处理平台，支持论文爬取、结构化解读、实验复现、知识图谱构建。

## 功能特性

### 📚 论文搜集模块
- 支持多平台数据源：arXiv、Semantic Scholar（开发中）、IEEE Xplore（开发中）
- 合规爬虫策略：速率限制、请求头伪装、robots.txt遵守
- 多维度检索：关键词、作者、机构、发表日期、分类
- 自动去重、断点续爬、增量更新
- PDF自动下载和本地存储

### 🔍 论文解读模块
- 基于大模型的结构化信息提取
- 提取内容包括：核心贡献、实验方法、数据集、结论、创新点、局限性
- 支持全文解读和摘要快速预览
- 输出格式校验和置信度评估
- 解读结果缓存，避免重复计算

### 🔬 复现验证模块
- 自动生成可执行的复现代码、requirements.txt、Dockerfile
- 沙箱环境执行，隔离安全
- 自动对比复现结果与论文结果，计算一致性得分
- 生成详细的复现报告，包含执行日志和结果分析
- 支持批量复现任务管理

### 🧠 知识库模块
- 向量数据库语义检索
- 相似论文推荐
- 知识图谱构建（论文-作者-机构-方法-数据集关联）
- 分类管理和标签体系
- 多格式导出支持

## 技术栈

| 层级 | 技术选型 |
|------|----------|
| 后端框架 | FastAPI + Python 3.10+ |
| 异步爬虫 | aiohttp + feedparser |
| PDF解析 | pdfplumber |
| 大模型 | LangChain + OpenAI API（兼容多模型） |
| 向量数据库 | ChromaDB |
| 关系数据库 | SQLite / PostgreSQL |
| 知识图谱 | NetworkX + PyVis |
| 沙箱执行 | Docker |
| 部署 | Docker Compose |

## 快速开始

### 环境要求
- Python 3.10+
- Docker（可选，用于复现功能和容器部署）
- 至少4GB内存（推荐8GB+）

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置环境变量
```bash
cp .env.example .env
```

编辑 `.env` 文件，配置你的OpenAI API密钥等信息：
```env
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1  # 可配置为其他兼容接口
MODEL_NAME=gpt-3.5-turbo-1106
```

### 3. 启动服务
```bash
cd src
python main.py
```

或者在项目根目录执行：
```bash
python src/main.py
```

服务将在 `http://localhost:8000` 启动。

### 4. 访问API文档
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Docker部署

### 使用Docker Compose一键启动
```bash
# 配置环境变量
export OPENAI_API_KEY=your-openai-api-key

# 启动服务
docker-compose up -d
```

### 构建自定义镜像
```bash
docker build -t ai-paper-system .
docker run -p 8000:8000 -v $(pwd)/storage:/app/storage ai-paper-system
```

## API接口示例

### 1. 搜索arXiv论文
```bash
curl -X POST "http://localhost:8000/api/v1/crawler/search/arxiv" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "large language model",
    "max_results": 10,
    "categories": ["cs.CL", "cs.AI"],
    "save_to_db": true
  }'
```

### 2. 解读论文
```bash
curl -X POST "http://localhost:8000/api/v1/interpretation/arxiv_2310.06825"
```

### 3. 生成复现脚本
```bash
curl -X POST "http://localhost:8000/api/v1/reproduction/generate/arxiv_2310.06825"
```

### 4. 语义搜索
```bash
curl -X POST "http://localhost:8000/api/v1/knowledge/search?query=chain of thought&limit=5"
```

### 5. 获取相似论文
```bash
curl -X GET "http://localhost:8000/api/v1/knowledge/similar/arxiv_2310.06825"
```

## 项目结构

```
.
├── main.py                          # 项目主入口
├── requirements.txt                 # Python依赖
├── .env.example                     # 环境变量模板
├── Dockerfile                       # Docker构建文件
├── docker-compose.yml               # Docker Compose配置
├── ARCHITECTURE.md                  # 系统架构文档
├── README.md                        # 项目说明
├── src/
│   ├── config/                      # 配置模块
│   │   └── settings.py              # 配置文件
│   ├── core/                        # 核心模块
│   │   └── init.py                  # 系统初始化
│   ├── db/                          # 数据库模块
│   │   ├── database.py              # 数据库连接
│   │   └── models.py                # 数据模型
│   ├── modules/                     # 业务模块
│   │   ├── crawler/                 # 爬虫模块
│   │   │   └── arxiv_crawler.py     # arXiv爬虫
│   │   ├── interpretation/          # 论文解读模块
│   │   │   └── paper_interpreter.py # 论文解读器
│   │   ├── reproduction/            # 复现验证模块
│   │   │   └── script_generator.py  # 脚本生成器
│   │   └── knowledge/               # 知识库模块
│   │       └── vector_store.py      # 向量存储
│   └── api/                         # API接口
│       └── v1/
│           ├── api.py               # 路由总入口
│           └── endpoints/           # 接口实现
│               ├── crawler.py
│               ├── interpretation.py
│               ├── reproduction.py
│               ├── knowledge.py
│               └── papers.py
├── storage/                         # 文件存储目录
│   ├── paper_system.db              # SQLite数据库文件
│   ├── chroma_db/                   # 向量数据库存储
│   ├── papers/                      # 论文解析结果（按论文ID分类）
│   │   └── {paper_id}/
│   │       ├── raw/                 # 原始PDF和文本
│   │       ├── images/              # 提取的图片
│   │       ├── structured/          # 结构化解析结果
│   │       └── reports/             # 生成的解读报告
│   ├── pdfs/                        # 原始PDF文件存储
│   ├── scripts/                     # 复现脚本
│   └── reports/                     # 复现报告
├── logs/                            # 日志文件
```

## 配置说明

### 核心配置
| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `OPENAI_API_KEY` | OpenAI API密钥 | 必填 |
| `OPENAI_BASE_URL` | API接口地址 | `https://api.openai.com/v1` |
| `MODEL_NAME` | 使用的大模型名称 | `gpt-3.5-turbo-1106` |
| `CRAWL_RATE_LIMIT` | 爬虫请求间隔（秒） | `1.0` |
| `SANDBOX_TIMEOUT` | 复现任务超时时间（秒） | `300` |
| `EMBEDDING_MODEL_NAME` | 向量嵌入模型 | `all-MiniLM-L6-v2` |

## 开发指南

### 添加新的数据源
1. 在 `src/modules/crawler/` 下创建新的爬虫类，实现 `search_papers` 和 `download_pdf` 方法
2. 在 `src/api/v1/endpoints/crawler.py` 添加对应的API接口
3. 更新支持的数据源列表

### 扩展大模型支持
系统使用LangChain抽象层，可以轻松支持其他大模型，只需修改 `PaperInterpreter` 和 `ScriptGenerator` 中的LLM初始化代码。

### 自定义解读字段
修改 `PaperInterpretationResult` Pydantic模型，添加需要的字段，然后更新对应的Prompt模板。

## 性能优化建议

1. **向量检索性能**：对于大规模论文库（>10万篇），建议使用Qdrant或Weaviate替代ChromaDB
2. **异步任务**：对于爬虫、解读、复现等耗时任务，建议使用Celery或RQ实现异步队列
3. **缓存策略**：对热门论文的解读结果和向量嵌入进行缓存，减少重复计算
4. **分布式部署**：支持多节点分布式爬虫和复现任务调度

## 安全考虑

1. **API限流**：生产环境建议添加API限流和身份认证
2. **沙箱隔离**：复现脚本在Docker沙箱中运行，限制资源占用和网络访问
3. **输入校验**：所有用户输入都经过严格校验，防止注入攻击
4. **数据备份**：定期备份数据库和向量索引

## 常见问题

### Q: 为什么复现功能不可用？
A: 复现功能需要Docker环境支持，请确保Docker已正确安装并启动，并且当前用户有Docker访问权限。

### Q: 支持国内的大模型吗？
A: 支持，只需修改 `OPENAI_BASE_URL` 为对应的API地址，如百度文心、阿里通义千问、讯飞星火等兼容OpenAI接口的服务。

### Q: PDF解析不准确怎么办？
A: 对于格式复杂的PDF，建议集成Grobid学术文档解析服务，可以显著提高解析准确率。

### Q: 如何处理大论文超过上下文限制？
A: 系统会自动截断长文本，优先保留重要部分。对于超长论文，可以实现分块解读和结果融合。

## 贡献指南

欢迎提交Issue和Pull Request！

1. Fork本仓库
2. 创建功能分支
3. 提交更改
4. 发起Pull Request

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交Issue或联系开发团队。
