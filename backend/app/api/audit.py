from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.services import audit_service
from app.api.deps import get_current_user, require_perm

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/logs")
def list_logs(module: str = None, user=Depends(require_perm("audit:view")), db: Session = Depends(get_db)):
    return audit_service.list_logs(db, module)
