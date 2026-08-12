from fastapi import APIRouter

from app.api import auth, policy, risk, blacklist, dashboard, audit, quality

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(policy.router)
api_router.include_router(risk.router)
api_router.include_router(blacklist.router)
api_router.include_router(dashboard.router)
api_router.include_router(audit.router)
api_router.include_router(quality.router)
