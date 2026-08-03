from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.database import get_db
from app.models.report import Report, ReportType
from app.models.user import User
from app.schemas.report import AdminReportOut, ReportCreate, ReportOut

router = APIRouter(prefix="/reports", tags=["reports"])
admin_router = APIRouter(prefix="/admin/reports", tags=["reports"])


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


def _to_admin_out(report: Report, reporter: User) -> AdminReportOut:
    return AdminReportOut(
        id=report.id,
        type=report.type,
        target_name=report.target_name,
        target_university=report.target_university,
        reason=report.reason,
        created_at=report.created_at,
        handled=report.handled,
        reporter_name=reporter.name,
        reporter_university=reporter.university,
    )


@admin_router.get("", response_model=list[AdminReportOut])
def list_reports(
    include_handled: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    query = db.query(Report, User).join(User, Report.reporter_id == User.id)
    if not include_handled:
        query = query.filter(Report.handled.is_(False))
    rows = query.order_by(Report.created_at.desc(), Report.id.desc()).all()
    return [_to_admin_out(report, reporter) for report, reporter in rows]


@admin_router.post("/{report_id}/handle", response_model=AdminReportOut)
def handle_report(
    report_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="존재하지 않는 신고입니다",
        )
    # 멱등: 이미 처리된 건을 다시 눌러도 200
    if not report.handled:
        report.handled = True
        db.commit()
        db.refresh(report)
    reporter = db.get(User, report.reporter_id)
    return _to_admin_out(report, reporter)
