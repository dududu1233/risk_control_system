import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.risk import RiskPolicy
from app.services import blacklist_service, event_service

# 条件操作符实现
OPS = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "gt": lambda a, b: a is not None and a > b,
    "gte": lambda a, b: a is not None and a >= b,
    "lt": lambda a, b: a is not None and a < b,
    "lte": lambda a, b: a is not None and a <= b,
    "in": lambda a, b: a in (b or []),
    "not_in": lambda a, b: a not in (b or []),
    "contains": lambda a, b: isinstance(a, str) and b in a,
    "regex": lambda a, b: a is not None and re.search(str(b), str(a)) is not None,
    "exists": lambda a, b: (a is not None) == bool(b),
}


def _get_field(payload: dict, field: str):
    """支持点号路径，例如 payload.department 或 payload.user.ip。"""
    cur = payload or {}
    for part in field.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def evaluate_condition(cond: dict, payload: dict) -> bool:
    op = cond.get("op")
    field = cond.get("field")
    value = cond.get("value")
    actual = _get_field(payload, field) if field else None
    fn = OPS.get(op)
    if not fn:
        return False
    try:
        return bool(fn(actual, value))
    except Exception:
        return False


# 决策动作严重度：数值越大处置越重
SEVERITY = {"ALLOW": 0, "WARN": 1, "ALERT": 2, "BLOCK": 3, "ADD_BLACKLIST": 3}


def evaluate(
    db: Session,
    event_type: str,
    payload: dict,
    actor=None,
    ip=None,
) -> dict:
    request_id = uuid.uuid4().hex[:16]
    triggered = []
    score = 0
    alerts = []
    decision = "ALLOW"

    policies = (
        db.query(RiskPolicy)
        .filter_by(enabled=True)
        .order_by(RiskPolicy.priority.asc())
        .all()
    )

    for p in policies:
        if p.event_type not in ("ALL", event_type):
            continue
        conds = p.conditions or []
        if not conds:
            continue
        if all(evaluate_condition(c, payload) for c in conds):
            triggered.append(
                {"id": p.id, "name": p.name, "action": p.action, "score": p.risk_score}
            )
            score += p.risk_score or 0
            act = p.action
            if act == "ADD_BLACKLIST":
                blacklist_service.add_policy_blacklist(db, payload, actor, ip, p, request_id)
                act = "BLOCK"
            # 取严重度更高的动作作为当前决策
            if SEVERITY.get(act, 0) > SEVERITY.get(decision, 0):
                decision = act

    # 黑白名单检查
    blacklisted = False
    subject_ip = ip or (payload or {}).get("ip")
    subject_user = actor or (payload or {}).get("username") or (payload or {}).get("user")
    if subject_ip and blacklist_service.is_blocked(db, "IP", subject_ip):
        blacklisted = True
    if subject_user and blacklist_service.is_blocked(db, "USER", subject_user):
        blacklisted = True
    if blacklisted:
        decision = "BLOCK"
        alerts.append("命中黑名单")

    # 评分阈值
    if decision == "ALLOW":
        if score >= settings.RISK_BLOCK_THRESHOLD:
            decision = "BLOCK"
        elif score >= settings.RISK_WARN_THRESHOLD:
            decision = "WARN"

    # 白名单豁免
    whitelisted = False
    if subject_ip and blacklist_service.is_whitelisted(db, "IP", subject_ip):
        whitelisted = True
    if subject_user and blacklist_service.is_whitelisted(db, "USER", subject_user):
        whitelisted = True
    if whitelisted:
        decision = "ALLOW"
        alerts.append("命中白名单豁免")

    if score > 0 or triggered or blacklisted or whitelisted:
        alerts.append(f"风险评分 {score}")

    event_service.record_event(
        db, event_type, payload, decision, score, triggered, alerts, request_id, actor, ip
    )

    return {
        "decision": decision,
        "score": score,
        "triggered_rules": triggered,
        "alerts": alerts,
        "blacklisted": blacklisted,
        "request_id": request_id,
    }
