"""
FastAPI 公共依赖模块
提供当前用户解析等依赖注入
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from common.security import decode_token
from common.repositories import user_repo
from config import SECRET_KEY, ALGORITHM


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    """获取当前登录用户"""
    try:
        payload = decode_token(token, SECRET_KEY, ALGORITHM)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌")
        user_id = int(user_id)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌")

    user = user_repo.get_by_id(user_id)
    if not user or user.get("disabled"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户已禁用")
    return user
