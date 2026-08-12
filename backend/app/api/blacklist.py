from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas import BlacklistCreate
from app.services import audit_service, blacklist_service
from app.api.deps import get_current_user, require_perm

router = APIRouter(prefix="/api/blacklist", tags=["blacklist"])


@router.get("")
def list_entries(
    list_type: str = None,
    entity_type: str = None,
    user=Depends(require_perm("risk:blacklist:view")),
    db: Session = Depends(get_db),
):
    return blacklist_service.list_entries(db, list_type, entity_type)


@router.post("")
def create(data: BlacklistCreate, request: Request, user=Depends(require_perm("risk:blacklist:manage")), db: Session = Depends(get_db)):
    e = blacklist_service.create_entry(db, data, user)
    audit_service.write_log(db, user.username, "blacklist", "create", "BlacklistEntry", e["id"], {"value": e["value"], "list_type": e["list_type"]}, request_id=getattr(request.state, "request_id", None))
    return e


@router.delete("/{entry_id}")
def delete(entry_id: int, request: Request, user=Depends(require_perm("risk:blacklist:manage")), db: Session = Depends(get_db)):
    ok = blacklist_service.delete_entry(db, entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="记录不存在")
    audit_service.write_log(db, user.username, "blacklist", "delete", "BlacklistEntry", entry_id, request_id=getattr(request.state, "request_id", None))
    return {"ok": True}
