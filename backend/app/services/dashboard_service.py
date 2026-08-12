from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.risk import BlacklistEntry, RiskEvent, RiskPolicy


def overview(db: Session) -> dict:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    day7 = now - timedelta(days=7)

    events = db.query(RiskEvent).all()
    total = len(events)
    blocked = sum(1 for e in events if e.decision == "BLOCK")
    warned = sum(1 for e in events if e.decision == "WARN")
    allowed = sum(1 for e in events if e.decision == "ALLOW")

    trend: dict = {}
    recent = [e for e in events if e.created_at and e.created_at >= day7]
    for e in recent:
        d = e.created_at.strftime("%m-%d")
        bucket = trend.setdefault(d, {"total": 0, "block": 0, "warn": 0, "allow": 0})
        bucket["total"] += 1
        bucket[e.decision.lower()] = bucket.get(e.decision.lower(), 0) + 1

    rule_counter: Counter = Counter()
    for e in events:
        for r in e.triggered_rule_ids or []:
            rule_counter[r] += 1
    top_rules = rule_counter.most_common(10)

    blocked_counter: Counter = Counter()
    for e in events:
        if e.decision == "BLOCK":
            blocked_counter[e.actor or e.ip or "-"] += 1
    top_blocked = blocked_counter.most_common(10)

    policies_total = db.query(RiskPolicy).count()
    policies_enabled = db.query(RiskPolicy).filter(RiskPolicy.enabled == True).count()  # noqa: E712
    black_total = (
        db.query(BlacklistEntry)
        .filter(BlacklistEntry.list_type == "BLACK", BlacklistEntry.enabled == True)  # noqa: E712
        .count()
    )

    return {
        "total": total,
        "blocked": blocked,
        "warned": warned,
        "allowed": allowed,
        "trend": trend,
        "top_rules": top_rules,
        "top_blocked": top_blocked,
        "policies_total": policies_total,
        "policies_enabled": policies_enabled,
        "black_total": black_total,
    }
