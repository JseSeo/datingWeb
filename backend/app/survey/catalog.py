"""설문 문항 카탈로그 — 단일 진실원.

프론트엔드는 `GET /survey/questions`로 이 데이터를 받아 렌더한다.
문항 id는 `Survey.answers` JSON의 키로 그대로 저장되므로 **절대 바꾸지 않는다.**

명명 규칙: `X_pref`(원하는 상대) ↔ `X_self`(나) 로 짝을 이룬다.
매칭 점수 계산이 이 규칙으로 짝을 찾으므로 새 문항을 넣을 때 반드시 지킨다.
예외는 `grooming_self` 하나뿐이다 (짝 없음 → 매칭에 쓰지 않음).
"""

from dataclasses import dataclass
from enum import StrEnum


class Category(StrEnum):
    """카테고리별 가중치를 매기는 단위. 값은 매칭 알고리즘 설계 §3.4 참조."""

    APPEARANCE = "appearance"
    VALUES = "values"
    RELATIONSHIP = "relationship"
    LIFESTYLE = "lifestyle"


@dataclass(frozen=True)
class Choice:
    id: str
    label: str


@dataclass(frozen=True)
class FaceType:
    id: str
    label: str
    image: str


@dataclass(frozen=True)
class Question:
    id: str
    section: str  # "self" | "partner"
    label: str
    type: str  # single | multi | scale | number | ranking | image-single | image-multi
    category: Category
    choices: list[Choice] | None = None
    face: bool = False
    rank_items: list[Choice] | None = None
    scale_labels: tuple[str, str] | None = None
    unit: str | None = None
    min: int | None = None  # number 타입 전용. 검증기와 프론트 input이 함께 읽는다
    max: int | None = None
    male_only: bool = False
    no_pref_id: str | None = None


# TODO(운영 전 교체): 얼굴상 목록·이미지 미확정(에셋 의존).
FACE_ANY_ID = "any"

FACE_TYPES: list[FaceType] = [
    FaceType(id="type_a", label="강아지상", image="/faces/placeholder-a.png"),
    FaceType(id="type_b", label="고양이상", image="/faces/placeholder-b.png"),
    FaceType(id="type_c", label="곰상", image="/faces/placeholder-c.png"),
    FaceType(id="type_d", label="여우상", image="/faces/placeholder-d.png"),
]

# 시/도 17개 (행정표준). 운영 전 팀 대학목록과 별개.
SIDO: list[Choice] = [
    Choice(id=s, label=s)
    for s in (
        "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
        "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
    )
]

QUESTIONS: list[Question] = [
    # ── 6.1 외모·스타일 ──
    Question(
        id="height_self", section="self", label="내 키", type="number",
        category=Category.APPEARANCE, unit="cm", min=120, max=220,
    ),
    Question(
        id="height_pref", section="partner", label="원하는 상대 키", type="single",
        category=Category.APPEARANCE,
        choices=[
            Choice(id="u165", label="~165"),
            Choice(id="165_175", label="165~175"),
            Choice(id="175_185", label="175~185"),
            Choice(id="o185", label="185↑"),
            Choice(id="any", label="상관없음"),
        ],
        no_pref_id="any",
    ),
    Question(
        id="face_self", section="self", label="내 얼굴상", type="image-single",
        category=Category.APPEARANCE, face=True,
    ),
    Question(
        id="face_pref", section="partner", label="원하는 상대 얼굴상",
        type="image-multi", category=Category.APPEARANCE,
        face=True, no_pref_id=FACE_ANY_ID,
    ),
    Question(
        id="style_self", section="self", label="내 스타일", type="multi",
        category=Category.APPEARANCE,
        choices=[
            Choice(id="casual", label="캐주얼"),
            Choice(id="formal", label="포멀"),
            Choice(id="street", label="스트릿"),
            Choice(id="minimal", label="미니멀"),
            Choice(id="vintage", label="빈티지"),
        ],
    ),
    Question(
        id="style_pref", section="partner", label="원하는 상대 스타일", type="multi",
        category=Category.APPEARANCE,
        choices=[
            Choice(id="casual", label="캐주얼"),
            Choice(id="formal", label="포멀"),
            Choice(id="street", label="스트릿"),
            Choice(id="minimal", label="미니멀"),
            Choice(id="vintage", label="빈티지"),
            Choice(id="any", label="상관없음"),
        ],
        no_pref_id="any",
    ),
    Question(
        id="tattoo_self", section="self", label="내 문신 여부", type="single",
        category=Category.APPEARANCE,
        choices=[
            Choice(id="yes", label="있음"),
            Choice(id="no", label="없음"),
        ],
    ),
    Question(
        id="tattoo_pref", section="partner", label="문신 선호", type="single",
        category=Category.APPEARANCE,
        choices=[
            Choice(id="ok", label="있어도됨"),
            Choice(id="none", label="없었으면"),
            Choice(id="any", label="상관없음"),
        ],
        no_pref_id="any",
    ),
    Question(
        id="piercing_self", section="self", label="내 피어싱 여부", type="single",
        category=Category.APPEARANCE,
        choices=[
            Choice(id="yes", label="있음"),
            Choice(id="no", label="없음"),
        ],
    ),
    Question(
        id="piercing_pref", section="partner", label="피어싱 선호", type="single",
        category=Category.APPEARANCE,
        choices=[
            Choice(id="ok", label="있어도됨"),
            Choice(id="none", label="없었으면"),
            Choice(id="any", label="상관없음"),
        ],
        no_pref_id="any",
    ),
    Question(
        id="grooming_self", section="self", label="외모관리 습관", type="multi",
        category=Category.APPEARANCE, male_only=True,
        choices=[
            Choice(id="lotion", label="로션"),
            Choice(id="sunscreen", label="썬크림"),
            Choice(id="hair", label="머리손질"),
            Choice(id="makeup", label="화장"),
            Choice(id="nails", label="손톱관리"),
        ],
    ),

    # ── 6.2 가치관·신념 ──
    Question(
        id="politics_self", section="self", label="정치 성향", type="single",
        category=Category.VALUES,
        choices=[
            Choice(id="progressive", label="진보"),
            Choice(id="moderate", label="중도"),
            Choice(id="conservative", label="보수"),
            Choice(id="unknown", label="모름"),
        ],
    ),
    Question(
        id="politics_pref", section="partner", label="상대 정치 성향", type="single",
        category=Category.VALUES,
        choices=[
            Choice(id="progressive", label="진보"),
            Choice(id="moderate", label="중도"),
            Choice(id="conservative", label="보수"),
            Choice(id="any", label="상관없음"),
        ],
        no_pref_id="any",
    ),
    Question(
        id="religion_self", section="self", label="종교", type="single",
        category=Category.VALUES,
        choices=[
            Choice(id="none", label="무교"),
            Choice(id="christian", label="기독교"),
            Choice(id="catholic", label="천주교"),
            Choice(id="buddhist", label="불교"),
            Choice(id="other", label="기타"),
        ],
    ),
    Question(
        id="religion_pref", section="partner", label="상대 종교", type="multi",
        category=Category.VALUES,
        choices=[
            Choice(id="christian", label="기독교"),
            Choice(id="catholic", label="천주교"),
            Choice(id="buddhist", label="불교"),
            Choice(id="none", label="무교"),
            Choice(id="any", label="상관없음"),
        ],
        no_pref_id="any",
    ),

    # ── 6.3 관계·감정 ──
    Question(
        id="contact_freq_self", section="self", label="내 연락 빈도 성향",
        type="scale", category=Category.RELATIONSHIP,
        scale_labels=("가끔", "자주"),
    ),
    Question(
        id="contact_freq_pref", section="partner", label="원하는 상대 연락 빈도",
        type="scale", category=Category.RELATIONSHIP,
        scale_labels=("가끔", "자주"),
    ),
    Question(
        id="date_freq_self", section="self", label="내 데이트 빈도 성향",
        type="scale", category=Category.RELATIONSHIP,
        scale_labels=("가끔", "자주"),
    ),
    Question(
        id="date_freq_pref", section="partner", label="원하는 상대 데이트 빈도",
        type="scale", category=Category.RELATIONSHIP,
        scale_labels=("가끔", "자주"),
    ),
    Question(
        id="alone_time_self", section="self", label="내 개인시간 필요 정도",
        type="scale", category=Category.RELATIONSHIP,
        scale_labels=("적음", "많음"),
    ),
    Question(
        id="alone_time_pref", section="partner", label="원하는 상대 개인시간 필요 정도",
        type="scale", category=Category.RELATIONSHIP,
        scale_labels=("적음", "많음"),
    ),
    Question(
        id="affection_self", section="self", label="내 애정표현 정도",
        type="scale", category=Category.RELATIONSHIP,
        scale_labels=("은은", "적극"),
    ),
    Question(
        id="affection_pref", section="partner", label="원하는 상대 애정표현 정도",
        type="scale", category=Category.RELATIONSHIP,
        scale_labels=("은은", "적극"),
    ),
    Question(
        id="conflict_style_self", section="self", label="내 갈등 시 반응", type="single",
        category=Category.RELATIONSHIP,
        choices=[
            Choice(id="immediate", label="즉시품"),
            Choice(id="later", label="시간두고"),
            Choice(id="alone", label="혼자삭힘"),
        ],
    ),
    Question(
        id="conflict_style_pref", section="partner", label="원하는 상대 갈등 반응", type="single",
        category=Category.RELATIONSHIP,
        choices=[
            Choice(id="immediate", label="즉시품"),
            Choice(id="later", label="시간두고"),
            Choice(id="alone", label="혼자삭힘"),
            Choice(id="any", label="상관없음"),
        ],
        no_pref_id="any",
    ),
    Question(
        id="priority_rank_self", section="self", label="내 인생 우선순위",
        type="ranking", category=Category.RELATIONSHIP,
        rank_items=[
            Choice(id="lover", label="연인"),
            Choice(id="friend", label="친구"),
            Choice(id="self_dev", label="자기개발"),
            Choice(id="family", label="가족"),
        ],
    ),
    Question(
        id="priority_rank_pref", section="partner", label="원하는 상대 우선순위",
        type="ranking", category=Category.RELATIONSHIP,
        rank_items=[
            Choice(id="lover", label="연인"),
            Choice(id="friend", label="친구"),
            Choice(id="self_dev", label="자기개발"),
            Choice(id="family", label="가족"),
        ],
    ),

    # ── 6.4 경제·생활·건강 ──
    Question(
        id="date_budget_self", section="self", label="내 1회 데이트 예산", type="single",
        category=Category.LIFESTYLE,
        choices=[
            Choice(id="u5", label="5만↓"),
            Choice(id="5_10", label="5~10"),
            Choice(id="10_20", label="10~20"),
            Choice(id="20_30", label="20~30"),
            Choice(id="o30", label="30↑"),
        ],
    ),
    Question(
        id="date_budget_pref", section="partner", label="원하는 상대 예산", type="single",
        category=Category.LIFESTYLE,
        choices=[
            Choice(id="u5", label="5만↓"),
            Choice(id="5_10", label="5~10"),
            Choice(id="10_20", label="10~20"),
            Choice(id="20_30", label="20~30"),
            Choice(id="o30", label="30↑"),
            Choice(id="any", label="상관없음"),
        ],
        no_pref_id="any",
    ),
    Question(
        id="cost_share_self", section="self", label="내 비용부담 선호", type="single",
        category=Category.LIFESTYLE,
        choices=[
            Choice(id="dutch", label="더치"),
            Choice(id="alternate", label="번갈아"),
            Choice(id="richer", label="여유쪽더"),
            Choice(id="me", label="내가전담"),
        ],
    ),
    Question(
        id="cost_share_pref", section="partner", label="원하는 상대 비용부담", type="single",
        category=Category.LIFESTYLE,
        choices=[
            Choice(id="dutch", label="더치"),
            Choice(id="alternate", label="번갈아"),
            Choice(id="richer", label="여유쪽더"),
            Choice(id="partner", label="상대전담"),
            Choice(id="any", label="상관없음"),
        ],
        no_pref_id="any",
    ),
    Question(
        id="smoking_self", section="self", label="내 흡연", type="single",
        category=Category.LIFESTYLE,
        choices=[
            Choice(id="none", label="비흡연"),
            Choice(id="sometimes", label="가끔"),
            Choice(id="yes", label="흡연"),
        ],
    ),
    Question(
        id="smoking_pref", section="partner", label="상대 흡연 선호", type="single",
        category=Category.LIFESTYLE,
        choices=[
            Choice(id="none_only", label="비흡연만"),
            Choice(id="sometimes_ok", label="가끔OK"),
            Choice(id="any", label="상관없음"),
        ],
        no_pref_id="any",
    ),
    Question(
        id="drinking_self", section="self", label="내 음주 빈도", type="single",
        category=Category.LIFESTYLE,
        choices=[
            Choice(id="none", label="안함"),
            Choice(id="sometimes", label="가끔"),
            Choice(id="often", label="자주"),
        ],
    ),
    Question(
        id="drinking_pref", section="partner", label="상대 음주 선호", type="single",
        category=Category.LIFESTYLE,
        choices=[
            Choice(id="none", label="안함"),
            Choice(id="sometimes_ok", label="가끔OK"),
            Choice(id="any", label="상관없음"),
        ],
        no_pref_id="any",
    ),
    Question(
        id="exercise_self", section="self", label="내 운동 빈도", type="single",
        category=Category.LIFESTYLE,
        choices=[
            Choice(id="none", label="안함"),
            Choice(id="w1_2", label="주1~2"),
            Choice(id="w3", label="주3↑"),
        ],
    ),
    Question(
        id="exercise_pref", section="partner", label="상대 운동 선호", type="single",
        category=Category.LIFESTYLE,
        choices=[
            Choice(id="none", label="안함"),
            Choice(id="w1_2", label="주1~2"),
            Choice(id="w3", label="주3↑"),
            Choice(id="any", label="상관없음"),
        ],
        no_pref_id="any",
    ),
    Question(
        id="sleep_self", section="self", label="내 수면 패턴", type="single",
        category=Category.LIFESTYLE,
        choices=[
            Choice(id="morning", label="아침형"),
            Choice(id="night", label="올빼미"),
            Choice(id="irregular", label="불규칙"),
        ],
    ),
    Question(
        id="sleep_pref", section="partner", label="상대 수면 선호", type="single",
        category=Category.LIFESTYLE,
        choices=[
            Choice(id="morning", label="아침형"),
            Choice(id="night", label="올빼미"),
            Choice(id="irregular", label="불규칙"),
            Choice(id="any", label="상관없음"),
        ],
        no_pref_id="any",
    ),
    Question(
        id="hobby_self", section="self", label="내 취미 성향", type="single",
        category=Category.LIFESTYLE,
        choices=[
            Choice(id="indoor", label="실내"),
            Choice(id="outdoor", label="실외"),
            Choice(id="both", label="둘다"),
        ],
    ),
    Question(
        id="hobby_pref", section="partner", label="상대 취미 선호", type="single",
        category=Category.LIFESTYLE,
        choices=[
            Choice(id="indoor", label="실내"),
            Choice(id="outdoor", label="실외"),
            Choice(id="any", label="상관없음"),
        ],
        no_pref_id="any",
    ),
    Question(
        id="residence_self", section="self", label="내 거주지", type="single",
        category=Category.LIFESTYLE, choices=SIDO,
    ),
    Question(
        id="residence_pref", section="partner", label="허용 이동거리", type="single",
        category=Category.LIFESTYLE,
        choices=[
            Choice(id="h1", label="차로 1시간↓"),
            Choice(id="h2", label="2시간↓"),
            Choice(id="h3", label="3시간↓"),
            Choice(id="any", label="상관없음"),
        ],
        no_pref_id="any",
    ),
    Question(
        id="living_self", section="self", label="내 자취 여부", type="single",
        category=Category.LIFESTYLE,
        choices=[
            Choice(id="independent", label="자취"),
            Choice(id="home", label="본가"),
            Choice(id="dorm", label="기숙사"),
        ],
    ),
    Question(
        id="living_pref", section="partner", label="상대 자취 선호", type="single",
        category=Category.LIFESTYLE,
        choices=[
            Choice(id="prefer_independent", label="자취선호"),
            Choice(id="any", label="상관없음"),
        ],
        no_pref_id="any",
    ),
]
