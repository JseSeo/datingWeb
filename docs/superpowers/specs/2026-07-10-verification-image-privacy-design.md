# 학생증 이미지 비공개화 설계

**작성일:** 2026-07-10
**상태:** 설계 승인 완료 (구현 대기)
**배경:** `RESUME-verification-frontend.md` 프로덕션 필수 항목 #1

## 목표

학생증 인증 이미지의 개인정보 노출 두 지점을 제거한다.

1. **API JSON 서버경로 노출** — 현재 `VerificationOut.image_url`이 로컬 파일시스템 경로(`<upload_dir>/uuid.jpg`)를 그대로 클라이언트에 반환한다.
2. **무인증 공개 서빙** — 학생증 이미지가 `/uploads` 정적 mount(무인증)를 통해 UUID URL만 알면 누구나 fetch 가능하다. 개인정보보호법 대상인 학생증에 대한 실제 PII 노출 구멍.

## 비목표 (스코프 밖)

- **프로필 사진 무인증 서빙** — 프로필 사진도 같은 `/uploads` 무인증 mount를 사용하나, 학생증보다 덜 민감하고 이번 RESUME 항목은 학생증만 지목. 별도 이슈로 보류.
- **관리자 심사 UI** — 프론트 화면(승인/반려)은 RESUME 프로덕션 필수 #2, 별개 작업.
- **본인의 자기 학생증 재조회** — 현재 프론트는 저장된 학생증을 다시 보여주지 않음(재업로드 시 로컬 파일 미리보기만). YAGNI.

## 설계

### 1. 저장소 분리

- `config.py`에 새 설정 `verification_dir` 추가 (기본값 `"verification_uploads"`).
- 이 디렉토리는 **정적 mount 하지 않는다** (main.py의 `/uploads` mount와 분리).
- 학생증 파일은 `verification_dir`에 저장한다.
- 프로필 사진은 기존 `upload_dir` + `/uploads` 공개 mount 그대로 유지 (스코프 밖).
- **확장자 sanitize (write-traversal 차단):** 현재 verification 업로드는 파일명 확장자를 검증 없이 사용한다. me.py profile-photo와 동일하게 "영숫자·5자 이하"만 허용하도록 맞춘다. 미검증 시 `../` 섞인 확장자로 파일이 공개 `upload_dir`로 새어나갈 수 있어 이번 privacy 목표를 직접 훼손하므로 포함.

### 2. DB 저장 형식

- `StudentVerification.image_url` 컬럼은 **전체 경로 대신 파일명만** 저장한다 (예: `a1b2c3.jpg`).
- 컬럼명은 `image_url` 유지 — 리네임은 마이그레이션 비용 발생 + surgical 원칙 위반. 값의 의미만 "파일명"으로 변경.
- 컬럼 값은 삭제(withdraw)와 관리자 이미지 서빙에서 `verification_dir`와 join하여 사용.

### 3. 응답 스키마 — `VerificationOut`에서 `image_url` 필드 제거

- `VerificationOut`에서 `image_url` 필드를 완전히 제거한다.
- 이 스키마를 공유하는 세 엔드포인트 모두 영향:
  - `POST /verification/upload` 응답
  - `GET /me/verification` 응답
  - `GET /admin/verifications` 응답
- 프론트엔드는 `status`만 소비하므로 무해.
- 관리자는 verification row의 `id`로 이미지를 fetch한다 (row 존재 = 이미지 존재, 컬럼 `nullable=False`이므로 `id`만으로 충분).

응답 예시:

```json
{ "id": 1, "user_id": 1, "status": "pending", "reviewed_at": null, "created_at": "2026-07-10T00:00:00" }
```

### 4. 새 엔드포인트 — 인증 이미지 서빙

```
GET /admin/verifications/{id}/image
```

- 의존성: `require_admin` (관리자만).
- verification row 조회 → 없으면 404.
- `verification_dir`에서 `os.path.basename(verification.image_url)`로 파일 경로 구성 (경로 조작 차단).
- 파일 없으면 404.
- `FileResponse`로 반환 (media type은 확장자로 추론).

### 5. 삭제 경로 수정

- `me.py` withdraw 로직 (현재 `os.path.exists(verification.image_url)` 직접 사용) — DB가 파일명만 저장하므로 `os.path.join(settings.verification_dir, verification.image_url)`로 경로 구성 후 삭제.

## 영향 파일

| 파일 | 변경 |
|------|------|
| `backend/app/config.py` | `verification_dir` 설정 추가 |
| `backend/app/api/verification.py` | 저장 dir을 `verification_dir`로, DB에 파일명만 저장, 새 `GET /admin/verifications/{id}/image` 엔드포인트 |
| `backend/app/api/me.py` | withdraw 삭제 경로를 `verification_dir` 기준으로 |
| `backend/app/schemas/verification.py` | `VerificationOut`에서 `image_url` 필드 제거 |
| `frontend/src/lib/types.ts` | `VerificationOut` 인터페이스에서 `image_url` 제거 |
| `backend/tests/test_verification.py` | `image_url` 응답 미포함 검증, 새 이미지 엔드포인트 테스트(관리자 200 / 비관리자 403 / 없는 id 404) |
| `frontend/src/lib/api.verification.test.ts` 외 2개 | mock의 `image_url` 필드 제거 |

프론트 mock 참조 3곳: `api.verification.test.ts`, `Pending.test.tsx`, `UploadForm.test.tsx`.

## 테스트 전략

- **백엔드**
  - 업로드 응답에 `image_url` 필드가 **없음** 검증.
  - 업로드된 파일이 `verification_dir`에 저장되고 `/uploads`로는 접근 불가함(파일이 upload_dir에 없음) 검증.
  - `GET /admin/verifications/{id}/image`: 관리자 200 + 올바른 바이트, 비관리자 403, 존재하지 않는 id 404.
  - withdraw 시 `verification_dir`의 파일이 삭제됨 검증.
- **프론트엔드**
  - 기존 테스트가 `image_url` 없는 타입으로 통과하도록 mock 갱신 (`status` 기반 로직 불변).

## 마이그레이션 / 데이터 노트

- 기존 DB row는 옛 전체경로 포맷을 가질 수 있음. 개발 단계이며 실제 프로덕션 데이터 없음 → 데이터 마이그레이션 불필요.
- 스키마 변경은 컬럼 추가/삭제 없음(값 의미만 변경) → Alembic 마이그레이션 불필요.
- `config.py` 설정 추가는 기본값 있으므로 `.env` 변경 불필요.

## 성공 기준

1. 어떤 API 응답에도 서버 파일시스템 경로가 포함되지 않는다.
2. 학생증 이미지는 `require_admin` 없이는 접근 불가하다 (정적 URL로 fetch 불가).
3. 프로필 사진 기능은 영향 없이 동작한다.
4. 기존 프론트 41개 + 백엔드 verification 테스트가 갱신 후 전부 통과한다.
