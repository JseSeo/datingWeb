# Frontend — React (Vite)

React + Vite. 모바일 우선 반응형.

## 개발 명령

```bash
npm run dev      # 개발 서버
npm run build    # 빌드
npm run preview  # 빌드 결과 미리보기
```

## 디자인 시스템

| 항목 | 값 |
|------|-----|
| 배경 (크림) | `#FFF5E6` |
| 주 강조 (코랄) | `#FF7F5C` |
| 보조 강조 (오렌지) | `#FF9472` |
| 기준 너비 | max-width 390px (모바일 우선) |
| PC | 중앙 정렬 컨테이너 |
| 스타일 | 클린 미니멀. 직선 위주, 타이포그래피 강조 |

## 화면 목록

| 화면 | 경로 (예정) |
|------|------------|
| 랜딩 | `/` |
| 회원가입 | `/register` |
| 인증 대기 | `/pending` |
| 로그인 | `/login` |
| 가치관 설문 | `/survey` |
| 프로필 설정 | `/profile` |
| 홈/메인 | `/home` |
| 게임 탭 | `/game` |
| 마이페이지 | `/mypage` |
| 관리자 탭 | `/admin` (숨김 경로) |
| 신고 & 건의 | `/report` |

## 코딩 규칙

| 규칙 | 내용 |
|------|------|
| API URL | `VITE_API_URL` 환경변수 사용. 하드코딩 금지 |
| 인증 토큰 | JWT localStorage 저장 |
| 라우팅 | pending 유저 → `/pending` redirect. active만 전체 접근 |
| 컴포넌트 | 페이지 단위 폴더 구조 (`src/pages/`) |
| 디자인 토큰 | 위 색상 외 임의 색상 사용 금지 |
