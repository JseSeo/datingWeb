import logging
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.core.security import hash_password
from app.database import get_db
from app.models.match import Match, MatchRound, RoundStatus
from app.models.survey import Survey
from app.models.user import User, UserStatus
from app.models.verification import StudentVerification
from app.schemas.matching import MatchResultOut
from app.schemas.survey import SurveyOut, SurveySubmit
from app.schemas.user import MatchingPauseUpdate, ProfileUpdate, UserOut
from app.schemas.verification import VerificationOut
from app.survey.validation import sanitize_responses

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me", tags=["me"])

_PREF_SUFFIX = "_pref"

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def _validate_answers(answers: dict) -> None:
    responses = answers.get("responses")
    absolute = answers.get("absolute")
    if not isinstance(responses, dict) or not isinstance(absolute, list):
        raise HTTPException(status_code=400, detail="설문 형식이 올바르지 않습니다")
    if not all(isinstance(x, str) for x in absolute):
        raise HTTPException(status_code=400, detail="절대질문 형식이 올바르지 않습니다")
    if len(absolute) > 2:
        raise HTTPException(status_code=400, detail="절대질문은 최대 2개입니다")
    if any(qid not in responses for qid in absolute):
        raise HTTPException(status_code=400, detail="절대질문은 응답한 문항만 가능합니다")


def _sanitized(answers: dict, user_id: int) -> dict:
    """카탈로그로 검증한 값만 남긴다. 위반은 400이 아니라 버린다.

    거절 대신 버리는 이유: 유일한 클라이언트가 우리 프론트라, 카탈로그가 바뀌는
    사이 오래된 탭을 열어둔 유저가 저장 자체를 못 하게 되는 쪽이 더 나쁘다.

    `absolute`는 두 번 걸러진다. 값이 버려진 문항을 가리키는 고아를 없애고
    (구조 검증은 버리기 전에 돌아 이걸 못 잡는다), `_pref`가 아닌 문항도 뺀다
    — `absolute_ok`가 어차피 무시하므로 남겨두면 유저에게 거짓말이 된다.
    """
    responses, dropped = sanitize_responses(answers["responses"])
    absolute = [
        qid for qid in answers["absolute"]
        if qid in responses and qid.endswith(_PREF_SUFFIX)
    ]
    if dropped:
        logger.warning("설문 응답 %d건을 버렸다 (user_id=%s): %s",
                       len(dropped), user_id, ", ".join(dropped))
    return {"responses": responses, "absolute": absolute}


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
    _validate_answers(payload.answers)
    answers = _sanitized(payload.answers, current_user.id)
    survey = db.query(Survey).filter(Survey.user_id == current_user.id).first()
    if survey:
        survey.answers = answers
    else:
        survey = Survey(user_id=current_user.id, answers=answers)
        db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey


@router.get("/match", response_model=MatchResultOut | None)
def get_my_match(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """가장 최근에 실행된 라운드의 내 결과. 미매칭이거나 실행된 라운드가 없으면 null.

    이력은 주지 않는다 — 화면이 보여주는 건 "이번 주 결과"뿐이다 (설계 §7.1).
    executed_at이 빈 done 행은 정렬 기준이 없어 제외한다. 정상 실행에서는
    생기지 않지만, 섞이면 최신 라운드 판정이 DB의 NULL 정렬 규칙에 좌우된다.
    """
    latest = (
        db.query(MatchRound)
        .filter(
            MatchRound.status == RoundStatus.done,
            MatchRound.executed_at.isnot(None),
        )
        .order_by(MatchRound.executed_at.desc())
        .first()
    )
    if latest is None:
        return None

    match = (
        db.query(Match)
        .filter(
            Match.match_round_id == latest.id,
            or_(Match.user_a_id == current_user.id, Match.user_b_id == current_user.id),
        )
        .first()
    )
    if match is None:
        return None

    partner_id = (
        match.user_b_id if match.user_a_id == current_user.id else match.user_a_id
    )
    partner = db.get(User, partner_id)
    return MatchResultOut(
        name=partner.name,
        university=partner.university,
        instagram=partner.instagram,
        kakao_id=partner.kakao_id,
        phone=partner.phone,
        executed_at=latest.executed_at,
    )
