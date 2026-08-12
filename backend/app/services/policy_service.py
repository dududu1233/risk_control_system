from sqlalchemy.orm import Session

from app.models.risk import RiskPolicy
from app.schemas import PolicyCreate, PolicyUpdate
from app.utils.serialize import iso


def list_policies(db: Session, enabled=None):
    q = db.query(RiskPolicy)
    if enabled is not None:
        q = q.filter(RiskPolicy.enabled == enabled)
    rows = q.order_by(RiskPolicy.priority.asc()).all()
    return [_serialize(p) for p in rows]


def get_policy(db: Session, policy_id: int):
    return db.query(RiskPolicy).filter(RiskPolicy.id == policy_id).first()


def create_policy(db: Session, data: PolicyCreate, username: str):
    p = RiskPolicy(
        name=data.name,
        description=data.description,
        event_type=data.event_type,
        enabled=data.enabled,
        priority=data.priority,
        conditions=[c.dict() for c in data.conditions],
        action=data.action,
        risk_score=data.risk_score,
        created_by=username,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _serialize(p)


def update_policy(db: Session, policy_id: int, data: PolicyUpdate):
    p = get_policy(db, policy_id)
    if not p:
        return None
    for k, v in data.dict(exclude_unset=True).items():
        if k == "conditions" and v is not None:
            v = [c.dict() for c in v]
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return _serialize(p)


def delete_policy(db: Session, policy_id: int) -> bool:
    p = get_policy(db, policy_id)
    if not p:
        return False
    db.delete(p)
    db.commit()
    return True


def set_enabled(db: Session, policy_id: int, enabled: bool):
    p = get_policy(db, policy_id)
    if not p:
        return None
    p.enabled = enabled
    db.commit()
    db.refresh(p)
    return _serialize(p)


def _serialize(p: RiskPolicy) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "event_type": p.event_type,
        "enabled": p.enabled,
        "priority": p.priority,
        "conditions": p.conditions,
        "action": p.action,
        "risk_score": p.risk_score,
        "created_at": iso(p.created_at),
        "updated_at": iso(p.updated_at),
        "created_by": p.created_by,
    }
