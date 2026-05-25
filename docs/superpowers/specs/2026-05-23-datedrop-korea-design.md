# DateDrop Korea — 전체 설계 문서

**작성일:** 2026-05-23  
**상태:** 매칭 알고리즘 보류 외 전체 확정

---

## 1. 프로젝트 개요

한국 대학생 대상 주간 소개팅 매칭 웹서비스. 스탠퍼드 DateDrop 벤치마킹.  
핵심 가치: 설레는 기다림 (주간 매칭 공개), 신뢰 (학생 인증), 재미 (게임 요소).

---

## 2. 기술 스택

| 레이어 | 기술 |
|---|---|
| 프론트엔드 | React (Vite) |
| 백엔드 | Python FastAPI |
| DB | PostgreSQL |
| ORM | SQLAlchemy |
| 프론트 배포 | Vercel |
| 백엔드 배포 | Railway |
| 알림 | 카카오 알림톡 (사업자등록 완료 후 연동) |

---

## 3. 디자인 시스템

- **컬러 팔레트:** 크림(#FFF5E6) + 코랄(#FF7F5C) + 오렌지(#FF9472)
- **UI 스타일:** 클린 미니멀 — 직선 위주, 타이포그래피 강조
- **레이아웃:** 모바일 우선 반응형 (max-width 390px 기준 설계, PC는 중앙 정렬 컨테이너)

---

## 4. 인증 및 접근 제어

- 대상: 한국 내 16개 대학 재학생 (대학 목록 팀 내부 선정 예정)
- 학생증 사진 업로드 → 관리자 수동 승인
- 승인 전: 서비스 전면 이용 제한 (대기 화면)
- 승인 후: 전체 기능 개방

---

## 5. 매칭 시스템

### 5.1 기본 구조
- 주 1회 특정 요일+시간에 일괄 매칭 (요일/시간 미결 — 팀 결정 필요)
- 매칭 결과: 카카오 알림톡으로만 전달 (인앱 결과 페이지 없음)
- 알림 내용: 상대방이 기입한 연락처(인스타/카톡ID/전화번호 중 1개 이상)

### 5.2 매칭 알고리즘
- **보류** — 팀 회의 후 별도 설계. 재개 명령: "매칭 알고리즘 설계 시작해"
- 확정된 것: 가치관 설문 기반 가중치 매칭 방향

### 5.3 매칭 확률 수정자 (게임 연동)
- 오작교 추천 1명 수신 시: +33%
- 오작교 추천 3명 수신 시: 100% 보장
- 붉은 실 상호 입력 시: 100% 보장
- 중복 매칭 방지 로직: 매칭 알고리즘 설계 시 결정

---

## 6. 게임 시스템

### 6.1 오작교 게임
- 목적: 신규 유저 유입 (가입 유도)
- 방식: 기존 유저가 지인에게 추천 링크 발송 → 가입 시 추천인의 매칭 확률 +33%
- 추천인: 익명 (피추천인에게 비공개)
- 반영 시점: 해당 주 정규 매칭에 반영

### 6.2 붉은 실 게임
- 목적: 아는 사람과의 확실한 연결
- 방식: 가입 회원끼리 서로 상대방 이름+학교 입력 → 양쪽 모두 입력 시 100% 매칭
- 반영 시점: 해당 주 정규 매칭에 반영
- 단방향 입력 시: 상대방 미입력 상태로 대기 (알림 없음)

---

## 7. 화면 목록

| 화면 | 설명 |
|---|---|
| 랜딩페이지 | 서비스 소개, 가입 유도 CTA |
| 회원가입 | 기본 정보 입력 + 학생증 업로드 |
| 인증 대기 | 관리자 승인 대기 화면 |
| 로그인 | 이메일+비밀번호 |
| 가치관 설문 | 매칭 알고리즘용 설문 + 연락처 입력(인스타/카톡ID/전화번호 중 1개 이상) |
| 프로필 설정 | 사진(선택), 자기소개 등. 미입력 시 응답률 저하 경고 |
| 홈/메인 | 현재 매칭 상태, 다음 매칭 D-day 카운트다운 |
| 게임 탭 | 오작교 게임 + 붉은 실 게임 |
| 마이페이지 | 프로필 수정, 설문 수정, 매칭 일시정지 토글 |
| 관리자 탭 | 숨김 경로. 학생증 승인, 매칭 실행, 유저 관리 |
| 신고 & 건의 | 부적절 유저 신고, 서비스 건의 |

---

## 8. 데이터 모델 (주요 엔티티)

```
User
  id, email, password_hash, name, university, student_id, status(pending/active/suspended)
  profile_photo(nullable), bio(nullable)
  instagram(nullable), kakao_id(nullable), phone(nullable)  -- 1개 이상 필수
  matching_paused(bool), created_at

StudentVerification
  id, user_id, image_url, status(pending/approved/rejected), reviewed_at, reviewed_by

Survey
  id, user_id, answers(JSONB), updated_at

Match
  id, user_a_id, user_b_id, matched_at, match_round_id

MatchRound
  id, scheduled_at, executed_at, status(pending/done)

Ojakgyo (오작교)
  id, referrer_id, referee_id(nullable -- 미가입이면 null), invite_token, created_at

RedThread (붉은 실)
  id, user_id, target_name, target_university, created_at

Report
  id, reporter_id, target_id, reason, created_at
```

---

## 9. API 구조 (주요 엔드포인트)

```
POST /auth/register
POST /auth/login
POST /auth/logout

GET  /me
PUT  /me/profile
PUT  /me/survey
PUT  /me/matching-pause

POST /verification/upload         -- 학생증 업로드
GET  /admin/verifications         -- 관리자: 승인 대기 목록
POST /admin/verifications/{id}    -- 관리자: 승인/거절

POST /game/ojakgyo/invite         -- 추천 링크 생성
POST /game/ojakgyo/accept         -- 추천 수락 (가입 시)
POST /game/red-thread             -- 붉은 실 입력
GET  /game/red-thread/status      -- 상호 입력 여부 확인

POST /admin/match/run             -- 관리자: 매칭 실행
GET  /admin/matches               -- 관리자: 매칭 결과

POST /reports                     -- 신고
```

---

## 10. 법적 준수 사항

- 가입 시 개인정보처리방침 + 이용약관 동의 필수 (체크박스)
- 학생증 이미지: 승인 후 즉시 삭제 또는 암호화 보관 (개인정보보호법)
- 회원 탈퇴 시: 개인정보 즉시 삭제 (연락처, 학생증, 설문 포함)
- 만 14세 미만 가입 불가 고지

---

## 11. 미결 항목

| 항목 | 비고 |
|---|---|
| 매칭 요일/시간 | 팀 결정 필요 |
| 매칭 알고리즘 상세 | 팀 회의 후 별도 설계 |
| 16개 대학 목록 | 팀 내부 선정 |
| 카카오 알림톡 연동 | 사업자등록증 발급 후 |
