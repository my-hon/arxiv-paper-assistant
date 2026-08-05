"""API异常处理工具。

各接口原本都以相同的``try/except``结构把内部异常转换为HTTP 500响应，
这里统一为装饰器，避免重复的样板代码。
"""

import functools
from typing import Any, Callable, TypeVar

from fastapi import HTTPException
from loguru import logger

F = TypeVar("F", bound=Callable[..., Any])


def handle_api_errors(message: str) -> Callable[[F], F]:
    """将未捕获的异常转换为HTTP 500响应的装饰器。

    HTTPException会原样抛出，保留接口自身定义的状态码和错误详情。

    Args:
        message: 错误前缀文案，如"搜索失败"。
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"{message}: {str(e)}")
                raise HTTPException(status_code=500, detail=f"{message}: {str(e)}")

        return wrapper  # type: ignore[return-value]

    return decorator
