from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.quality import InspectionRecord, ProductionBatch
from app.services import risk_engine_service


def utcnow():
    return datetime.now(timezone.utc)


# ---------------- 序列化 ----------------
def serialize_batch(b: ProductionBatch) -> dict:
    return {
        "id": b.id,
        "batch_no": b.batch_no,
        "product_line": b.product_line,
        "product_name": b.product_name,
        "plan_qty": b.plan_qty,
        "produced_qty": b.produced_qty,
        "status": b.status,
        "created_by": b.created_by,
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "updated_at": b.updated_at.isoformat() if b.updated_at else None,
    }


def serialize_inspection(r: InspectionRecord) -> dict:
    return {
        "id": r.id,
        "batch_id": r.batch_id,
        "batch_no": r.batch_no,
        "product_line": r.product_line,
        "inspector": r.inspector,
        "inspected_qty": r.inspected_qty,
        "failed_qty": r.failed_qty,
        "defect_rate": r.defect_rate,
        "sample_mode": r.sample_mode,
        "is_leak": r.is_leak,
        "consecutive_failed": r.consecutive_failed,
        "result": r.result,
        "risk_decision": r.risk_decision,
        "risk_score": r.risk_score,
        "triggered_rules": r.triggered_rules or [],
        "request_id": r.request_id,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


# ---------------- 批次 ----------------
def create_batch(db: Session, data, user) -> dict:
    b = ProductionBatch(
        batch_no=data.batch_no,
        product_line=data.product_line,
        product_name=data.product_name,
        plan_qty=data.plan_qty,
        produced_qty=data.produced_qty,
        status="PENDING",
        created_by=user.username,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return serialize_batch(b)


def list_batches(db: Session, product_line=None, status=None, limit=200):
    q = db.query(ProductionBatch)
    if product_line:
        q = q.filter(ProductionBatch.product_line == product_line)
    if status:
        q = q.filter(ProductionBatch.status == status)
    rows = q.order_by(ProductionBatch.id.desc()).limit(limit).all()
    return [serialize_batch(r) for r in rows]


# ---------------- 质检 ----------------
def _compute_consecutive_failed(db: Session, product_line: str, current_failed: bool) -> int:
    """统计该产线此前连续出现质量问题的批数(决策非 ALLOW)，再加上当前这批(若有问题)。"""
    recs = (
        db.query(InspectionRecord)
        .filter(InspectionRecord.product_line == product_line)
        .order_by(InspectionRecord.id.desc())
        .all()
    )
    prior = 0
    for r in recs:
        if r.risk_decision and r.risk_decision != "ALLOW":
            prior += 1
        else:
            break
    return prior + (1 if current_failed else 0)


def create_inspection(db: Session, data, user):
    batch = db.query(ProductionBatch).filter(ProductionBatch.batch_no == data.batch_no).first()
    product_line = data.product_line or (batch.product_line if batch else None)

    inspected_qty = data.inspected_qty or 0
    failed_qty = data.failed_qty or 0
    # 漏检：未抽检或显式标记
    is_leak = bool(data.is_leak) or inspected_qty <= 0
    # 漏检(未抽检)时不合格率无意义，记为 0，避免误触「不合格率超阈值」规则；
    # 漏检由专门的「整批漏检告警」规则按 is_leak 判定为 ALERT。
    defect_rate = round(failed_qty / inspected_qty * 100, 2) if inspected_qty > 0 else 0.0
    current_failed = (failed_qty > 0) or is_leak
    consecutive_failed = _compute_consecutive_failed(db, product_line, current_failed)

    payload = {
        "batch_no": data.batch_no,
        "product_line": product_line,
        "inspected_qty": inspected_qty,
        "failed_qty": failed_qty,
        "defect_rate": defect_rate,
        "is_leak": is_leak,
        "sample_mode": data.sample_mode or "SAMPLE",
        "consecutive_failed": consecutive_failed,
        "inspector": data.inspector,
    }

    result = risk_engine_service.evaluate(
        db, "PRODUCTION_INSPECTION", payload, actor=data.inspector, ip=None
    )
    decision = result["decision"]
    rec_result = "PASS" if decision in ("ALLOW",) else ("FAIL" if decision == "BLOCK" else "WARN")

    rec = InspectionRecord(
        batch_id=batch.id if batch else None,
        batch_no=data.batch_no,
        product_line=product_line,
        inspector=data.inspector,
        inspected_qty=inspected_qty,
        failed_qty=failed_qty,
        defect_rate=defect_rate,
        sample_mode=data.sample_mode or "SAMPLE",
        is_leak=is_leak,
        consecutive_failed=consecutive_failed,
        result=rec_result,
        risk_decision=decision,
        risk_score=result["score"],
        triggered_rules=[t["name"] for t in result["triggered_rules"]],
        request_id=result.get("request_id"),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    # 回写批次状态
    if batch:
        if decision == "BLOCK":
            batch.status = "BLOCKED"
        elif decision == "ALERT":
            batch.status = "PENDING"  # 漏检等告警情形，仍需补检
        else:
            batch.status = "INSPECTED"
        batch.updated_at = utcnow()
        db.commit()

    return serialize_inspection(rec), result


def list_inspections(db: Session, batch_no=None, limit=200):
    q = db.query(InspectionRecord)
    if batch_no:
        q = q.filter(InspectionRecord.batch_no == batch_no)
    rows = q.order_by(InspectionRecord.id.desc()).limit(limit).all()
    return [serialize_inspection(r) for r in rows]


# ---------------- 统计 ----------------
def quality_stats(db: Session) -> dict:
    def count(model, **filters):
        q = db.query(model)
        for k, v in filters.items():
            q = q.filter(getattr(model, k) == v)
        return q.count()

    return {
        "total_batches": count(ProductionBatch),
        "pending": count(ProductionBatch, status="PENDING"),
        "inspected": count(ProductionBatch, status="INSPECTED"),
        "blocked": count(ProductionBatch, status="BLOCKED"),
        "total_inspections": count(InspectionRecord),
        "insp_block": count(InspectionRecord, risk_decision="BLOCK"),
        "insp_warn": count(InspectionRecord, risk_decision="WARN"),
        "insp_alert": count(InspectionRecord, risk_decision="ALERT"),
        "insp_pass": count(InspectionRecord, risk_decision="ALLOW"),
    }
