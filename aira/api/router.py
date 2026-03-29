"""AIRA module: api/router.py"""

from fastapi import APIRouter

from api.audit import router as audit_router
from api.charts import router as charts_router
from api.health import router as health_router
from api.market_gpt import router as market_gpt_router
from api.orchestrator_routes import router as orchestrator_router
from api.portfolio import router as portfolio_router
from api.signals import router as signals_router
from api.user import router as user_router
from api.video_studio import router as video_studio_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(audit_router, prefix="/audit", tags=["audit"])
api_router.include_router(user_router, prefix="/user", tags=["user"])
api_router.include_router(orchestrator_router, prefix="/orchestrate", tags=["orchestrator"])
api_router.include_router(portfolio_router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(signals_router, prefix="/signals", tags=["signals"])
api_router.include_router(charts_router, prefix="/charts", tags=["charts"])
api_router.include_router(market_gpt_router, prefix="/market-gpt", tags=["market-gpt"])
api_router.include_router(video_studio_router, prefix="/video-studio", tags=["video-studio"])
