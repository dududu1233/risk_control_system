from sqlalchemy.orm import Session

from app.models.risk import OperationLog
from app.utils.serialize import iso


def write_log(
    db: Session,
    username: str,
    module: str,
    action: str,
    object_type=None,
    object_id=None,
    detail=None,
    request_id=None,
    ip=None,
):
    log = OperationLog(
        username=username,
        module=module,
        action=action,
        object_type=object_type,
        object_id=str(object_id) if object_id is not None else None,
        detail=detail,
        request_id=request_id,
        ip=ip,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return _serialize(log)


def list_logs(db: Session, module=None, limit: int = 200):
    q = db.query(OperationLog)
    if module:
        q = q.filter(OperationLog.module == module)
    rows = q.order_by(OperationLog.created_at.desc()).limit(limit).all()
    return [_serialize(l) for l in rows]


def _serialize(l: OperationLog) -> dict:
    return {
        "id": l.id,
        "username": l.username,
        "module": l.module,
        "action": l.action,
        "object_type": l.object_type,
        "object_id": l.object_id,
        "detail": l.detail,
        "request_id": l.request_id,
        "ip": l.ip,
        "created_at": iso(l.created_at),
    }
