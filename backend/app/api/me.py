import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.core.security import hash_password
from app.database import get_db
from app.models.survey import Survey
from app.models.user import User, UserStatus
from app.models.verification import StudentVerification
from app.schemas.survey import SurveyOut, SurveySubmit
from app.schemas.user import MatchingPauseUpdate, ProfileUpdate, UserOut
from app.schemas.verification import VerificationOut

router = APIRouter(prefix="/me", tags=["me"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.get("", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/profile-photo", response_model=UserOut)
async def upload_profile_photo(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="JPG, PNG, WEBP 파일만 업로드 가능합니다",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="파일 크기는 10MB 이하여야 합니다",
        )

    os.makedirs(settings.upload_dir, exist_ok=True)
    # 확장자는 파일명에서 추출하되 영숫자·5자 이하만 허용 (경로 조작 차단)
    ext = "jpg"
    if file.filename and "." in file.filename:
        candidate = file.filename.rsplit(".", 1)[-1].lower()
        if candidate.isalnum() and len(candidate) <= 5:
            ext = candidate
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(settings.upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    # 기존 사진 파일 삭제 후 교체
    if current_user.profile_photo:
        old = os.path.join(
            settings.upload_dir, os.path.basename(current_user.profile_photo)
        )
        if os.path.exists(old):
            os.remove(old)

    current_user.profile_photo = f"/uploads/{filename}"
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def withdraw(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 저장된 파일 삭제 (프로필 사진 + 학생증)
    if current_user.profile_photo:
        photo = os.path.join(
            settings.upload_dir, os.path.basename(current_user.profile_photo)
        )
        if os.path.exists(photo):
            os.remove(photo)

    verification = (
        db.query(StudentVerification)
        .filter(StudentVerification.user_id == current_user.id)
        .first()
    )
    if verification:
        vpath = os.path.join(
            settings.verification_dir, os.path.basename(verification.image_url)
        )
        if os.path.exists(vpath):
            os.remove(vpath)
        db.delete(verification)

    survey = db.query(Survey).filter(Survey.user_id == current_user.id).first()
    if survey:
        db.delete(survey)

    # 개인정보 익명화
    current_user.email = f"withdrawn_{current_user.id}@deleted.local"
    current_user.name = "탈퇴회원"
    current_user.password_hash = hash_password(uuid.uuid4().hex)
    current_user.instagram = None
    current_user.kakao_id = None
    current_user.phone = None
    current_user.bio = None
    current_user.profile_photo = None
    current_user.status = UserStatus.withdrawn

    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


@router.get("/verification", response_model=VerificationOut | None)
def get_my_verification(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(StudentVerification)
        .filter(StudentVerification.user_id == current_user.id)
        .first()
    )


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
