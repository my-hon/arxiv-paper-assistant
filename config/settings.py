"""系统配置文件，使用Pydantic Settings管理环境变量。

所有配置项均可通过环境变量覆盖，支持从.env文件加载配置。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """系统配置类，定义所有可配置的参数。

    所有参数均可通过环境变量覆盖，默认值适用于开发环境。
    生产环境请务必修改敏感配置项，如SECRET_KEY、OPENAI_API_KEY等。
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # 服务配置
    HOST: str = "0.0.0.0"
    """服务绑定的主机地址，默认绑定所有网卡"""
    PORT: int = 8000
    """服务监听的端口，默认8000"""
    DEBUG: bool = True
    """是否开启调试模式，生产环境请设置为False"""

    # 大模型配置
    OPENAI_API_KEY: str = ""
    """OpenAI API密钥，调用大模型服务必需"""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    """OpenAI API基础URL，可配置为兼容OpenAI协议的其他服务"""
    MODEL_NAME: str = "gpt-3.5-turbo-1106"
    """默认使用的大模型名称"""
    MAX_TOKENS: int = 4000
    """大模型单次调用的最大token数"""
    TEMPERATURE: float = 0.1
    """大模型生成的温度参数，值越小越确定，越大越有创造性"""

    # 爬虫配置
    CRAWL_RATE_LIMIT: float = 1.0
    """爬虫请求间隔时间（秒），避免请求过于频繁"""
    CRAWL_MAX_RETRIES: int = 3
    """爬虫请求失败的最大重试次数"""
    PROXY_URL: Optional[str] = None
    """代理服务器URL，用于需要代理访问外网的场景"""

    # 数据库配置
    DATABASE_URL: str = "sqlite:///./paper_system.db"
    """关系数据库连接URL，默认使用SQLite"""
    CHROMA_DB_PATH: str = "./chroma_db"
    """Chroma向量数据库本地存储路径，仅在使用本地模式时有效"""
    CHROMA_DB_HOST: Optional[str] = None
    """远程Chroma服务主机地址，配置后使用远程模式"""
    CHROMA_DB_PORT: Optional[int] = None
    """远程Chroma服务端口"""
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    """文本嵌入模型名称，用于生成向量表示"""

    # 复现环境配置
    DOCKER_SOCKET: str = "unix:///var/run/docker.sock"
    """Docker守护进程套接字路径，用于容器化复现环境"""
    SANDBOX_MEMORY_LIMIT: str = "2g"
    """复现沙箱的内存限制"""
    SANDBOX_CPU_LIMIT: float = 2.0
    """复现沙箱的CPU核心限制"""
    SANDBOX_TIMEOUT: int = 300
    """复现任务的超时时间（秒）"""

    # 存储配置
    STORAGE_PATH: str = "./storage"
    """根存储目录，所有文件默认存储在此目录下"""
    PDF_STORAGE_PATH: str = "./storage/pdfs"
    """论文PDF文件存储路径"""
    SCRIPT_STORAGE_PATH: str = "./storage/scripts"
    """复现脚本存储路径"""
    REPORT_STORAGE_PATH: str = "./storage/reports"
    """复现报告存储路径"""


settings = Settings()
