from typing import Any, List, Optional

from pydantic import BaseModel, Field


# ---------------- 认证 ----------------
class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    display_name: Optional[str] = None
    department: Optional[str] = None
    status: str
    is_superadmin: bool


# ---------------- 策略 ----------------
class PolicyCondition(BaseModel):
    field: str
    op: str  # eq ne gt gte lt lte in not_in contains regex exists
    value: Any = None


class PolicyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    event_type: str = "ALL"
    enabled: bool = True
    priority: int = 100
    conditions: List[PolicyCondition]
    action: str = "WARN"
    risk_score: int = 50


class PolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    conditions: Optional[List[PolicyCondition]] = None
    action: Optional[str] = None
    risk_score: Optional[int] = None


# ---------------- 决策 ----------------
class EvaluateRequest(BaseModel):
    event_type: str
    payload: dict = Field(default_factory=dict)
    actor: Optional[str] = None
    ip: Optional[str] = None


class EvaluateResponse(BaseModel):
    decision: str
    score: int
    triggered_rules: list
    alerts: list
    blacklisted: bool


# ---------------- 黑白名单 ----------------
class BlacklistCreate(BaseModel):
    list_type: str = "BLACK"  # BLACK / WHITE
    entity_type: str  # IP / USER / DEPARTMENT
    value: str
    reason: Optional[str] = None
    expires_at: Optional[str] = None  # ISO 字符串，可空


# ---------------- 通用 ----------------
class MessageOut(BaseModel):
    ok: bool = True
    message: str = ""


# ---------------- 生产质量 ----------------
class BatchCreate(BaseModel):
    batch_no: str
    product_line: str
    product_name: Optional[str] = None
    plan_qty: int = 0
    produced_qty: int = 0


class InspectionSubmit(BaseModel):
    batch_no: str
    product_line: Optional[str] = None  # 留空则沿用批次登记时的产线
    inspector: Optional[str] = None
    inspected_qty: int = 0
    failed_qty: int = 0
    sample_mode: str = "SAMPLE"  # FULL / SAMPLE
    is_leak: bool = False  # 漏检(未检就流转)
