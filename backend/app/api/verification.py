import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user, require_admin
from app.database import get_db
from app.models.user import User, UserStatus
from app.models.verification import StudentVerification, VerificationStatus
from app.schemas.verification import VerificationAction, VerificationOut

router = APIRouter(tags=["verification"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/verification/upload", response_model=VerificationOut, status_code=201)
async def upload_student_id(
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

    # 학생증은 비공개 디렉토리에 저장 (정적 mount 안 됨) — 프로덕션은 S3로 교체
    os.makedirs(settings.verification_dir, exist_ok=True)
    # 확장자는 파일명에서 추출하되 영숫자·5자 이하만 허용 (경로 조작 차단)
    ext = "jpg"
    if file.filename and "." in file.filename:
        candidate = file.filename.rsplit(".", 1)[-1].lower()
        if candidate.isalnum() and len(candidate) <= 5:
            ext = candidate
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(settings.verification_dir, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    # upsert: 이미 제출한 경우 덮어쓰기
    verification = (
        db.query(StudentVerification)
        .filter(StudentVerification.user_id == current_user.id)
        .first()
    )
    if verification:
        verification.image_url = filename
        verification.status = VerificationStatus.pending
        verification.reviewed_at = None
        verification.reviewed_by = None
    else:
        verification = StudentVerification(
            user_id=current_user.id,
            image_url=filename,
        )
        db.add(verification)

    db.commit()
    db.refresh(verification)
    return verification


@router.get("/admin/verifications", response_model=list[VerificationOut])
def list_pending_verifications(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return (
        db.query(StudentVerification)
        .filter(StudentVerification.status == VerificationStatus.pending)
        .all()
    )


@router.post("/admin/verifications/{verification_id}", response_model=VerificationOut)
def review_verification(
    verification_id: int,
    payload: VerificationAction,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    verification = db.get(StudentVerification, verification_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    if payload.action == "approve":
        verification.status = VerificationStatus.approved
        user = db.get(User, verification.user_id)
        if user:
            user.status = UserStatus.active
    else:
        verification.status = VerificationStatus.rejected

    verification.reviewed_at = datetime.utcnow()
    verification.reviewed_by = admin.id
    db.commit()
    db.refresh(verification)
    return verification


@router.get("/admin/verifications/{verification_id}/image")
def get_verification_image(
    verification_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    verification = db.get(StudentVerification, verification_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")
    filepath = os.path.join(
        settings.verification_dir, os.path.basename(verification.image_url)
    )
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(filepath)
