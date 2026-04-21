# 配置说明

## 配置文件位置
配置文件默认位于：`~/.paper-assistant/.env`

首次运行 `paper-assistant init` 命令时会自动创建默认配置文件。

## 配置项说明

### OpenAI API配置
| 配置项 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `OPENAI_API_KEY` | OpenAI API密钥 | 无 | ✅ |
| `OPENAI_BASE_URL` | API接口地址，可配置为兼容OpenAI接口的其他服务 | `https://api.openai.com/v1` | ❌ |
| `MODEL_NAME` | 使用的大模型名称 | `gpt-3.5-turbo-1106` | ❌ |
| `EMBEDDING_MODEL_NAME` | 向量嵌入模型名称 | `all-MiniLM-L6-v2` | ❌ |

### 爬虫配置
| 配置项 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `CRAWL_RATE_LIMIT` | arXiv API请求间隔（秒），遵守爬虫协议 | `1.0` | ❌ |
| `CRAWL_TIMEOUT` | 爬取请求超时时间（秒） | `30` | ❌ |

### 存储配置
| 配置项 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `STORAGE_PATH` | 数据存储目录，包括PDF、复现脚本、报告等 | `~/.paper-assistant/storage` | ❌ |
| `CHROMA_DB_PATH` | Chroma向量数据库存储路径 | `~/.paper-assistant/chroma_db` | ❌ |
| `LOG_PATH` | 日志文件存储路径 | `~/.paper-assistant/logs` | ❌ |

### 复现环境配置
| 配置项 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `SANDBOX_TIMEOUT` | 复现任务执行超时时间（秒） | `300` | ❌ |
| `SANDBOX_MEMORY_LIMIT` | Docker沙箱内存限制 | `4g` | ❌ |

## 配置示例
```env
# OpenAI API配置
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4-turbo-preview
EMBEDDING_MODEL_NAME=text-embedding-3-small

# 爬虫配置
CRAWL_RATE_LIMIT=2.0
CRAWL_TIMEOUT=60

# 自定义存储路径
STORAGE_PATH=/data/paper-assistant/storage
CHROMA_DB_PATH=/data/paper-assistant/chroma_db
LOG_PATH=/data/paper-assistant/logs

# 复现配置
SANDBOX_TIMEOUT=600
SANDBOX_MEMORY_LIMIT=8g
```

## 多环境支持
你可以通过环境变量覆盖配置文件中的设置：
```bash
# 临时使用其他API密钥
export OPENAI_API_KEY=sk-yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
paper-assistant search "machine learning"
```

## 兼容国内大模型
本工具兼容所有支持OpenAI接口格式的大模型服务：

### 百度文心一言
```env
OPENAI_BASE_URL=https://qianfan.baidubce.com/v2
MODEL_NAME=ERNIE-4.0-8K
```

### 阿里通义千问
```env
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen-max
```

### 讯飞星火
```env
OPENAI_BASE_URL=https://spark-api.xf-yun.com/v3.5
MODEL_NAME=generalv3.5
```

### 智谱AI
```env
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
MODEL_NAME=glm-4
```

## 配置验证
运行 `paper-assistant config` 命令可以查看当前生效的配置，敏感信息会被自动隐藏。
