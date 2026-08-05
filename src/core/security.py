"""API鉴权模块。

提供基于API Key的可选鉴权依赖。当 settings.API_KEY 为空时不启用鉴权，
保持向后兼容；配置后所有受保护的接口都需要在请求头 X-API-Key 中携带正确的密钥。
"""

import secrets

from fastapi import Header, HTTPException, status

from src.config.settings import settings


async def require_api_key(x_api_key: str = Header(default="")) -> None:
    """校验请求头中的API密钥。

    未配置 API_KEY 时直接放行；配置后使用常量时间比较校验，
    防止时序侧信道泄露密钥。

    Args:
        x_api_key: 请求头 X-API-Key 的值。

    Raises:
        HTTPException: 当启用鉴权且密钥缺失或不匹配时返回401。
    """
    if not settings.API_KEY:
        return

    if not x_api_key or not secrets.compare_digest(x_api_key, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或缺失的API密钥",
            headers={"WWW-Authenticate": "API-Key"},
        )
