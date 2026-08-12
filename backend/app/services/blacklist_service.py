from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.risk import BlacklistEntry
from app.utils.serialize import iso


def _now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def is_blocked(db: Session, entity_type: str, value: str) -> bool:
    rows = (
        db.query(BlacklistEntry)
        .filter(
            BlacklistEntry.list_type == "BLACK",
            BlacklistEntry.entity_type == entity_type,
            BlacklistEntry.value == value,
            BlacklistEntry.enabled == True,  # noqa: E712
        )
        .all()
    )
    now = _now_naive()
    return any(e.expires_at is None or e.expires_at >= now for e in rows)


def is_whitelisted(db: Session, entity_type: str, value: str) -> bool:
    rows = (
        db.query(BlacklistEntry)
        .filter(
            BlacklistEntry.list_type == "WHITE",
            BlacklistEntry.entity_type == entity_type,
            BlacklistEntry.value == value,
            BlacklistEntry.enabled == True,  # noqa: E712
        )
        .all()
    )
    now = _now_naive()
    return any(e.expires_at is None or e.expires_at >= now for e in rows)


def add_policy_blacklist(db: Session, payload: dict, actor, ip, policy, request_id: str):
    """策略命中 ADD_BLACKLIST 时，将 IP 或 USER 自动拉黑。"""
    target = ip or (payload or {}).get("ip")
    etype = "IP"
    val = target
    if not val:
        val = actor or (payload or {}).get("username") or (payload or {}).get("user")
        etype = "USER"
    if not val:
        return
    existing = (
        db.query(BlacklistEntry)
        .filter(
            BlacklistEntry.list_type == "BLACK",
            BlacklistEntry.entity_type == etype,
            BlacklistEntry.value == val,
        )
        .first()
    )
    if existing:
        return
    entry = BlacklistEntry(
        list_type="BLACK",
        entity_type=etype,
        value=val,
        reason=f"策略[{policy.name}]自动拉黑",
        source="POLICY",
        created_by="system",
    )
    db.add(entry)
    db.commit()


def list_entries(db: Session, list_type=None, entity_type=None, enabled=None):
    q = db.query(BlacklistEntry)
    if list_type:
        q = q.filter(BlacklistEntry.list_type == list_type)
    if entity_type:
        q = q.filter(BlacklistEntry.entity_type == entity_type)
    if enabled is not None:
        q = q.filter(BlacklistEntry.enabled == enabled)
    rows = q.order_by(BlacklistEntry.created_at.desc()).all()
    return [_serialize(e) for e in rows]


def create_entry(db: Session, data, user):
    expires_at = None
    if data.expires_at:
        try:
            expires_at = datetime.fromisoformat(data.expires_at)
        except Exception:
            expires_at = None
    entry = BlacklistEntry(
        list_type=data.list_type,
        entity_type=data.entity_type,
        value=data.value,
        reason=data.reason,
        expires_at=expires_at,
        source="MANUAL",
        created_by=user.username,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _serialize(entry)


def delete_entry(db: Session, entry_id: int):
    e = db.query(BlacklistEntry).filter(BlacklistEntry.id == entry_id).first()
    if e:
        db.delete(e)
        db.commit()
    return e is not None


def _serialize(e: BlacklistEntry) -> dict:
    return {
        "id": e.id,
        "list_type": e.list_type,
        "entity_type": e.entity_type,
        "value": e.value,
        "reason": e.reason,
        "source": e.source,
        "expires_at": iso(e.expires_at),
        "enabled": e.enabled,
        "created_at": iso(e.created_at),
        "created_by": e.created_by,
    }
