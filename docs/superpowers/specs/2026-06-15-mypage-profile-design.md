# 마이페이지 · 프로필 설계

작성일: 2026-06-15
범위: 프론트 `/mypage`·`/profile` + 백엔드 사진 업로드·회원 탈퇴 엔드포인트

## 목표

로그인한 사용자가 자기 정보를 보고(마이페이지), 프로필을 수정하고, 매칭을 일시중지하고, 로그아웃·회원 탈퇴할 수 있다.

## 성공 기준

- 사용자가 프로필 사진을 올리면 저장되고 마이페이지에 보인다.
- 자기소개·연락처를 수정·저장할 수 있고, 연락처 1개 이상 없으면 저장이 막힌다.
- 매칭 일시중지 토글이 백엔드에 반영된다.
- 회원 탈퇴 시 개인정보가 익명화되고 학생증·설문 데이터가 삭제된다.
- 백엔드·프론트 테스트 모두 통과.

## 범위 밖 (이번 작업 아님)

- 가치관 설문 화면 구현 (마이페이지에 비활성 자리만 둠)
- 이름·학교·이메일 수정 (읽기전용)
- 비밀번호 변경

---

## 1. 백엔드

### 1.1 `withdrawn` status 추가

`app/models/user.py`의 `UserStatus` enum에 `withdrawn = "withdrawn"` 추가.
탈퇴한 계정 표시용. enum 값 추가이므로 SQLite dev.db는 테이블 재생성(또는 무관 — 문자열 저장).

### 1.2 프로필 사진 업로드 — `POST /me/profile-photo`

`app/api/me.py`에 추가. `verification.py`의 `upload_student_id` 패턴 그대로 따른다.

- multipart `file: UploadFile`
- content-type 검사: `image/jpeg`, `image/png`, `image/webp`만 허용 (아니면 400)
- 크기 제한 10MB (초과 시 400)
- `uploads/`에 `{uuid}.{ext}` 저장
- 기존 `profile_photo` 파일이 있으면 삭제 후 교체 (디스크 경로는 `os.path.basename`으로 복원)
- `current_user.profile_photo = f"/uploads/{filename}"` (URL 경로, 슬래시), commit
- 응답: `UserOut`

서빙: `main.py`에서 `uploads/`를 `/uploads`로 `StaticFiles` 마운트 → 프론트가 `${VITE_API_URL}${profile_photo}`로 `<img>` 로드. verification 이미지(admin 경로 확인만)와 달리 프로필 사진은 브라우저 표시가 필요해 OS 경로 대신 URL 경로로 저장(2026-06-20 결정).

상수(`ALLOWED_CONTENT_TYPES`, `MAX_FILE_SIZE`)는 verification.py와 동일 값. 중복을 피하려면 공용 위치로 뺄 수 있으나, 현 규모에선 me.py에 같은 상수를 두는 것으로 충분(YAGNI). 구현 시 판단.

### 1.3 회원 탈퇴 (익명화) — `DELETE /me`

`app/api/me.py`에 추가. soft delete = User 행 유지, 개인정보 제거.

탈퇴 처리:
- `email` → `withdrawn_{id}@deleted.local` (unique 제약 유지 + 원래 이메일 재가입 가능)
- `name` → `"탈퇴회원"`
- `password_hash` → 무작위 해시 (재로그인 불가)
- `instagram`, `kakao_id`, `phone`, `bio` → `None`
- `profile_photo` → `None` (저장된 파일도 삭제)
- `StudentVerification` 행 삭제 (이미지 파일도 삭제)
- `Survey` 행 삭제
- `status` → `withdrawn`
- commit

응답: 204 No Content.

근거: 매칭·신고·오작교·붉은실 테이블이 향후 user를 FK 참조할 수 있어 행 자체 삭제는 무결성 위험. 익명화로 개인정보보호법(연락처·학생증·설문 즉시 삭제) 충족하면서 참조 유지.

---

## 2. 프론트

### 2.1 `/mypage` — 마이페이지 (카드 그룹 레이아웃)

`src/pages/MyPage/`. 모바일 우선 390px, 디자인 토큰 사용.

구성(위→아래):
- **헤더**: 프로필 사진(없으면 기본 원형), 이름, 학교, status 뱃지
- **프로필 카드**: "프로필 수정"(→`/profile`), "가치관 설문"(비활성 — "준비중" 표시, 클릭 불가)
- **설정 카드**: "매칭 일시중지" 토글 → `PUT /me/matching-pause`
- **계정 카드**: "로그아웃"(context.logout → 랜딩), "회원 탈퇴"(확인 모달/confirm 후 `DELETE /me` → 토큰 삭제 → 랜딩)

### 2.2 `/profile` — 프로필 수정 폼

`src/pages/Profile/`.

- 상단 원형 사진 + 변경 버튼(파일 선택 → `POST /me/profile-photo`, 즉시 반영)
- 이름·학교: 읽기전용 표시
- 자기소개: textarea
- 연락처: instagram / kakao_id / phone 입력 3칸
- 검증: 연락처 3개 모두 비면 저장 막고 에러 표시 ("연락처를 1개 이상 입력하세요")
- 저장 → `PUT /me/profile` → context 갱신 → 마이페이지로 이동(또는 완료 표시)

### 2.3 공통

- `src/lib/api.ts`에 추가:
  - `fetchMe()` (이미 있으면 재사용)
  - `updateProfile(data)` → `PUT /me/profile`
  - `uploadProfilePhoto(file)` → `POST /me/profile-photo` (FormData, Content-Type 미설정 — 기존 FormData 처리 로직 활용)
  - `toggleMatchingPause(paused)` → `PUT /me/matching-pause`
  - `withdraw()` → `DELETE /me`
- `src/lib/auth.tsx`: 프로필 변경 후 context user 갱신용 `refreshUser()` 추가 (또는 `setUser` 노출)
- `src/lib/types.ts`: `UserStatus`에 `withdrawn` 반영(타입 union)
- 라우트(`App.tsx`): `/mypage`, `/profile` — 둘 다 `ProtectedRoute`(로그인 필요). status 요구는 안 둠(pending·active 모두 자기 정보 접근 가능).
- `withdrawn` 라우팅: 탈퇴 직후 토큰 삭제 + 랜딩 이동으로 처리. ProtectedRoute는 user 없으면 `/login`으로 보내므로 별도 분기 불필요.

---

## 3. 테스트 (TDD)

### 백엔드 (pytest)
- 사진 업로드: 성공(파일 저장·profile_photo 설정), 잘못된 content-type 400, 10MB 초과 400
- 탈퇴: 익명화 필드 검증(email·name·연락처·bio·photo), StudentVerification·Survey 행 삭제, status=withdrawn, 204

### 프론트 (vitest)
- 프로필 폼: 연락처 1개 이상 필수 검증
- 탈퇴 플로우: confirm 후 토큰 삭제·리다이렉트

---

## 미결/주의

- 가치관 설문 화면 미구현 — 마이페이지에 비활성 자리만. 설문 구현 시 활성화·연결.
- 프로덕션 파일 저장은 S3 교체 예정(현재 로컬 `uploads/`, verification과 동일).
- 학생증 업로드 화면(`/pending`)은 이번 범위 아님.
