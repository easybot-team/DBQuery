from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from config import get_config  # 用延迟加载的配置

# 定义API Key请求头（前端需携带X-API-Key）
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="API Key（来自config.ini的api_keys配置）"
)

def verify_api_key(api_key: str = Depends(api_key_header)) -> str:
    """API Key校验依赖项（所有接口强制认证）"""
    config = get_config()  # 获取配置
    
    # 1. 检查是否携带API Key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供API Key！请在请求头添加 X-API-Key: 你的API Key",
            headers={"WWW-Authenticate": "X-API-Key"},
        )
    
    # 2. 检查API Key是否有效
    if api_key not in config.api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的API Key！请核对config.ini中的api_keys",
            headers={"WWW-Authenticate": "X-API-Key"},
        )
    
    return api_key
