from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.base import get_db
from app.services import auth_service, rbac_service

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效或已过期")
    user = auth_service.get_user_by_username(db, payload.get("sub"))
    if not user or user.status != "ENABLED":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号不可用")
    request.state.user = user
    return user


def require_perm(code: str):
    def checker(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
        if user.is_superadmin:
            return user
        perms = rbac_service.get_user_permissions(db, user)
        if code not in perms:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"缺少权限：{code}")
        return user

    return checker
