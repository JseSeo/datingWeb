from fastapi import APIRouter
from app.api import auth, game, matching, me, reports, rounds, survey, verification

router = APIRouter()
router.include_router(auth.router)
router.include_router(me.router)
router.include_router(verification.router)
router.include_router(reports.router)
router.include_router(game.router)
router.include_router(rounds.router)
router.include_router(survey.router)
router.include_router(reports.admin_router)
router.include_router(rounds.admin_router)
router.include_router(matching.admin_router)
