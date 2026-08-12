from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas import LoginRequest
from app.services import auth_service, rbac_service
from app.core.security import create_access_token
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    perms = rbac_service.get_user_permissions(db, user)
    token = create_access_token(user.username)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "department": user.department,
            "status": user.status,
            "is_superadmin": user.is_superadmin,
            "permissions": list(perms),
        },
    }


@router.get("/me")
def me(user=Depends(get_current_user), db: Session = Depends(get_db)):
    perms = rbac_service.get_user_permissions(db, user)
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "department": user.department,
        "status": user.status,
        "is_superadmin": user.is_superadmin,
        "permissions": list(perms),
    }
