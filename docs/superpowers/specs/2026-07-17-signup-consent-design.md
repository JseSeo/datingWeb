# 가입 동의 체크박스 — 설계 (Task B)

**작성: 2026-07-17**
**근거: 메인 스펙 `2026-05-23-datedrop-korea-design.md` §10 법적 준수 사항**

## 1. 목적

회원가입 시 법적 필수 동의(개인정보처리방침·이용약관)와 만 14세 미만 가입불가 고지를 추가하고, 동의 사실을 서버에 기록한다.

### 법적 근거

| 항목 | 근거 |
|------|------|
| 개인정보처리방침 동의 (필수) | 개인정보보호법 §15, §22 |
| 이용약관 동의 (필수) | 약관규제법 |
| 만 14세 미만 가입불가 고지 | 개인정보보호법 §22의2 |
| 동의 시각 서버 기록 | 개인정보보호법 §22 (처리자 입증책임) |

**핵심 결정:** 클라이언트 게이트만으로는 개보법 §22 입증책임을 충족 못 함 → 동의 시각을 DB에 기록(서버 기록 방식).

## 2. 범위

### 포함
- 회원가입 폼에 동의 체크박스 3종 + 전체동의 편의 체크
- 백엔드 동의 검증 + 동의 시각 DB 기록
- 약관/개인정보처리방침 보기 모달 (placeholder 문안)

### 제외 (YAGNI / 미결)
- **실제 약관·개인정보처리방침 문안** — 법적 효력 문서. 팀/변호사가 실제 수집항목·처리내용 확정 후 작성. 본 작업은 뼈대(모달·링크·기록)만.
- **마케팅/선택 동의** — 카카오 알림톡 미결. 생기면 별도 구조(동의상태 bool + 철회시각/이력)로 추가. 지금 필수 동의를 항목별로 쪼개도 마케팅 요건을 미리 못 채우므로 조기최적화.
- **약관 버전관리(개정 시 재동의)** — 문안이 placeholder라 버전 개념 없음. 문안 확정 시 별도 마이그레이션.
- **기존 유저 백필** — `terms_agreed_at` nullable, 기존 유저 NULL 유지.

## 3. 백엔드

### 3.1 스키마 — `app/schemas/auth.py`

`RegisterRequest`에 필드 3개 추가:

```python
agreed_terms: bool       # 이용약관 동의
agreed_privacy: bool     # 개인정보처리방침 동의
agreed_age_14: bool      # 만 14세 이상 확인
```

### 3.2 엔드포인트 — `app/api/auth.py` `register`

- 셋 중 하나라도 `False` → `HTTPException(status_code=400, detail="필수 약관에 동의해야 가입할 수 있습니다")`
- 통과 시 User 생성하며 `terms_agreed_at = datetime.utcnow()` 세팅

### 3.3 모델 — `app/models/user.py`

`User`에 컬럼 추가:

```python
terms_agreed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- nullable=True (기존 유저 NULL)
- Alembic autogenerate 마이그레이션 생성·적용

## 4. 프론트

### 4.1 가입 폼 — `frontend/src/pages/Register/Register.tsx`

폼 하단 동의 블록:

```
☐ 전체 동의
─────────────────────────
☐ [이용약관] 보기 · 동의 (필수)
☐ [개인정보처리방침] 보기 · 동의 (필수)
☐ 만 14세 이상입니다 (필수)

ⓘ 만 14세 미만은 가입할 수 없습니다
```

동작:
- **전체 동의** 체크 → 3개 일괄 on. 개별 하나라도 해제 → 전체동의 자동 해제.
- 3개 모두 체크 전에는 **가입 버튼 disabled** (1차 방어)
- 제출 시 `agreed_terms`, `agreed_privacy`, `agreed_age_14` 3개 bool을 register API로 전송

### 4.2 약관/방침 보기 — 모달

- `[이용약관]`, `[개인정보처리방침]` 링크 클릭 → **모달**로 문안 표시 (가입 흐름 안 끊김)
- 문안 = placeholder ("준비 중 — 팀 문안 확정 후 교체")
- 별도 라우트(`/terms`) 대신 모달 채택: 가입 이탈 방지

## 5. 데이터 흐름

```
[프론트] 3개 체크 (버튼 게이트)
   → POST /auth/register { email, pw, name, university, agreed_terms, agreed_privacy, agreed_age_14 }
   → [백엔드] 3개 bool 검증
        ├ 하나라도 false → 400
        └ 전부 true → User 생성 + terms_agreed_at = utcnow()
```

## 6. 에러 처리 (2단 방어)

| 단 | 위치 | 동작 |
|----|------|------|
| 1차 | 프론트 | 미체크 시 가입 버튼 disabled |
| 2차 | 백엔드 | 조작된 요청도 검증 거부 → 400 (입증책임 보장) |

## 7. 테스트

### 백엔드 (TDD)
- 동의 없이 가입 요청 → 400
- 일부만 동의(예: terms만 true) → 400
- 전부 동의 → 201 + 생성된 User의 `terms_agreed_at` 기록 확인

### 프론트
- 미체크 시 가입 버튼 disabled
- 전체동의 토글 → 3개 일괄 on/off
- 개별 하나 해제 → 전체동의 해제
- 3개 체크 시 버튼 활성

## 8. 파일 영향 요약

| 파일 | 변경 |
|------|------|
| `backend/app/schemas/auth.py` | RegisterRequest에 동의 필드 3개 |
| `backend/app/api/auth.py` | register 동의 검증 + terms_agreed_at 기록 |
| `backend/app/models/user.py` | terms_agreed_at 컬럼 |
| `backend/alembic/versions/*` | 마이그레이션 (autogenerate) |
| `frontend/src/pages/Register/Register.tsx` | 동의 블록 UI + 게이트 + API 전송 |
| 신규 프론트 컴포넌트 | 약관/방침 모달 (placeholder 문안) |
