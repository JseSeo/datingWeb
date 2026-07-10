# 학생증 이미지 비공개화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 학생증 인증 이미지를 API 응답의 서버경로 노출 없이, 무인증 정적 서빙 대신 관리자 전용 인증 엔드포인트로만 접근 가능하게 만든다.

**Architecture:** 학생증 파일을 정적 mount 안 되는 별도 `verification_dir`에 저장하고 DB엔 파일명만 기록한다. `VerificationOut` 응답 스키마에서 `image_url`을 제거하고, 관리자 심사용 이미지는 `GET /admin/verifications/{id}/image`(require_admin)로 서빙한다.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, pytest (백엔드) / React + Vite + Vitest, TypeScript (프론트).

## Global Constraints

- 스펙이 진실: `docs/superpowers/specs/2026-07-10-verification-image-privacy-design.md`. 충돌 시 사용자 확인 후 스펙 우선 수정.
- 환경변수/설정 하드코딩 금지 — `app/config.py` Settings 통해서만 (`backend/CLAUDE.md`).
- 엔드포인트마다 Pydantic 스키마 사용, 입력≠응답 스키마 분리 (`backend/CLAUDE.md`).
- 프로필 사진(`upload_dir` + `/uploads` 공개 mount)은 건드리지 않는다 (스코프 밖).
- git 커밋/푸시는 사용자 허락 후에만 (`CLAUDE.md`). 각 Task의 커밋 스텝은 허락 전제로 작성됨.
- TDD: 실패 테스트 먼저 → 최소 구현 → 통과 → 커밋.

---

## File Structure

| 파일 | 책임 | Task |
|------|------|------|
| `backend/app/config.py` | `verification_dir` 설정 | 1 |
| `backend/app/api/verification.py` | 학생증 저장(비공개dir·파일명·확장자검증), 관리자 이미지 서빙 | 1, 2 |
| `backend/app/api/me.py` | withdraw 시 학생증 파일 삭제 경로 | 1 |
| `backend/app/schemas/verification.py` | `VerificationOut`에서 `image_url` 제거 | 2 |
| `backend/tests/test_verification.py` | 저장위치·응답·이미지엔드포인트 테스트 | 1, 2 |
| `frontend/src/lib/types.ts` | `VerificationOut` 인터페이스 `image_url` 제거 | 3 |
| `frontend/src/lib/api.verification.test.ts` 외 2 | mock의 `image_url` 제거 | 3 |

---

### Task 1: 학생증 비공개 저장소 분리

학생증 파일을 정적 서빙되지 않는 `verification_dir`로 옮기고, DB엔 전체경로 대신 파일명만 저장한다. 확장자 write-traversal을 차단하고, withdraw 삭제 경로를 새 디렉토리 기준으로 고친다.

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/api/verification.py:40-70`
- Modify: `backend/app/api/me.py:87-95`
- Test: `backend/tests/test_verification.py`

**Interfaces:**
- Consumes: `settings.upload_dir`(기존), `StudentVerification.image_url`(컬럼, 이제 파일명 저장).
- Produces:
  - `settings.verification_dir: str` — 학생증 비공개 저장 디렉토리 (기본 `"verification_uploads"`).
  - 업로드 후 `StudentVerification.image_url` == 파일명만 (예: `a1b2.jpg`, 경로 구분자 없음).
  - 파일은 `os.path.join(settings.verification_dir, <파일명>)`에 존재, `settings.upload_dir`엔 없음.

- [ ] **Step 1: config에 verification_dir 추가**

`backend/app/config.py`의 `Settings` 클래스에서 `upload_dir` 아래 줄 추가:

```python
    upload_dir: str = "uploads"
    verification_dir: str = "verification_uploads"
```

- [ ] **Step 2: 실패 테스트 작성 — 비공개 저장 검증**

`backend/tests/test_verification.py` 상단 import에 추가 (파일 최상단):

```python
import io
import os

from fastapi.testclient import TestClient

from tests.conftest import TestingSessionLocal
from app.config import settings
from app.models.verification import StudentVerification
```

파일 끝에 테스트 추가:

```python
def test_upload_stores_in_private_dir_not_public(client: TestClient):
    headers = _register_and_get_headers(client, "priv@test.com")
    res = client.post(
        "/verification/upload",
        files={"file": ("id.jpg", io.BytesIO(b"secret-id-bytes"), "image/jpeg")},
        headers=headers,
    )
    assert res.status_code == 201

    db = TestingSessionLocal()
    try:
        v = db.query(StudentVerification).order_by(StudentVerification.id.desc()).first()
        filename = v.image_url
    finally:
        db.close()

    # DB엔 파일명만 저장 (경로 구분자 없음)
    assert "/" not in filename
    assert "\\" not in filename
    # 비공개 디렉토리에 존재
    assert os.path.exists(os.path.join(settings.verification_dir, filename))
    # 공개 uploads 디렉토리엔 없음
    assert not os.path.exists(os.path.join(settings.upload_dir, filename))
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_verification.py::test_upload_stores_in_private_dir_not_public -v`
Expected: FAIL — 현재는 `image_url`에 전체경로 저장 + `upload_dir`에 파일 저장되므로 assertion 실패.

- [ ] **Step 4: verification.py 업로드 로직 수정**

`backend/app/api/verification.py`의 저장 블록(현재 40-48행)을 아래로 교체:

```python
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
```

이어지는 upsert 블록(현재 56-65행)에서 `filepath` → `filename`으로 교체 (DB엔 파일명만 저장):

```python
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
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_verification.py::test_upload_stores_in_private_dir_not_public -v`
Expected: PASS

- [ ] **Step 6: withdraw 삭제 경로 수정**

`backend/app/api/me.py`의 withdraw 내 학생증 삭제 블록(현재 92-95행)을 교체:

```python
    if verification:
        vpath = os.path.join(
            settings.verification_dir, os.path.basename(verification.image_url)
        )
        if os.path.exists(vpath):
            os.remove(vpath)
        db.delete(verification)
```

- [ ] **Step 7: 전체 백엔드 테스트로 회귀 확인**

Run: `cd backend && uv run pytest tests/test_verification.py tests/test_withdraw.py -v`
Expected: 전부 PASS (기존 withdraw 테스트는 DB row 삭제만 검증하므로 경로 변경과 무관하게 통과).

- [ ] **Step 8: 커밋**

```bash
git add backend/app/config.py backend/app/api/verification.py backend/app/api/me.py backend/tests/test_verification.py
git commit -m "feat(backend): 학생증 이미지 비공개 디렉토리로 분리 (verification_dir)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: 응답 스키마 정리 + 관리자 이미지 서빙 엔드포인트

`VerificationOut`에서 `image_url`을 제거해 서버경로/파일명 노출을 없애고, 관리자만 접근 가능한 이미지 서빙 엔드포인트를 추가한다.

**Files:**
- Modify: `backend/app/schemas/verification.py:6-14`
- Modify: `backend/app/api/verification.py` (import + 새 엔드포인트)
- Test: `backend/tests/test_verification.py`

**Interfaces:**
- Consumes: Task 1의 `settings.verification_dir`, `StudentVerification.image_url`(파일명).
- Produces:
  - `VerificationOut`: 필드 = `id, user_id, status, reviewed_at, created_at` (image_url 없음).
  - `GET /admin/verifications/{verification_id}/image` — require_admin, 존재하면 `FileResponse`, 없으면 404.

- [ ] **Step 1: 실패 테스트 작성 — 응답 image_url 없음 + 이미지 엔드포인트**

`backend/tests/test_verification.py` 파일 끝에 추가:

```python
def test_upload_response_has_no_image_url(client: TestClient):
    headers = _register_and_get_headers(client, "noimgurl@test.com")
    res = client.post(
        "/verification/upload",
        files={"file": ("id.jpg", io.BytesIO(b"img"), "image/jpeg")},
        headers=headers,
    )
    assert res.status_code == 201
    assert "image_url" not in res.json()


def test_admin_can_fetch_verification_image(admin_client: TestClient):
    admin_client.post("/auth/register", json={
        "email": "imgstudent@test.com",
        "password": "password123",
        "name": "학생",
        "university": "서울대학교",
    })
    res = admin_client.post("/auth/login", json={
        "email": "imgstudent@test.com", "password": "password123"
    })
    student_token = res.json()["access_token"]
    up = admin_client.post(
        "/verification/upload",
        files={"file": ("id.jpg", io.BytesIO(b"secret-image"), "image/jpeg")},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    vid = up.json()["id"]

    img_res = admin_client.get(f"/admin/verifications/{vid}/image")
    assert img_res.status_code == 200
    assert img_res.content == b"secret-image"


def test_non_admin_cannot_fetch_verification_image(client: TestClient):
    headers = _register_and_get_headers(client, "notadminimg@test.com")
    up = client.post(
        "/verification/upload",
        files={"file": ("id.jpg", io.BytesIO(b"img"), "image/jpeg")},
        headers=headers,
    )
    vid = up.json()["id"]
    res = client.get(f"/admin/verifications/{vid}/image", headers=headers)
    assert res.status_code == 403


def test_fetch_missing_verification_image_404(admin_client: TestClient):
    res = admin_client.get("/admin/verifications/999999/image")
    assert res.status_code == 404
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_verification.py -k "image_url or verification_image" -v`
Expected: FAIL — `test_upload_response_has_no_image_url`는 아직 image_url 포함, 이미지 엔드포인트는 404(라우트 없음).

- [ ] **Step 3: VerificationOut에서 image_url 제거**

`backend/app/schemas/verification.py`의 `VerificationOut`에서 `image_url: str` 줄 삭제:

```python
class VerificationOut(BaseModel):
    id: int
    user_id: int
    status: VerificationStatus
    reviewed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: 이미지 서빙 엔드포인트 추가**

`backend/app/api/verification.py` import 블록(현재 5행)에 `FileResponse` 추가:

```python
from fastapi.responses import FileResponse
```

파일 끝(review_verification 아래)에 엔드포인트 추가:

```python
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
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_verification.py -v`
Expected: 전부 PASS (기존 + 신규 4개). 기존 `test_admin_list_verifications`, `test_get_my_verification_*`는 `status`만 검증하므로 image_url 제거와 무관하게 통과.

- [ ] **Step 6: 커밋**

```bash
git add backend/app/schemas/verification.py backend/app/api/verification.py backend/tests/test_verification.py
git commit -m "feat(backend): VerificationOut image_url 제거 + 관리자 전용 이미지 서빙 엔드포인트

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: 프론트 타입 정리

`VerificationOut` 인터페이스와 테스트 mock에서 `image_url`을 제거한다. 프론트는 `status`만 소비하므로 로직 변경 없음.

**Files:**
- Modify: `frontend/src/lib/types.ts:59-66`
- Modify: `frontend/src/lib/api.verification.test.ts:23`
- Modify: `frontend/src/pages/Pending/Pending.test.tsx:25`
- Modify: `frontend/src/pages/Pending/UploadForm.test.tsx:22`

**Interfaces:**
- Consumes: 백엔드 `VerificationOut`(image_url 없음, Task 2).
- Produces: 프론트 `VerificationOut` 타입 = `{ id, user_id, status, reviewed_at, created_at }`.

- [ ] **Step 1: 타입에서 image_url 제거**

`frontend/src/lib/types.ts`의 `VerificationOut` 인터페이스에서 `image_url: string;` 줄 삭제:

```typescript
export interface VerificationOut {
  id: number;
  user_id: number;
  status: VerificationStatus;
  reviewed_at: string | null;
  created_at: string;
}
```

- [ ] **Step 2: 테스트 mock에서 image_url 제거**

세 파일의 mock 객체 리터럴에서 `image_url: "x",` 조각만 삭제한다 (나머지 필드 불변).

`frontend/src/lib/api.verification.test.ts` (현재 23행): `id: 1, user_id: 1, image_url: "x", status: "pending",` → `id: 1, user_id: 1, status: "pending",`

`frontend/src/pages/Pending/Pending.test.tsx` (현재 25행): `id: 1, user_id: 1, image_url: "x",` → `id: 1, user_id: 1,`

`frontend/src/pages/Pending/UploadForm.test.tsx` (현재 22행): `id: 1, user_id: 1, image_url: "x", status: "pending" as const,` → `id: 1, user_id: 1, status: "pending" as const,`

- [ ] **Step 3: 타입체크 + 테스트 통과 확인**

Run: `cd frontend && npm run test`
Expected: 전 테스트 PASS (image_url 제거로 깨지는 참조 없음 — 컴포넌트는 status만 사용).

- [ ] **Step 4: 빌드 확인**

Run: `cd frontend && npm run build`
Expected: 타입 에러 없이 빌드 성공.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.verification.test.ts frontend/src/pages/Pending/Pending.test.tsx frontend/src/pages/Pending/UploadForm.test.tsx
git commit -m "chore(frontend): VerificationOut 타입에서 image_url 제거 (백엔드 스키마 정합)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 마이그레이션 / 데이터 노트

- 기존 DB row는 옛 전체경로 포맷일 수 있으나 개발 단계·실 데이터 없음 → 데이터 마이그레이션 불필요.
- 컬럼 추가/삭제 없음(값 의미만 변경) → Alembic 마이그레이션 불필요.
- `verification_dir`는 기본값 있으므로 `.env` 변경 불필요.

## 성공 기준 (전 Task 완료 후)

1. 어떤 API 응답에도 서버 파일시스템 경로/파일명이 포함되지 않는다 (`test_upload_response_has_no_image_url`).
2. 학생증 이미지는 `require_admin` 없이 접근 불가 (`test_non_admin_cannot_fetch_verification_image`), 정적 URL로 접근 불가 (파일이 `upload_dir` 밖 = mount 밖).
3. 프로필 사진 기능 무영향 (`test_withdraw_anonymizes_and_deletes` 통과).
4. 백엔드 verification/withdraw 테스트 + 프론트 전체 테스트 통과.
