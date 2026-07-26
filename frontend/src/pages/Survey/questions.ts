import type { Question } from "./types";
import { FACE_ANY_ID } from "./faceTypes";

// 단일 진실원(§6 design doc, 45문항). 백엔드는 이 카탈로그를 모른다.
// 시/도 17개 (행정표준). 운영 전 팀 대학목록과 별개.
const SIDO = [
  "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
  "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
].map((s) => ({ id: s, label: s }));

export const QUESTIONS: Question[] = [
  // ── 6.1 외모·스타일 ──
  { id: "height_self", section: "self", label: "내 키", type: "number", unit: "cm" },
  { id: "height_pref", section: "partner", label: "원하는 상대 키", type: "single",
    choices: [
      { id: "u165", label: "~165" }, { id: "165_175", label: "165~175" },
      { id: "175_185", label: "175~185" }, { id: "o185", label: "185↑" },
      { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "face_self", section: "self", label: "내 얼굴상", type: "image-single", face: true },
  { id: "face_pref", section: "partner", label: "원하는 상대 얼굴상", type: "image-multi",
    face: true, noPrefId: FACE_ANY_ID },
  { id: "style_self", section: "self", label: "내 스타일", type: "multi",
    choices: [
      { id: "casual", label: "캐주얼" }, { id: "formal", label: "포멀" },
      { id: "street", label: "스트릿" }, { id: "minimal", label: "미니멀" },
      { id: "vintage", label: "빈티지" },
    ] },
  { id: "style_pref", section: "partner", label: "원하는 상대 스타일", type: "multi",
    choices: [
      { id: "casual", label: "캐주얼" }, { id: "formal", label: "포멀" },
      { id: "street", label: "스트릿" }, { id: "minimal", label: "미니멀" },
      { id: "vintage", label: "빈티지" }, { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "tattoo_self", section: "self", label: "내 문신 여부", type: "single",
    choices: [{ id: "yes", label: "있음" }, { id: "no", label: "없음" }] },
  { id: "tattoo_pref", section: "partner", label: "문신 선호", type: "single",
    choices: [
      { id: "ok", label: "있어도됨" }, { id: "none", label: "없었으면" },
      { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "piercing_self", section: "self", label: "내 피어싱 여부", type: "single",
    choices: [{ id: "yes", label: "있음" }, { id: "no", label: "없음" }] },
  { id: "piercing_pref", section: "partner", label: "피어싱 선호", type: "single",
    choices: [
      { id: "ok", label: "있어도됨" }, { id: "none", label: "없었으면" },
      { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "grooming_self", section: "self", label: "외모관리 습관", type: "multi", maleOnly: true,
    choices: [
      { id: "lotion", label: "로션" }, { id: "sunscreen", label: "썬크림" },
      { id: "hair", label: "머리손질" }, { id: "makeup", label: "화장" },
      { id: "nails", label: "손톱관리" },
    ] },

  // ── 6.2 가치관·신념 ──
  { id: "politics_self", section: "self", label: "정치 성향", type: "single",
    choices: [
      { id: "progressive", label: "진보" }, { id: "moderate", label: "중도" },
      { id: "conservative", label: "보수" }, { id: "unknown", label: "모름" },
    ] },
  { id: "politics_pref", section: "partner", label: "상대 정치 성향", type: "single",
    choices: [
      { id: "progressive", label: "진보" }, { id: "moderate", label: "중도" },
      { id: "conservative", label: "보수" }, { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "religion_self", section: "self", label: "종교", type: "single",
    choices: [
      { id: "none", label: "무교" }, { id: "christian", label: "기독교" },
      { id: "catholic", label: "천주교" }, { id: "buddhist", label: "불교" },
      { id: "other", label: "기타" },
    ] },
  { id: "religion_pref", section: "partner", label: "상대 종교", type: "multi",
    choices: [
      { id: "christian", label: "기독교" }, { id: "catholic", label: "천주교" },
      { id: "buddhist", label: "불교" }, { id: "none", label: "무교" },
      { id: "any", label: "상관없음" },
    ], noPrefId: "any" },

  // ── 6.3 관계·감정 ──
  { id: "contact_freq_self", section: "self", label: "내 연락 빈도 성향", type: "scale",
    scaleLabels: ["가끔", "자주"] },
  { id: "contact_freq_pref", section: "partner", label: "원하는 상대 연락 빈도", type: "scale",
    scaleLabels: ["가끔", "자주"] },
  { id: "date_freq_self", section: "self", label: "내 데이트 빈도 성향", type: "scale",
    scaleLabels: ["가끔", "자주"] },
  { id: "date_freq_pref", section: "partner", label: "원하는 상대 데이트 빈도", type: "scale",
    scaleLabels: ["가끔", "자주"] },
  { id: "alone_time_self", section: "self", label: "내 개인시간 필요 정도", type: "scale",
    scaleLabels: ["적음", "많음"] },
  { id: "alone_time_pref", section: "partner", label: "원하는 상대 개인시간 필요 정도", type: "scale",
    scaleLabels: ["적음", "많음"] },
  { id: "affection_self", section: "self", label: "내 애정표현 정도", type: "scale",
    scaleLabels: ["은은", "적극"] },
  { id: "affection_pref", section: "partner", label: "원하는 상대 애정표현 정도", type: "scale",
    scaleLabels: ["은은", "적극"] },
  { id: "conflict_style_self", section: "self", label: "내 갈등 시 반응", type: "single",
    choices: [
      { id: "immediate", label: "즉시품" }, { id: "later", label: "시간두고" },
      { id: "alone", label: "혼자삭힘" },
    ] },
  { id: "conflict_style_pref", section: "partner", label: "원하는 상대 갈등 반응", type: "single",
    choices: [
      { id: "immediate", label: "즉시품" }, { id: "later", label: "시간두고" },
      { id: "alone", label: "혼자삭힘" }, { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "priority_rank_self", section: "self", label: "내 인생 우선순위", type: "ranking",
    rankItems: [
      { id: "lover", label: "연인" }, { id: "friend", label: "친구" },
      { id: "self_dev", label: "자기개발" }, { id: "family", label: "가족" },
    ] },
  { id: "priority_rank_pref", section: "partner", label: "원하는 상대 우선순위", type: "ranking",
    rankItems: [
      { id: "lover", label: "연인" }, { id: "friend", label: "친구" },
      { id: "self_dev", label: "자기개발" }, { id: "family", label: "가족" },
    ] },

  // ── 6.4 경제·생활·건강 ──
  { id: "date_budget_self", section: "self", label: "내 1회 데이트 예산", type: "single",
    choices: [
      { id: "u5", label: "5만↓" }, { id: "5_10", label: "5~10" },
      { id: "10_20", label: "10~20" }, { id: "20_30", label: "20~30" },
      { id: "o30", label: "30↑" },
    ] },
  { id: "date_budget_pref", section: "partner", label: "원하는 상대 예산", type: "single",
    choices: [
      { id: "u5", label: "5만↓" }, { id: "5_10", label: "5~10" },
      { id: "10_20", label: "10~20" }, { id: "20_30", label: "20~30" },
      { id: "o30", label: "30↑" }, { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "cost_share_self", section: "self", label: "내 비용부담 선호", type: "single",
    choices: [
      { id: "dutch", label: "더치" }, { id: "alternate", label: "번갈아" },
      { id: "richer", label: "여유쪽더" }, { id: "me", label: "내가전담" },
    ] },
  { id: "cost_share_pref", section: "partner", label: "원하는 상대 비용부담", type: "single",
    choices: [
      { id: "dutch", label: "더치" }, { id: "alternate", label: "번갈아" },
      { id: "richer", label: "여유쪽더" }, { id: "partner", label: "상대전담" },
      { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "smoking_self", section: "self", label: "내 흡연", type: "single",
    choices: [
      { id: "none", label: "비흡연" }, { id: "sometimes", label: "가끔" },
      { id: "yes", label: "흡연" },
    ] },
  { id: "smoking_pref", section: "partner", label: "상대 흡연 선호", type: "single",
    choices: [
      { id: "none_only", label: "비흡연만" }, { id: "sometimes_ok", label: "가끔OK" },
      { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "drinking_self", section: "self", label: "내 음주 빈도", type: "single",
    choices: [
      { id: "none", label: "안함" }, { id: "sometimes", label: "가끔" },
      { id: "often", label: "자주" },
    ] },
  { id: "drinking_pref", section: "partner", label: "상대 음주 선호", type: "single",
    choices: [
      { id: "none", label: "안함" }, { id: "sometimes_ok", label: "가끔OK" },
      { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "exercise_self", section: "self", label: "내 운동 빈도", type: "single",
    choices: [
      { id: "none", label: "안함" }, { id: "w1_2", label: "주1~2" },
      { id: "w3", label: "주3↑" },
    ] },
  { id: "exercise_pref", section: "partner", label: "상대 운동 선호", type: "single",
    choices: [
      { id: "none", label: "안함" }, { id: "w1_2", label: "주1~2" },
      { id: "w3", label: "주3↑" }, { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "sleep_self", section: "self", label: "내 수면 패턴", type: "single",
    choices: [
      { id: "morning", label: "아침형" }, { id: "night", label: "올빼미" },
      { id: "irregular", label: "불규칙" },
    ] },
  { id: "sleep_pref", section: "partner", label: "상대 수면 선호", type: "single",
    choices: [
      { id: "morning", label: "아침형" }, { id: "night", label: "올빼미" },
      { id: "irregular", label: "불규칙" }, { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "hobby_self", section: "self", label: "내 취미 성향", type: "single",
    choices: [
      { id: "indoor", label: "실내" }, { id: "outdoor", label: "실외" },
      { id: "both", label: "둘다" },
    ] },
  { id: "hobby_pref", section: "partner", label: "상대 취미 선호", type: "single",
    choices: [
      { id: "indoor", label: "실내" }, { id: "outdoor", label: "실외" },
      { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "residence_self", section: "self", label: "내 거주지", type: "single", choices: SIDO },
  { id: "residence_pref", section: "partner", label: "허용 이동거리", type: "single",
    choices: [
      { id: "h1", label: "차로 1시간↓" }, { id: "h2", label: "2시간↓" },
      { id: "h3", label: "3시간↓" }, { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "living_self", section: "self", label: "내 자취 여부", type: "single",
    choices: [
      { id: "independent", label: "자취" }, { id: "home", label: "본가" },
      { id: "dorm", label: "기숙사" },
    ] },
  { id: "living_pref", section: "partner", label: "상대 자취 선호", type: "single",
    choices: [
      { id: "prefer_independent", label: "자취선호" }, { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
];
