from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas import PolicyCreate, PolicyUpdate
from app.services import audit_service, policy_service
from app.api.deps import get_current_user, require_perm

router = APIRouter(prefix="/api/policies", tags=["policies"])


@router.get("")
def list_policies(
    enabled: bool = None,
    user=Depends(require_perm("risk:policy:view")),
    db: Session = Depends(get_db),
):
    return policy_service.list_policies(db, enabled)


@router.post("")
def create(data: PolicyCreate, request: Request, user=Depends(require_perm("risk:policy:manage")), db: Session = Depends(get_db)):
    p = policy_service.create_policy(db, data, user.username)
    audit_service.write_log(db, user.username, "policy", "create", "RiskPolicy", p["id"], {"name": p["name"]}, request_id=getattr(request.state, "request_id", None))
    return p


@router.put("/{policy_id}")
def update(policy_id: int, data: PolicyUpdate, request: Request, user=Depends(require_perm("risk:policy:manage")), db: Session = Depends(get_db)):
    p = policy_service.update_policy(db, policy_id, data)
    if not p:
        raise HTTPException(status_code=404, detail="策略不存在")
    audit_service.write_log(db, user.username, "policy", "update", "RiskPolicy", policy_id, request_id=getattr(request.state, "request_id", None))
    return p


@router.post("/{policy_id}/toggle")
def toggle(policy_id: int, request: Request, user=Depends(require_perm("risk:policy:manage")), db: Session = Depends(get_db)):
    p = policy_service.get_policy(db, policy_id)
    if not p:
        raise HTTPException(status_code=404, detail="策略不存在")
    updated = policy_service.set_enabled(db, policy_id, not p.enabled)
    audit_service.write_log(db, user.username, "policy", "toggle", "RiskPolicy", policy_id, {"enabled": updated["enabled"]}, request_id=getattr(request.state, "request_id", None))
    return updated


@router.delete("/{policy_id}")
def delete(policy_id: int, request: Request, user=Depends(require_perm("risk:policy:manage")), db: Session = Depends(get_db)):
    ok = policy_service.delete_policy(db, policy_id)
    if not ok:
        raise HTTPException(status_code=404, detail="策略不存在")
    audit_service.write_log(db, user.username, "policy", "delete", "RiskPolicy", policy_id, request_id=getattr(request.state, "request_id", None))
    return {"ok": True}
