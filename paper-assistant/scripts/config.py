"""
配置管理模块
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置"""

    # OpenAI配置
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    MODEL_NAME: str = "gpt-3.5-turbo-1106"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

    # 爬虫配置
    CRAWL_RATE_LIMIT: float = 1.0  # 请求间隔（秒）
    CRAWL_TIMEOUT: int = 30  # 超时时间（秒）

    # 存储配置
    STORAGE_PATH: Path = Path.home() / ".paper-assistant" / "storage"
    CHROMA_DB_PATH: Path = Path.home() / ".paper-assistant" / "chroma_db"
    LOG_PATH: Path = Path.home() / ".paper-assistant" / "logs"

    # 复现配置
    SANDBOX_TIMEOUT: int = 300  # 复现任务超时（秒）
    SANDBOX_MEMORY_LIMIT: str = "4g"  # 内存限制

    model_config = SettingsConfigDict(
        env_file=Path.home() / ".paper-assistant" / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# 全局配置实例
settings = Settings()


def init_config():
    """初始化配置目录和文件"""
    # 创建必要的目录
    settings.STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    settings.CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
    settings.LOG_PATH.mkdir(parents=True, exist_ok=True)
    (settings.STORAGE_PATH / "pdfs").mkdir(exist_ok=True)
    (settings.STORAGE_PATH / "scripts").mkdir(exist_ok=True)
    (settings.STORAGE_PATH / "reports").mkdir(exist_ok=True)

    # 创建默认.env文件
    env_file = Path.home() / ".paper-assistant" / ".env"
    if not env_file.exists():
        default_env = """# AI论文助手配置文件
# OpenAI API配置
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-3.5-turbo-1106
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2

# 爬虫配置
CRAWL_RATE_LIMIT=1.0
CRAWL_TIMEOUT=30

# 存储配置（默认在用户目录下）
# STORAGE_PATH=~/.paper-assistant/storage
# CHROMA_DB_PATH=~/.paper-assistant/chroma_db
# LOG_PATH=~/.paper-assistant/logs

# 复现配置
SANDBOX_TIMEOUT=300
SANDBOX_MEMORY_LIMIT=4g
"""
        env_file.write_text(default_env, encoding="utf-8")
        print(f"✅ 配置文件已创建：{env_file}")
        print("⚠️  请编辑配置文件，填入您的OpenAI API密钥")


def check_config() -> bool:
    """检查配置是否完整"""
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your_api_key_here":
        print("❌ OpenAI API密钥未配置")
        print("请编辑配置文件：", Path.home() / ".paper-assistant" / ".env")
        return False
    return True


def show_config():
    """显示当前配置（隐藏敏感信息）"""
    print("📋 当前配置：")
    print("-" * 50)
    print(f"API Base URL: {settings.OPENAI_BASE_URL}")
    print(f"Model Name: {settings.MODEL_NAME}")
    print(f"Embedding Model: {settings.EMBEDDING_MODEL_NAME}")
    print(
        f"API Key: {'*' * 8 + settings.OPENAI_API_KEY[-4:] if settings.OPENAI_API_KEY else '未配置'}"
    )
    print(f"Storage Path: {settings.STORAGE_PATH}")
    print(f"Chroma DB Path: {settings.CHROMA_DB_PATH}")
    print(f"Crawl Rate Limit: {settings.CRAWL_RATE_LIMIT}s/request")
    print(f"Sandbox Timeout: {settings.SANDBOX_TIMEOUT}s")
    print("-" * 50)
