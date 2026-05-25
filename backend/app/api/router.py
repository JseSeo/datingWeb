from fastapi import APIRouter
from app.api import auth, me, verification

router = APIRouter()
router.include_router(auth.router)
router.include_router(me.router)
router.include_router(verification.router)
