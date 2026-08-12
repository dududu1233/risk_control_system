from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


class ProductionBatch(Base):
    """生产批次台账。每批产出登记一次，质检后状态更新为 已检/阻断。"""

    __tablename__ = "production_batches"

    id = Column(Integer, primary_key=True)
    batch_no = Column(String(64), unique=True, index=True, nullable=False)
    product_line = Column(String(128), nullable=False)  # 产线
    product_name = Column(String(128))  # 产品/工序名
    plan_qty = Column(Integer, default=0)  # 计划产量
    produced_qty = Column(Integer, default=0)  # 实际产出
    status = Column(String(16), default="PENDING")  # PENDING / INSPECTED / BLOCKED / RELEASED
    created_by = Column(String(64))
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class InspectionRecord(Base):
    """质检/检测记录。每次对该批产出做检测即落一条，并触发风控决策。"""

    __tablename__ = "inspection_records"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("production_batches.id"), nullable=True)
    batch_no = Column(String(64), nullable=False, index=True)
    product_line = Column(String(128))
    inspector = Column(String(64))  # 质检员
    inspected_qty = Column(Integer, default=0)  # 抽检/全检数量
    failed_qty = Column(Integer, default=0)  # 不合格数量
    defect_rate = Column(Float, default=0.0)  # 不合格率(%) = failed/inspected*100
    sample_mode = Column(String(16), default="SAMPLE")  # FULL / SAMPLE
    is_leak = Column(Boolean, default=False)  # 是否漏检(未检就流转)
    consecutive_failed = Column(Integer, default=0)  # 同产线连续不合格批数(含本批)
    result = Column(String(16), default="PASS")  # PASS / WARN / FAIL
    risk_decision = Column(String(16))  # ALLOW / WARN / ALERT / BLOCK
    risk_score = Column(Integer, default=0)
    triggered_rules = Column(JSON)  # 命中的策略名列表
    request_id = Column(String(64))
    created_at = Column(DateTime, default=utcnow)
