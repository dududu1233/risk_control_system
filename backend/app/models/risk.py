from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, Boolean

from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


class RiskPolicy(Base):
    """风控策略 / 规则。conditions 为条件列表（AND 关系），命中后累计 risk_score 并执行 action。"""

    __tablename__ = "risk_policies"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    event_type = Column(String(64), nullable=False, default="ALL")  # LOGIN / KNOWLEDGE_ACCESS / EXPORT / IMPORT / ALL
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=100)  # 越小越先评估
    conditions = Column(JSON, nullable=False)
    action = Column(String(32), default="WARN")  # ALLOW / WARN / BLOCK / ADD_BLACKLIST
    risk_score = Column(Integer, default=50)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    created_by = Column(String(64))


class RiskEvent(Base):
    """一次风控决策记录（对外暴露的「风险事件」）。"""

    __tablename__ = "risk_events"

    id = Column(Integer, primary_key=True)
    event_type = Column(String(64), nullable=False)
    payload = Column(JSON)
    decision = Column(String(16))  # ALLOW / WARN / BLOCK
    score = Column(Integer, default=0)
    triggered_rule_ids = Column(JSON)
    alerts = Column(JSON)
    request_id = Column(String(64))
    actor = Column(String(64))  # 触发主体（用户名 / 业务方）
    ip = Column(String(64))
    created_at = Column(DateTime, default=utcnow)


class BlacklistEntry(Base):
    """黑白名单。list_type=BLACK 命中即阻断；WHITE 为白名单豁免。"""

    __tablename__ = "blacklist_entries"

    id = Column(Integer, primary_key=True)
    list_type = Column(String(16), default="BLACK")  # BLACK / WHITE
    entity_type = Column(String(32), nullable=False)  # IP / USER / DEPARTMENT
    value = Column(String(255), nullable=False)
    reason = Column(Text)
    source = Column(String(32), default="MANUAL")  # MANUAL / POLICY
    expires_at = Column(DateTime)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    created_by = Column(String(64))


class OperationLog(Base):
    """操作审计日志。"""

    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True)
    username = Column(String(64))
    module = Column(String(64))
    action = Column(String(64))
    object_type = Column(String(64))
    object_id = Column(String(64))
    detail = Column(JSON)
    request_id = Column(String(64))
    ip = Column(String(64))
    created_at = Column(DateTime, default=utcnow)
