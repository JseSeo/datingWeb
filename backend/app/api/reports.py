from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.report import Report, ReportType
from app.models.user import User
from app.schemas.report import ReportCreate, ReportOut

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportOut, status_code=201)
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="내용을 입력하세요",
        )

    name: str | None = (payload.target_name or "").strip()
    university: str | None = (payload.target_university or "").strip()

    if payload.type == ReportType.suggestion:
        # 건의는 대상이 없다. 클라이언트가 무엇을 보내든 버린다.
        name = None
        university = None
    else:
        if not name or not university:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="신고 대상의 이름과 학교를 입력하세요",
            )
        if (
            name == current_user.name.strip()
            and university == current_user.university.strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="자기 자신을 신고할 수 없습니다",
            )

    report = Report(
        reporter_id=current_user.id,
        type=payload.type,
        target_name=name,
        target_university=university,
        reason=reason,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
