from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.quality import ProductionBatch
from app.schemas import BatchCreate, InspectionSubmit
from app.services import audit_service, quality_service
from app.api.deps import get_current_user, require_perm

router = APIRouter(prefix="/api/quality", tags=["quality"])


@router.post("/batches")
def create_batch(
    data: BatchCreate, request: Request,
    user=Depends(require_perm("quality:manage")), db: Session = Depends(get_db),
):
    dup = db.query(ProductionBatch).filter_by(batch_no=data.batch_no).first()
    if dup:
        raise HTTPException(status_code=400, detail="批次号已存在")
    b = quality_service.create_batch(db, data, user)
    audit_service.write_log(
        db, user.username, "quality", "create_batch", "ProductionBatch", b["id"],
        {"batch_no": b["batch_no"]}, request_id=getattr(request.state, "request_id", None),
    )
    return b


@router.get("/batches")
def list_batches(
    product_line: str = None, status: str = None,
    user=Depends(require_perm("quality:view")), db: Session = Depends(get_db),
):
    return quality_service.list_batches(db, product_line, status)


@router.post("/inspections")
def submit_inspection(
    data: InspectionSubmit, request: Request,
    user=Depends(require_perm("quality:manage")), db: Session = Depends(get_db),
):
    rec, result = quality_service.create_inspection(db, data, user)
    audit_service.write_log(
        db, user.username, "quality", "inspect", "InspectionRecord", rec["id"],
        {"batch_no": rec["batch_no"], "decision": rec["risk_decision"]},
        request_id=getattr(request.state, "request_id", None),
    )
    return {"record": rec, "decision": result["decision"], "score": result["score"],
            "triggered_rules": result["triggered_rules"], "alerts": result["alerts"]}


@router.get("/inspections")
def list_inspections(
    batch_no: str = None,
    user=Depends(require_perm("quality:view")), db: Session = Depends(get_db),
):
    return quality_service.list_inspections(db, batch_no)


@router.get("/stats")
def stats(user=Depends(require_perm("quality:view")), db: Session = Depends(get_db)):
    return quality_service.quality_stats(db)
