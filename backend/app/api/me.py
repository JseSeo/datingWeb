from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.survey import Survey
from app.models.user import User
from app.schemas.survey import SurveyOut, SurveySubmit
from app.schemas.user import MatchingPauseUpdate, ProfileUpdate, UserOut

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/profile", response_model=UserOut)
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/matching-pause", response_model=UserOut)
def toggle_matching_pause(
    payload: MatchingPauseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.matching_paused = payload.matching_paused
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/survey", response_model=SurveyOut)
def get_survey(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    survey = db.query(Survey).filter(Survey.user_id == current_user.id).first()
    if survey is None:
        return SurveyOut(answers={})
    return survey


@router.put("/survey", response_model=SurveyOut)
def save_survey(
    payload: SurveySubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    survey = db.query(Survey).filter(Survey.user_id == current_user.id).first()
    if survey:
        survey.answers = payload.answers
    else:
        survey = Survey(user_id=current_user.id, answers=payload.answers)
        db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey
