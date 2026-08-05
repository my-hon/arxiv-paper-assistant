"""应用统一异常定义。

模块层抛出这些异常，由API层的全局异常处理器统一转换为HTTP响应，
避免错误被吞掉后只返回一个没有原因的失败结果。
"""


class AppError(Exception):
    """应用异常基类。

    Attributes:
        message: 面向调用方的错误描述。
        status_code: 对应的HTTP状态码。
    """

    status_code: int = 500

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(AppError):
    """请求的资源不存在。"""

    status_code = 404


class ValidationError(AppError):
    """请求参数或数据状态不满足要求。"""

    status_code = 400


class ExternalServiceError(AppError):
    """外部服务（arXiv、大模型等）调用失败。"""

    status_code = 502


class CrawlerError(AppError):
    """论文爬取/解析失败。"""

    status_code = 502


class StorageError(AppError):
    """本地存储或数据库操作失败。"""

    status_code = 500


class VectorStoreError(AppError):
    """向量存储操作失败。"""

    status_code = 500


class InterpretationError(AppError):
    """论文解读失败。"""

    status_code = 500


class ReproductionError(AppError):
    """复现脚本生成或执行失败。"""

    status_code = 500
