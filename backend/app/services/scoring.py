"""설문 응답 → 궁합 점수. DB를 모른다 (설계 §2.1).

용어
  responses : {문항id: 값}                        = Survey.answers["responses"]
  answers   : {"responses": {...}, "absolute": [...]} = Survey.answers 전체
"""

from collections import deque

from app.survey.catalog import QUESTIONS, Category, Question

# 설계 §3.4. 운영 데이터가 쌓이면 조정한다
CATEGORY_WEIGHT: dict[Category, float] = {
    Category.VALUES: 1.5,
    Category.RELATIONSHIP: 1.3,
    Category.LIFESTYLE: 1.0,
    Category.APPEARANCE: 0.8,
}

_BY_ID: dict[str, Question] = {q.id: q for q in QUESTIONS}
_PREF_SUFFIX = "_pref"


def _build_pairs() -> dict[str, tuple[Question, Question]]:
    """`X_pref` ↔ `X_self` 짝을 카탈로그에서 뽑는다. 짝 없는 _pref는 설정 오류다."""
    pairs: dict[str, tuple[Question, Question]] = {}
    for q in QUESTIONS:
        if not q.id.endswith(_PREF_SUFFIX):
            continue
        base = q.id[: -len(_PREF_SUFFIX)]
        self_q = _BY_ID.get(f"{base}_self")
        if self_q is None:
            raise ValueError(f"짝이 없는 _pref 문항: {q.id}")
        pairs[base] = (q, self_q)
    return pairs


PAIRS: dict[str, tuple[Question, Question]] = _build_pairs()


# ── 값 도우미 ──────────────────────────────────────────────

def _as_list(value) -> list:
    if isinstance(value, list):
        return value
    return [] if value is None else [value]


def _is_empty(value) -> bool:
    return value is None or value == "" or (isinstance(value, list) and not value)


def _is_no_pref(question: Question, value) -> bool:
    if question.no_pref_id is None:
        return False
    if value == question.no_pref_id:
        return True
    return isinstance(value, list) and question.no_pref_id in value


def _step(diff: int) -> float:
    """순서형 3단계 공통: 차이 0→1.0, 1→0.5, 2 이상→0.0"""
    return {0: 1.0, 1: 0.5}.get(diff, 0.0)


def _ordinal(order: dict[str, int]):
    def rule(pref, self_value):
        i, j = order.get(pref), order.get(self_value)
        if i is None or j is None:
            return None
        return _step(abs(i - j))
    return rule


def _table(table: dict[str, dict[str, float]]):
    """행=pref, 열=self 매핑표. 표에 없는 값이면 판정 불가(None)."""
    def rule(pref, self_value):
        row = table.get(pref)
        return None if row is None else row.get(self_value)
    return rule


# ── 문항별 규칙 (설계 §3.2) ────────────────────────────────

_HEIGHT_PREF_INDEX = {"u165": 0, "165_175": 1, "175_185": 2, "o185": 3}


def _height_index(cm) -> int | None:
    if isinstance(cm, bool) or not isinstance(cm, (int, float)):
        return None
    if cm < 165:
        return 0
    if cm < 175:
        return 1
    if cm < 185:
        return 2
    return 3


def _height(pref, self_value):
    i, j = _HEIGHT_PREF_INDEX.get(pref), _height_index(self_value)
    if i is None or j is None:
        return None
    return _step(abs(i - j))


def _contains(pref, self_value):
    return 1.0 if self_value in _as_list(pref) else 0.0


def _intersects(pref, self_value):
    return 1.0 if set(_as_list(pref)) & set(_as_list(self_value)) else 0.0


def _body_mark(pref, self_value):
    """문신·피어싱 공통. ok는 무조건 만족, none은 '없음'만 만족."""
    if pref == "ok":
        return 1.0
    if pref != "none":
        return None
    return 1.0 if self_value == "no" else 0.0


_POLITICS_ORDER = {"progressive": 0, "moderate": 1, "conservative": 2}


def _politics(pref, self_value):
    if self_value == "unknown":  # 판정 불가라 중간값
        return 0.5
    return _ordinal(_POLITICS_ORDER)(pref, self_value)


def _religion(pref, self_value):
    if self_value == "other":  # 세부 종교를 모르니 중간값
        return 0.5
    return _contains(pref, self_value)


def _scale(pref, self_value):
    """1~5 척도. 1 − |차이| / 4"""
    if isinstance(pref, bool) or isinstance(self_value, bool):
        return None
    if not isinstance(pref, (int, float)) or not isinstance(self_value, (int, float)):
        return None
    return 1 - abs(pref - self_value) / 4


def _exact(pref, self_value):
    return 1.0 if pref == self_value else 0.0


_RANK_MAX_DISTANCE = 8  # 4개 항목이 완전 역순일 때의 순위차 합


def _priority_rank(pref, self_value):
    a, b = _as_list(pref), _as_list(self_value)
    if len(a) != 4 or sorted(a) != sorted(b):
        return None
    position = {item: i for i, item in enumerate(b)}
    distance = sum(abs(i - position[item]) for i, item in enumerate(a))
    return 1 - distance / _RANK_MAX_DISTANCE


_COST_SHARE = {
    "dutch": {"dutch": 1.0, "alternate": 0.5, "richer": 0.5, "me": 0.5},
    "alternate": {"dutch": 0.5, "alternate": 1.0, "richer": 0.5, "me": 0.5},
    "richer": {"dutch": 0.5, "alternate": 0.5, "richer": 1.0, "me": 0.5},
    "partner": {"dutch": 0.0, "alternate": 0.5, "richer": 0.5, "me": 1.0},
}
_SMOKING = {
    "none_only": {"none": 1.0, "sometimes": 0.0, "yes": 0.0},
    "sometimes_ok": {"none": 1.0, "sometimes": 1.0, "yes": 0.0},
}
_DRINKING = {
    "none": {"none": 1.0, "sometimes": 0.5, "often": 0.0},
    "sometimes_ok": {"none": 1.0, "sometimes": 1.0, "often": 0.5},
}
_HOBBY = {
    "indoor": {"indoor": 1.0, "outdoor": 0.0, "both": 1.0},
    "outdoor": {"indoor": 0.0, "outdoor": 1.0, "both": 1.0},
}
_LIVING = {"prefer_independent": {"independent": 1.0, "dorm": 0.5, "home": 0.0}}


# ── 거주지 (설계 §3.3) ────────────────────────────────────

_ADJACENT: dict[str, tuple[str, ...]] = {
    "서울": ("인천", "경기"),
    "인천": ("서울", "경기"),
    "경기": ("서울", "인천", "강원", "충북", "충남"),
    "강원": ("경기", "충북", "경북"),
    "충북": ("경기", "강원", "충남", "세종", "대전", "경북", "전북"),
    "충남": ("경기", "충북", "세종", "대전", "전북"),
    "세종": ("충북", "충남", "대전"),
    "대전": ("충북", "충남", "세종"),
    "전북": ("충남", "충북", "전남", "경남", "경북"),
    "전남": ("전북", "광주", "경남"),
    "광주": ("전남",),
    "경북": ("강원", "충북", "전북", "경남", "대구", "울산"),
    "대구": ("경북",),
    "경남": ("전북", "전남", "경북", "부산", "울산"),
    "부산": ("경남", "울산"),
    "울산": ("경남", "경북", "부산"),
    "제주": (),  # 육로 연결 없음
}

# 홉 수 → 만족도. 표에 없는 홉 수(연결 없음 포함)는 0.0
_RESIDENCE_TABLE = {
    "h1": {0: 1.0, 1: 0.5},
    "h2": {0: 1.0, 1: 1.0, 2: 0.5},
    "h3": {0: 1.0, 1: 1.0, 2: 1.0},
}


def _hops(start: str, goal: str) -> int | None:
    """인접 그래프 최단 홉. 도달 불가면 None."""
    if start not in _ADJACENT or goal not in _ADJACENT:
        return None
    if start == goal:
        return 0
    seen = {start}
    queue = deque([(start, 0)])
    while queue:
        node, depth = queue.popleft()
        for nxt in _ADJACENT[node]:
            if nxt in seen:
                continue
            if nxt == goal:
                return depth + 1
            seen.add(nxt)
            queue.append((nxt, depth + 1))
    return None


def _residence(pref, my_sido, their_sido):
    table = _RESIDENCE_TABLE.get(pref)
    if table is None or _is_empty(my_sido) or _is_empty(their_sido):
        return None
    hops = _hops(my_sido, their_sido)
    return 0.0 if hops is None else table.get(hops, 0.0)


_RULES = {
    "height": _height,
    "face": _contains,
    "style": _intersects,
    "tattoo": _body_mark,
    "piercing": _body_mark,
    "politics": _politics,
    "religion": _religion,
    "contact_freq": _scale,
    "date_freq": _scale,
    "alone_time": _scale,
    "affection": _scale,
    "conflict_style": _exact,
    "priority_rank": _priority_rank,
    "date_budget": _ordinal({"u5": 0, "5_10": 1, "10_20": 2, "20_30": 3, "o30": 4}),
    "cost_share": _table(_COST_SHARE),
    "smoking": _table(_SMOKING),
    "drinking": _table(_DRINKING),
    "exercise": _ordinal({"none": 0, "w1_2": 1, "w3": 2}),
    "sleep": _exact,
    "hobby": _table(_HOBBY),
    "living": _table(_LIVING),
    # residence는 '내 거주지'가 더 필요해 satisfaction()에서 따로 처리한다
}


def satisfaction(base: str, pref_responses: dict, self_responses: dict) -> float | None:
    """`base` 문항 한 쌍의 만족도. `None`이면 계산에서 제외한다 (설계 §3.1)."""
    pref_q, self_q = PAIRS[base]
    pref_value = pref_responses.get(pref_q.id)
    self_value = self_responses.get(self_q.id)
    if _is_empty(pref_value) or _is_empty(self_value):
        return None
    if _is_no_pref(pref_q, pref_value):
        return None
    if base == "residence":
        return _residence(pref_value, pref_responses.get("residence_self"), self_value)
    return _RULES[base](pref_value, self_value)
