# 마이페이지 · 프로필 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 로그인 사용자가 마이페이지에서 자기 정보를 보고, 프로필(사진·자기소개·연락처)을 수정하고, 매칭 일시중지·로그아웃·회원 탈퇴할 수 있게 한다.

**Architecture:** 백엔드 — `app/api/me.py`에 사진 업로드(`POST /me/profile-photo`)·회원 탈퇴(`DELETE /me`, 익명화 soft-delete) 추가, `UserStatus`에 `withdrawn` 추가, `uploads/`를 `/uploads`로 정적 서빙. 프론트 — `/mypage`(카드 그룹)·`/profile`(수정 폼) 페이지, `api.ts`에 호출 함수 4개, `auth.tsx`에 `refreshUser`.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + pytest(TestClient) / React(Vite) + react-router-dom + vitest + @testing-library/react

> **설계 결정 (스펙 보완):** 스펙은 사진 *서빙* 방법을 명시 안 함. 마이페이지에 사진을 보이려면 URL 접근이 필요하므로 — ① `main.py`에서 `uploads/`를 `/uploads`로 StaticFiles 마운트, ② `profile_photo`는 verification.py의 OS 경로(`os.path.join`, Windows 역슬래시) 대신 **URL 경로 `/uploads/{filename}`**(슬래시)로 저장한다. 파일 삭제 시 디스크 경로는 `os.path.join(upload_dir, basename(profile_photo))`로 복원. 이 점만 verification 패턴과 다르며 이유는 서빙 가능 URL 확보다.

---

## File Structure

**백엔드**
- Modify `app/models/user.py` — `UserStatus`에 `withdrawn` 추가
- Modify `app/main.py` — `/uploads` StaticFiles 마운트
- Modify `app/api/me.py` — `POST /me/profile-photo`, `DELETE /me` 추가
- Create `tests/test_profile_photo.py` — 사진 업로드 테스트
- Create `tests/test_withdraw.py` — 탈퇴 익명화 테스트

**프론트**
- Modify `src/lib/types.ts` — `UserStatus` union에 `withdrawn`
- Modify `src/lib/api.ts` — `updateProfile`·`uploadProfilePhoto`·`toggleMatchingPause`·`withdraw`
- Modify `src/lib/auth.tsx` — `refreshUser` 노출
- Create `src/pages/Profile/Profile.tsx` + `Profile.module.css` + `Profile.test.tsx`
- Create `src/pages/MyPage/MyPage.tsx` + `MyPage.module.css` + `MyPage.test.tsx`
- Modify `src/App.tsx` — `/mypage`·`/profile` 라우트

---

## Task 1: `UserStatus`에 `withdrawn` 추가

**Files:**
- Modify: `backend/app/models/user.py:8-11`

- [ ] **Step 1: enum 값 추가**

`app/models/user.py`의 `UserStatus`를 다음으로 교체:

```python
class UserStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    suspended = "suspended"
    withdrawn = "withdrawn"
```

- [ ] **Step 2: 기존 테스트로 회귀 확인**

Run: `cd backend && uv run pytest -q`
Expected: PASS (기존 전부 통과 — enum 추가는 비파괴적)

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/user.py
git commit -m "feat(backend): UserStatus에 withdrawn 추가"
```

---

## Task 2: `uploads/` 정적 서빙 마운트

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: StaticFiles 마운트 추가**

`app/main.py`를 다음으로 교체(라우터 등록 뒤에 마운트 추가):

```python
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import app.models  # noqa: F401
from app.api.router import router
from app.config import settings

app = FastAPI(title="DateDrop Korea API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


@app.get("/health")
def health_check():
    return {"status": "ok"}
```

- [ ] **Step 2: 서버 import 확인**

Run: `cd backend && uv run python -c "import app.main"`
Expected: 에러 없음(종료 코드 0)

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(backend): uploads 디렉터리 /uploads 정적 서빙"
```

---

## Task 3: `POST /me/profile-photo` — 프로필 사진 업로드

**Files:**
- Modify: `backend/app/api/me.py`
- Test: `backend/tests/test_profile_photo.py`

- [ ] **Step 1: 실패하는 테스트 작성**

Create `backend/tests/test_profile_photo.py`:

```python
import io
from fastapi.testclient import TestClient


def _register_and_get_headers(client: TestClient, email: str) -> dict:
    client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "테스터",
        "university": "서울대학교",
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_upload_profile_photo(client: TestClient):
    headers = _register_and_get_headers(client, "photo@test.com")
    response = client.post(
        "/me/profile-photo",
        files={"file": ("me.jpg", io.BytesIO(b"fake image data"), "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["profile_photo"] is not None
    assert data["profile_photo"].startswith("/uploads/")


def test_upload_profile_photo_wrong_type(client: TestClient):
    headers = _register_and_get_headers(client, "photowrong@test.com")
    response = client.post(
        "/me/profile-photo",
        files={"file": ("doc.pdf", io.BytesIO(b"pdf data"), "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 400


def test_upload_profile_photo_too_large(client: TestClient):
    headers = _register_and_get_headers(client, "photobig@test.com")
    big = io.BytesIO(b"x" * (10 * 1024 * 1024 + 1))
    response = client.post(
        "/me/profile-photo",
        files={"file": ("big.jpg", big, "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 400


def test_upload_profile_photo_unauthenticated(client: TestClient):
    response = client.post(
        "/me/profile-photo",
        files={"file": ("me.jpg", io.BytesIO(b"data"), "image/jpeg")},
    )
    assert response.status_code == 401
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_profile_photo.py -v`
Expected: FAIL — `404 Not Found` (엔드포인트 없음)

- [ ] **Step 3: 엔드포인트 구현**

`app/api/me.py` 상단 import 블록을 다음으로 교체:

```python
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.database import get_db
from app.models.survey import Survey
from app.models.user import User
from app.schemas.survey import SurveyOut, SurveySubmit
from app.schemas.user import MatchingPauseUpdate, ProfileUpdate, UserOut

router = APIRouter(prefix="/me", tags=["me"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
```

그리고 `get_me` 함수 바로 아래에 엔드포인트 추가:

```python
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
    ext = "jpg"
    if file.filename and "." in file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower()
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
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_profile_photo.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/me.py backend/tests/test_profile_photo.py
git commit -m "feat(backend): 프로필 사진 업로드 POST /me/profile-photo"
```

---

## Task 4: `DELETE /me` — 회원 탈퇴 (익명화)

**Files:**
- Modify: `backend/app/api/me.py`
- Test: `backend/tests/test_withdraw.py`

- [ ] **Step 1: 실패하는 테스트 작성**

Create `backend/tests/test_withdraw.py`:

```python
import io
from fastapi.testclient import TestClient

from tests.conftest import TestingSessionLocal
from app.models.user import User, UserStatus
from app.models.verification import StudentVerification
from app.models.survey import Survey


def _register_and_get_headers(client: TestClient, email: str) -> dict:
    client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "테스터",
        "university": "서울대학교",
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_withdraw_anonymizes_and_deletes(client: TestClient):
    headers = _register_and_get_headers(client, "bye@test.com")
    # 프로필·학생증·설문 채우기
    client.put("/me/profile", json={
        "bio": "안녕", "instagram": "ig", "kakao_id": "kk", "phone": "010",
    }, headers=headers)
    client.post(
        "/me/profile-photo",
        files={"file": ("me.jpg", io.BytesIO(b"img"), "image/jpeg")},
        headers=headers,
    )
    client.post(
        "/verification/upload",
        files={"file": ("id.jpg", io.BytesIO(b"img"), "image/jpeg")},
        headers=headers,
    )
    client.put("/me/survey", json={"answers": {"q1": "a"}}, headers=headers)

    response = client.delete("/me", headers=headers)
    assert response.status_code == 204

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.name == "탈퇴회원").first()
        assert user is not None
        assert user.status == UserStatus.withdrawn
        assert user.email == f"withdrawn_{user.id}@deleted.local"
        assert user.instagram is None
        assert user.kakao_id is None
        assert user.phone is None
        assert user.bio is None
        assert user.profile_photo is None
        assert db.query(StudentVerification).filter(
            StudentVerification.user_id == user.id
        ).first() is None
        assert db.query(Survey).filter(Survey.user_id == user.id).first() is None
    finally:
        db.close()


def test_withdraw_blocks_relogin(client: TestClient):
    headers = _register_and_get_headers(client, "byerelogin@test.com")
    client.delete("/me", headers=headers)
    res = client.post("/auth/login", json={
        "email": "byerelogin@test.com", "password": "password123",
    })
    assert res.status_code == 401


def test_withdraw_unauthenticated(client: TestClient):
    response = client.delete("/me")
    assert response.status_code == 401
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_withdraw.py -v`
Expected: FAIL — `405 Method Not Allowed` 또는 404 (DELETE /me 없음)

- [ ] **Step 3: 엔드포인트 구현**

`app/api/me.py` import에 다음 두 줄 추가(기존 import 블록 안):

```python
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from app.core.security import hash_password
from app.models.verification import StudentVerification
```

(이미 있는 import는 중복 추가 말 것 — `APIRouter/Depends/HTTPException/UploadFile/status`는 Task 3에서 정리됨. `Response`만 새로 추가, `Survey`는 이미 import됨.)

`upload_profile_photo` 아래에 엔드포인트 추가:

```python
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
        if verification.image_url and os.path.exists(verification.image_url):
            os.remove(verification.image_url)
        db.delete(verification)

    survey = (
        db.query(Survey).filter(Survey.user_id == current_user.id).first()
    )
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
```

`UserStatus` import 확인 — `from app.models.user import User, UserStatus`로 변경(현재 `User`만 import).

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_withdraw.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 전체 백엔드 회귀**

Run: `cd backend && uv run pytest -q`
Expected: PASS (전체)

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/me.py backend/tests/test_withdraw.py
git commit -m "feat(backend): 회원 탈퇴 DELETE /me (익명화 soft-delete)"
```

---

## Task 5: 프론트 타입 + API 함수

**Files:**
- Modify: `frontend/src/lib/types.ts:1`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: `UserStatus`에 `withdrawn` 추가**

`src/lib/types.ts:1`을 교체:

```typescript
export type UserStatus = "pending" | "active" | "suspended" | "withdrawn";
```

- [ ] **Step 2: API 함수 추가**

`src/lib/api.ts` 끝(`fetchMe` 아래)에 추가:

```typescript
export function updateProfile(data: {
  bio?: string;
  instagram?: string;
  kakao_id?: string;
  phone?: string;
}): Promise<UserOut> {
  return apiFetch<UserOut>("/me/profile", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function uploadProfilePhoto(file: File): Promise<UserOut> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<UserOut>("/me/profile-photo", {
    method: "POST",
    body: form,
  });
}

export function toggleMatchingPause(paused: boolean): Promise<UserOut> {
  return apiFetch<UserOut>("/me/matching-pause", {
    method: "PUT",
    body: JSON.stringify({ matching_paused: paused }),
  });
}

export function withdraw(): Promise<void> {
  return apiFetch<void>("/me", { method: "DELETE" });
}
```

- [ ] **Step 3: 타입 체크**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: 에러 없음

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts
git commit -m "feat(frontend): 프로필/탈퇴 API 함수 + withdrawn 타입"
```

---

## Task 6: auth context에 `refreshUser` 노출

**Files:**
- Modify: `frontend/src/lib/auth.tsx`

- [ ] **Step 1: `refreshUser` 추가**

`src/lib/auth.tsx`의 `AuthState` 인터페이스에 추가:

```typescript
interface AuthState {
  user: UserOut | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<UserOut>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}
```

`logout` 함수 아래에 추가:

```typescript
  async function refreshUser(): Promise<void> {
    const me = await fetchMe();
    setUser(me);
  }
```

Provider value 교체:

```typescript
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>
```

- [ ] **Step 2: 타입 체크**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: 에러 없음

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/auth.tsx
git commit -m "feat(frontend): auth context refreshUser 추가"
```

---

## Task 7: `/profile` 프로필 수정 폼

**Files:**
- Create: `frontend/src/pages/Profile/Profile.tsx`
- Create: `frontend/src/pages/Profile/Profile.module.css`
- Test: `frontend/src/pages/Profile/Profile.test.tsx`

- [ ] **Step 1: 실패하는 테스트 작성**

Create `frontend/src/pages/Profile/Profile.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Profile from "./Profile";
import * as api from "../../lib/api";

const user = {
  id: 1, email: "a@b.com", name: "김미", university: "서울대학교",
  status: "active" as const, profile_photo: null, bio: null,
  instagram: null, kakao_id: null, phone: null,
  matching_paused: false, is_admin: false, created_at: "2026-01-01",
};

vi.mock("../../lib/auth", () => ({
  useAuth: () => ({ user, refreshUser: vi.fn().mockResolvedValue(undefined) }),
}));

const navigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return { ...actual, useNavigate: () => navigate };
});

beforeEach(() => vi.clearAllMocks());

function renderProfile() {
  render(<MemoryRouter><Profile /></MemoryRouter>);
}

describe("Profile", () => {
  it("연락처 3개 모두 비면 저장 막고 에러 표시", async () => {
    const spy = vi.spyOn(api, "updateProfile");
    renderProfile();
    fireEvent.click(screen.getByRole("button", { name: "저장" }));
    await waitFor(() =>
      expect(screen.getByText("연락처를 1개 이상 입력하세요")).toBeInTheDocument(),
    );
    expect(spy).not.toHaveBeenCalled();
  });

  it("연락처 1개 있으면 저장 호출", async () => {
    const spy = vi.spyOn(api, "updateProfile").mockResolvedValue(user);
    renderProfile();
    fireEvent.change(screen.getByLabelText("인스타그램"), {
      target: { value: "myig" },
    });
    fireEvent.click(screen.getByRole("button", { name: "저장" }));
    await waitFor(() => expect(spy).toHaveBeenCalled());
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npx vitest run src/pages/Profile/Profile.test.tsx`
Expected: FAIL — `Profile` 모듈 없음

- [ ] **Step 3: CSS 작성**

Create `frontend/src/pages/Profile/Profile.module.css`:

```css
.wrap { padding-top: 24px; }

.title {
  font-size: 28px;
  margin-bottom: 24px;
  color: var(--color-primary);
}

.photoRow {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.photo {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  object-fit: cover;
  background: var(--color-accent);
}

.readonly {
  font-size: 14px;
  color: #666;
  margin-bottom: var(--space);
}

.textarea {
  width: 100%;
  min-height: 80px;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-family: inherit;
  margin-bottom: var(--space);
}

.error {
  color: var(--color-error);
  font-size: 14px;
  margin-bottom: var(--space);
}
```

- [ ] **Step 4: 컴포넌트 작성**

Create `frontend/src/pages/Profile/Profile.tsx`:

```tsx
import { useState, type FormEvent, type ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { updateProfile, uploadProfilePhoto, ApiError } from "../../lib/api";
import { Input } from "../../components/Input/Input";
import { Button } from "../../components/Button/Button";
import styles from "./Profile.module.css";

const API = import.meta.env.VITE_API_URL;

export default function Profile() {
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();

  const [bio, setBio] = useState(user?.bio ?? "");
  const [instagram, setInstagram] = useState(user?.instagram ?? "");
  const [kakaoId, setKakaoId] = useState(user?.kakao_id ?? "");
  const [phone, setPhone] = useState(user?.phone ?? "");
  const [photo, setPhoto] = useState(user?.profile_photo ?? null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handlePhoto(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    try {
      const updated = await uploadProfilePhoto(file);
      setPhoto(updated.profile_photo);
      await refreshUser();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "사진 업로드에 실패했습니다");
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!instagram && !kakaoId && !phone) {
      setError("연락처를 1개 이상 입력하세요");
      return;
    }
    setSubmitting(true);
    try {
      await updateProfile({ bio, instagram, kakao_id: kakaoId, phone });
      await refreshUser();
      navigate("/mypage");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "저장에 실패했습니다");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>프로필 수정</h1>

      <div className={styles.photoRow}>
        {photo ? (
          <img className={styles.photo} src={`${API}${photo}`} alt="프로필 사진" />
        ) : (
          <div className={styles.photo} aria-label="기본 프로필" />
        )}
        <label>
          사진 변경
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handlePhoto}
            style={{ display: "none" }}
          />
        </label>
      </div>

      <p className={styles.readonly}>이름: {user?.name}</p>
      <p className={styles.readonly}>학교: {user?.university}</p>

      <form onSubmit={handleSubmit}>
        <label htmlFor="bio">자기소개</label>
        <textarea
          id="bio"
          className={styles.textarea}
          value={bio}
          onChange={(e) => setBio(e.target.value)}
        />
        <Input id="instagram" label="인스타그램" value={instagram}
          onChange={(e) => setInstagram(e.target.value)} />
        <Input id="kakao" label="카카오톡 ID" value={kakaoId}
          onChange={(e) => setKakaoId(e.target.value)} />
        <Input id="phone" label="전화번호" value={phone}
          onChange={(e) => setPhone(e.target.value)} />
        {error && <p className={styles.error}>{error}</p>}
        <Button type="submit" disabled={submitting}>
          {submitting ? "저장 중..." : "저장"}
        </Button>
      </form>
    </div>
  );
}
```

- [ ] **Step 5: 통과 확인**

Run: `cd frontend && npx vitest run src/pages/Profile/Profile.test.tsx`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Profile
git commit -m "feat(frontend): 프로필 수정 폼 /profile (연락처 필수 검증)"
```

---

## Task 8: `/mypage` 마이페이지

**Files:**
- Create: `frontend/src/pages/MyPage/MyPage.tsx`
- Create: `frontend/src/pages/MyPage/MyPage.module.css`
- Test: `frontend/src/pages/MyPage/MyPage.test.tsx`

- [ ] **Step 1: 실패하는 테스트 작성**

Create `frontend/src/pages/MyPage/MyPage.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import MyPage from "./MyPage";
import * as api from "../../lib/api";

const user = {
  id: 1, email: "a@b.com", name: "김미", university: "서울대학교",
  status: "active" as const, profile_photo: null, bio: null,
  instagram: null, kakao_id: null, phone: null,
  matching_paused: false, is_admin: false, created_at: "2026-01-01",
};

const logout = vi.fn();
vi.mock("../../lib/auth", () => ({
  useAuth: () => ({ user, logout, refreshUser: vi.fn() }),
}));

const navigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return { ...actual, useNavigate: () => navigate };
});

beforeEach(() => vi.clearAllMocks());

function renderMyPage() {
  render(<MemoryRouter><MyPage /></MemoryRouter>);
}

describe("MyPage", () => {
  it("탈퇴 confirm 후 withdraw 호출 + 랜딩 이동", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const spy = vi.spyOn(api, "withdraw").mockResolvedValue(undefined);
    const clear = vi.spyOn(api, "clearToken").mockImplementation(() => {});
    renderMyPage();
    fireEvent.click(screen.getByRole("button", { name: "회원 탈퇴" }));
    await waitFor(() => expect(spy).toHaveBeenCalled());
    expect(clear).toHaveBeenCalled();
    expect(navigate).toHaveBeenCalledWith("/");
  });

  it("탈퇴 confirm 취소 시 withdraw 호출 안 함", () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const spy = vi.spyOn(api, "withdraw");
    renderMyPage();
    fireEvent.click(screen.getByRole("button", { name: "회원 탈퇴" }));
    expect(spy).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npx vitest run src/pages/MyPage/MyPage.test.tsx`
Expected: FAIL — `MyPage` 모듈 없음

- [ ] **Step 3: CSS 작성**

Create `frontend/src/pages/MyPage/MyPage.module.css`:

```css
.wrap { padding-top: 24px; }

.header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-bottom: 24px;
}

.photo {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  object-fit: cover;
  background: var(--color-accent);
}

.name { font-size: 20px; font-weight: bold; }
.school { font-size: 14px; color: #666; }

.badge {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--color-accent);
  color: #fff;
}

.card {
  background: #fff;
  border-radius: 12px;
  padding: 8px 0;
  margin-bottom: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 14px 16px;
  background: none;
  border: none;
  font-size: 15px;
  text-align: left;
  cursor: pointer;
}

.rowDisabled { color: #bbb; cursor: not-allowed; }
.danger { color: var(--color-error); }
.soon { font-size: 12px; color: #bbb; }
```

- [ ] **Step 4: 컴포넌트 작성**

Create `frontend/src/pages/MyPage/MyPage.tsx`:

```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { toggleMatchingPause, withdraw, clearToken } from "../../lib/api";
import styles from "./MyPage.module.css";

const API = import.meta.env.VITE_API_URL;

const STATUS_LABEL: Record<string, string> = {
  pending: "인증 대기",
  active: "활동중",
  suspended: "정지",
  withdrawn: "탈퇴",
};

export default function MyPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [paused, setPaused] = useState(user?.matching_paused ?? false);

  async function handlePause() {
    const next = !paused;
    setPaused(next);
    try {
      await toggleMatchingPause(next);
    } catch {
      setPaused(!next); // 실패 롤백
    }
  }

  function handleLogout() {
    logout();
    navigate("/");
  }

  async function handleWithdraw() {
    if (!window.confirm("정말 탈퇴하시겠어요? 프로필·연락처·설문이 삭제됩니다.")) {
      return;
    }
    await withdraw();
    clearToken();
    navigate("/");
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.header}>
        {user?.profile_photo ? (
          <img className={styles.photo} src={`${API}${user.profile_photo}`} alt="프로필" />
        ) : (
          <div className={styles.photo} aria-label="기본 프로필" />
        )}
        <div className={styles.name}>{user?.name}</div>
        <div className={styles.school}>{user?.university}</div>
        <span className={styles.badge}>
          {STATUS_LABEL[user?.status ?? "pending"]}
        </span>
      </div>

      <div className={styles.card}>
        <button className={styles.row} onClick={() => navigate("/profile")}>
          <span>프로필 수정</span><span>›</span>
        </button>
        <div className={`${styles.row} ${styles.rowDisabled}`}>
          <span>가치관 설문</span><span className={styles.soon}>준비중</span>
        </div>
      </div>

      <div className={styles.card}>
        <button className={styles.row} onClick={handlePause}>
          <span>매칭 일시중지</span>
          <span>{paused ? "ON" : "OFF"}</span>
        </button>
      </div>

      <div className={styles.card}>
        <button className={styles.row} onClick={handleLogout}>
          <span>로그아웃</span><span>›</span>
        </button>
        <button className={`${styles.row} ${styles.danger}`} onClick={handleWithdraw}>
          <span>회원 탈퇴</span><span>›</span>
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: 통과 확인**

Run: `cd frontend && npx vitest run src/pages/MyPage/MyPage.test.tsx`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/MyPage
git commit -m "feat(frontend): 마이페이지 /mypage (카드 그룹·탈퇴·일시중지)"
```

---

## Task 9: 라우트 배선

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 라우트 추가**

`src/App.tsx`를 교체:

```tsx
import { Routes, Route } from "react-router-dom";
import Landing from "./pages/Landing/Landing";
import Register from "./pages/Register/Register";
import Login from "./pages/Login/Login";
import Pending from "./pages/Pending/Pending";
import Home from "./pages/Home/Home";
import MyPage from "./pages/MyPage/MyPage";
import Profile from "./pages/Profile/Profile";
import { ProtectedRoute } from "./components/ProtectedRoute";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/register" element={<Register />} />
      <Route path="/login" element={<Login />} />
      <Route
        path="/pending"
        element={
          <ProtectedRoute requireStatus="pending">
            <Pending />
          </ProtectedRoute>
        }
      />
      <Route
        path="/home"
        element={
          <ProtectedRoute requireStatus="active">
            <Home />
          </ProtectedRoute>
        }
      />
      <Route
        path="/mypage"
        element={
          <ProtectedRoute>
            <MyPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
```

> `ProtectedRoute`는 `requireStatus` 없으면 로그인만 요구(pending·active 모두 접근). 현재 구현 그대로 동작.

- [ ] **Step 2: 전체 프론트 테스트 + 빌드**

Run: `cd frontend && npx vitest run && npm run build`
Expected: 모든 테스트 PASS, 빌드 성공

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(frontend): /mypage·/profile 라우트 배선"
```

---

## 최종 검증

- [ ] 백엔드 전체: `cd backend && uv run pytest -q` → 전부 PASS
- [ ] 프론트 전체: `cd frontend && npx vitest run` → 전부 PASS
- [ ] 프론트 빌드: `cd frontend && npm run build` → 성공
- [ ] 수동: 로그인 → `/mypage` → 사진 업로드 → 마이페이지에 사진 표시 확인 → 일시중지 토글 → 탈퇴

---

## 스펙 커버리지 체크

| 스펙 항목 | 태스크 |
|----------|--------|
| 1.1 withdrawn status | Task 1 |
| 1.2 POST /me/profile-photo | Task 3 (+ Task 2 서빙) |
| 1.3 DELETE /me 익명화 | Task 4 |
| 2.1 /mypage 카드 그룹 | Task 8 |
| 2.2 /profile 수정 폼 | Task 7 |
| 2.3 api.ts 함수 | Task 5 |
| 2.3 auth refreshUser | Task 6 |
| 2.3 types withdrawn | Task 5 |
| 2.3 라우트 | Task 9 |
| 3 백엔드 테스트 | Task 3·4 |
| 3 프론트 테스트 | Task 7·8 |

**스펙 대비 보완:** 사진 서빙(Task 2) — 스펙 미언급이나 "마이페이지에 보인다" 성공기준 충족에 필수. `profile_photo` 저장형식을 URL(`/uploads/{filename}`)로 변경.
