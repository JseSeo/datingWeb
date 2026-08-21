from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.survey import SurveyCatalogOut
from app.survey.catalog import FACE_ANY_ID, FACE_TYPES, QUESTIONS

router = APIRouter(prefix="/survey", tags=["survey"])


@router.get("/questions", response_model=SurveyCatalogOut)
def get_catalog(_: User = Depends(get_current_user)):
    """설문 문항 카탈로그. 프론트는 이걸 받아 설문 화면을 렌더한다.

    로그인을 요구하는 이유: 문항 전체가 공개되면 서비스 설문 설계가 그대로 노출된다.
    설문 화면 자체도 active 유저만 들어오므로 접근 범위가 어긋나지 않는다.
    """
    return SurveyCatalogOut(
        questions=QUESTIONS,
        face_types=FACE_TYPES,
        face_any_id=FACE_ANY_ID,
    )
