from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.services import dashboard_service
from app.api.deps import get_current_user, require_perm

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview")
def overview(user=Depends(require_perm("dashboard:view")), db: Session = Depends(get_db)):
    return dashboard_service.overview(db)
