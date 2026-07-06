# 학생증 인증 업로드 프론트 — 설계

**날짜:** 2026-07-06
**대상:** 가입 후 `pending` 유저가 학생증을 올리고 심사 상태를 확인하는 프론트 화면
**브랜치(예정):** 신규 feature 브랜치

## 배경 / 문제

현재 흐름이 깨져 있음:

- 가입 → `user.status = pending` → 자동으로 `/pending`(승인대기) 화면 이동
- `/pending` 화면은 "학생증 인증이 검토 중입니다"라고 표시 — **그러나 학생증을 올릴 UI가 어디에도 없음**
- 백엔드 `POST /verification/upload`(업로드), `GET/POST /admin/verifications`(관리자 심사)는 이미 존재하나 **프론트 미연결**
- 백엔드에 **본인 인증 상태 조회 GET 엔드포인트가 없어** 프론트가 "안 올림 / 심사중 / 반려됨"을 구분 불가

## 목표

`/pending` 화면을 상태기계로 개조해 업로드 폼 + 심사 상태를 제공. 반려 시 재업로드 가능. 승인되면 홈으로 이동.

**비목표(스코프 밖):** 관리자 심사 UI(`/admin`), `image_url` 서버경로 노출 개선, 매칭/설문.

## 백엔드 계약 (기존)

`POST /verification/upload` (multipart, field `file`, 인증 필요):
- content-type ∈ {image/jpeg, image/png, image/webp} 아니면 400 `"JPG, PNG, WEBP 파일만 업로드 가능합니다"`
- 용량 > 10MB면 400 `"파일 크기는 10MB 이하여야 합니다"`
- upsert: 재제출 시 덮어쓰기, status → pending 리셋
- 201 `VerificationOut { id, user_id, image_url, status, reviewed_at, created_at }`

`VerificationStatus = pending | approved | rejected`. 관리자 approve 시 `user.status → active`.

## 설계

### 1. 백엔드 추가 — `GET /me/verification`

기존 `/me/survey` GET 패턴 그대로. 본인 인증 상태 조회.

- 인증 필요(`get_current_user`)
- verification 있으면 `VerificationOut`(200), **없으면 `null`(200)**
- `response_model=VerificationOut | None`
- **왜 404 아닌 null:** "아직 안 올림"은 정상 초기 상태 → 프론트가 에러처리로 다루지 않게 200+null이 깔끔
- `image_url`(서버 경로)이 응답에 포함되나 프론트는 `status`만 소비. 경로 노출은 기존 POST 응답과 동일한 별도 이슈 → 이번 스코프 밖

### 2. 프론트 타입 + api 함수 (`frontend/src/lib`)

타입 추가:
```ts
type VerificationStatus = "pending" | "approved" | "rejected";
interface VerificationOut {
  id: number;
  user_id: number;
  image_url: string;
  status: VerificationStatus;
  reviewed_at: string | null;
  created_at: string;
}
```

api 함수 추가 (`api.ts`):
```ts
getMyVerification(): Promise<VerificationOut | null>   // GET /me/verification
uploadVerification(file: File): Promise<VerificationOut> // POST /verification/upload, FormData
```

`uploadVerification`은 기존 `uploadProfilePhoto` 선례 그대로 `FormData` 사용. `apiFetch`는 body가 FormData면 Content-Type을 자동 생략함(검증 완료).

### 3. `Pending` 화면 = 상태기계

마운트 시 `fetchMe()`(status) + `getMyVerification()` 병렬 조회 → 분기:

| 조건 | 렌더 |
|------|------|
| 로딩 중 | "확인 중…" |
| user.status === active | `/home` 리다이렉트 (승인 완료) |
| verification === null | 안내 "학생증을 올려주세요" + **업로드 폼** |
| status === pending | "검토 중입니다" + 재업로드 폼(펼침) |
| status === rejected | "반려됐어요. 다시 올려주세요" + **업로드 폼** |

- 승인 감지 = **마운트 시 1회 체크만**(폴링 없음). 심사는 admin 수동이라 실시간 불필요. 유저 재방문/재로그인 시 자동 이동.
- 기존 로그아웃 버튼 유지.

### 4. 업로드 폼 컴포넌트 (Pending 내부)

- `<input type="file" accept="image/*">`
- 파일 선택 시 `URL.createObjectURL`로 썸네일 미리보기 (unmount/재선택 시 `revokeObjectURL`)
- **클라 검증(제출 전):** 타입 ∈ {jpg,png,webp}, 용량 ≤ 10MB. 위반 시 인라인 에러 표시하고 제출 차단
- 제출 → 성공 시 verification 상태를 응답값(pending)으로 갱신, "제출됐어요" 안내
- 백엔드 400 `detail`도 인라인 에러로 표시(방어)

### 5. 에러 / 색상 / 테스트

- 색상: 기존 정책 재사용 — 에러 `#d33`, 안내 `#666`, 토큰 코랄 `#FF7F5C`. 임의 색 추가 금지
- 반응형: 기존 max-width 390px 모바일 우선 유지

**테스트 (TDD):**
- 백엔드: `GET /me/verification` — 미제출 시 null 반환 / 제출 후 해당 레코드 반환 / 미인증 401
- 프론트:
  - 클라 검증 — 잘못된 타입 거부, 10MB 초과 거부(제출 안 감)
  - 상태별 렌더 4종(null / pending / rejected / active→redirect)
  - 업로드 성공 → pending 전환 + "제출됐어요"
  - 백엔드 400 detail 인라인 표시

## 성공 기준

- pending 유저가 `/pending`에서 학생증 올릴 수 있음
- 반려 시 재업로드 가능
- 승인 시 재방문하면 홈으로 이동
- 잘못된 파일(타입/용량)은 제출 전 막힘
- 백엔드 GET/프론트 테스트 전부 통과, build clean
