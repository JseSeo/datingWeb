from fastapi import APIRouter
from app.api import auth, game, me, reports, verification

router = APIRouter()
router.include_router(auth.router)
router.include_router(me.router)
router.include_router(verification.router)
router.include_router(reports.router)
router.include_router(game.router)
