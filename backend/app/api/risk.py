from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas import EvaluateRequest, EvaluateResponse
from app.services import event_service, risk_engine_service
from app.api.deps import get_current_user, require_perm

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate(req: EvaluateRequest, request: Request, user=Depends(require_perm("risk:event:evaluate")), db: Session = Depends(get_db)):
    if not req.event_type:
        raise HTTPException(status_code=400, detail="event_type 不能为空")
    return risk_engine_service.evaluate(
        db, req.event_type, req.payload or {}, actor=req.actor, ip=req.ip
    )


@router.get("/events")
def list_events(
    event_type: str = None,
    decision: str = None,
    user=Depends(require_perm("risk:event:view")),
    db: Session = Depends(get_db),
):
    return event_service.list_events(db, event_type, decision)
