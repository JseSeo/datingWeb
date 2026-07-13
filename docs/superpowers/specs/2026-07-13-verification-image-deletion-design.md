# 학생증 심사 완료 시 이미지 삭제 — 설계

**날짜:** 2026-07-13
**상태:** 설계 승인됨
**범위:** 백엔드 전용 (`backend/app/api/verification.py`)

## 배경

`backend/CLAUDE.md` 도메인규칙: **"학생증 이미지 — 승인 후 즉시 삭제 또는 암호화 보관 (개인정보보호법)"**.

현재 `review_verification` 엔드포인트는 승인/반려 시 `status`만 변경하고 이미지 파일을 삭제하지 않음 → 도메인규칙 위반. 심사 완료 후에도 학생증 이미지가 `verification_dir`에 무기한 잔존.

## 결정 사항

| 항목 | 결정 |
|------|------|
| 삭제 트리거 | **승인·반려 둘 다** — 심사 완료 = 목적 달성 = 즉시 삭제. 개인정보 최소보관 원칙 일관 적용 |
| DB `image_url` 필드 | **유지** (파일명 문자열 남김). 파일만 삭제. 마이그레이션 없음. 필드는 이미 API 응답에서 미노출(비공개화 작업) |
| 삭제 실패/파일없음 | 존재 체크 후 삭제 (멱등). 파일 없어도 에러 안 냄 |

## 동작

`review_verification` (backend/app/api/verification.py):

1. (기존) `payload.action`에 따라 status 세팅:
   - `approve` → `status=approved`, 해당 `user.status=active`
   - 그 외 → `status=rejected`
2. (기존) `reviewed_at`, `reviewed_by` 기록 후 `db.commit()`.
3. **(추가)** commit 후 이미지 파일 삭제:
   - 경로 계산은 `get_verification_image`과 동일 패턴:
     `os.path.join(settings.verification_dir, os.path.basename(verification.image_url))`
   - `os.path.exists`로 확인 후 존재하면 `os.remove`. 없으면 no-op.

`image_url` 필드값은 변경하지 않음 (dangling 파일명 문자열 유지, API 미노출).

## 엣지 케이스

- **파일 이미 없음** (재심사·중복 요청): 존재 체크로 안전. review 응답 200 정상.
- **GET `/admin/verifications/{id}/image`**: 삭제 후 파일 없으므로 404 반환. 프론트는 심사 후 카드를 낙관적 제거하므로 재조회 없음 → 정상 동작.

## 테스트 (TDD)

1. **승인 시 파일 삭제** — 업로드 후 approve → 디스크에서 파일 삭제됨 확인.
2. **반려 시 파일 삭제** — 업로드 후 reject → 파일 삭제됨 확인.
3. **멱등성** — 파일이 이미 없어도 review 200 성공.

## 범위 밖

- 재업로드(upsert) 시 이전 파일 orphan 누수 — 기존 별도 버그. 이 작업에서 다루지 않음.
- `image_url` nullable 전환 마이그레이션 — 불필요.
