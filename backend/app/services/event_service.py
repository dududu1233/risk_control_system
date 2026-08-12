from sqlalchemy.orm import Session

from app.models.risk import RiskEvent
from app.utils.serialize import iso


def record_event(
    db: Session,
    event_type: str,
    payload,
    decision: str,
    score: int,
    triggered,
    alerts,
    request_id: str,
    actor,
    ip,
) -> dict:
    e = RiskEvent(
        event_type=event_type,
        payload=payload,
        decision=decision,
        score=score,
        triggered_rule_ids=[t.get("name") for t in triggered],
        alerts=alerts,
        request_id=request_id,
        actor=actor,
        ip=ip,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return _serialize(e)


def list_events(db: Session, event_type=None, decision=None, limit: int = 200):
    q = db.query(RiskEvent)
    if event_type:
        q = q.filter(RiskEvent.event_type == event_type)
    if decision:
        q = q.filter(RiskEvent.decision == decision)
    rows = q.order_by(RiskEvent.created_at.desc()).limit(limit).all()
    return [_serialize(e) for e in rows]


def _serialize(e: RiskEvent) -> dict:
    return {
        "id": e.id,
        "event_type": e.event_type,
        "payload": e.payload,
        "decision": e.decision,
        "score": e.score,
        "triggered_rule_ids": e.triggered_rule_ids,
        "alerts": e.alerts,
        "request_id": e.request_id,
        "actor": e.actor,
        "ip": e.ip,
        "created_at": iso(e.created_at),
    }
