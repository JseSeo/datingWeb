"""설문 응답 값 검증 — 카탈로그로 검증한 값만 남긴다.

`PUT /me/survey`가 쓰기 직전에 부른다. 검증되지 않은 값이 DB에 들어가면
매칭 계산(`app/services/scoring.py`)에서 예외로 터진다.

규칙은 문항 타입별로 하나씩. 값을 그대로 통과시키거나, 정제한 값을 돌려주거나,
`_DROP`을 돌려 버린다.
"""

from app.survey.catalog import FACE_TYPES, QUESTIONS, Question

_BY_ID = {q.id: q for q in QUESTIONS}

_DROP = object()  # 규칙 위반. None은 정상 값일 수 있어 센티넬을 따로 둔다

_FACE_IDS = {f.id for f in FACE_TYPES}


def _allowed_ids(question: Question) -> set[str]:
    """얼굴상 문항은 choices가 비어 있고 FACE_TYPES를 쓴다.

    `no_pref_id`는 일반 문항이면 이미 choices에 들어 있지만, 얼굴상은
    별도 목록이라 여기서 더해준다.
    """
    ids = _FACE_IDS if question.face else {c.id for c in question.choices or []}
    if question.no_pref_id is not None:
        ids = ids | {question.no_pref_id}
    return ids


def _single(question: Question, value):
    if isinstance(value, str) and value in _allowed_ids(question):
        return value
    return _DROP


def _multi(question: Question, value):
    if not isinstance(value, list):
        return _DROP
    allowed = _allowed_ids(question)
    if not all(isinstance(v, str) and v in allowed for v in value):
        return _DROP
    return list(dict.fromkeys(value))  # 중복 제거, 순서 유지


_SCALE_MIN, _SCALE_MAX = 1, 5  # 프론트가 렌더하는 눈금 (QuestionField.tsx의 [1..5])


def _scale(_: Question, value):
    if isinstance(value, bool) or not isinstance(value, int):
        return _DROP
    if not _SCALE_MIN <= value <= _SCALE_MAX:
        return _DROP
    return value


def _ranking(question: Question, value):
    """`rank_items`를 빠짐없이 한 번씩 쓴 순열만 통과. 순서 자체가 응답이다."""
    if not isinstance(value, list):
        return _DROP
    items = [c.id for c in question.rank_items or []]
    if not all(isinstance(v, str) for v in value):
        return _DROP
    if sorted(value) != sorted(items):
        return _DROP
    return value


def _number(question: Question, value):
    """범위는 카탈로그가 선언한다. 선언이 없으면 타입만 본다."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return _DROP
    if question.min is not None and value < question.min:
        return _DROP
    if question.max is not None and value > question.max:
        return _DROP
    return value


_RULES = {
    "single": _single,
    "multi": _multi,
    "scale": _scale,
    "ranking": _ranking,
    "number": _number,
    "image-single": _single,
    "image-multi": _multi,
}


def sanitize_responses(responses: dict) -> tuple[dict, list[str]]:
    """반환: (정제된 responses, 버린 문항 id 목록)"""
    clean: dict = {}
    dropped: list[str] = []
    for qid, value in responses.items():
        question = _BY_ID.get(qid)
        if question is None:
            dropped.append(qid)
            continue
        rule = _RULES.get(question.type)
        if rule is not None:
            value = rule(question, value)
            if value is _DROP:
                dropped.append(qid)
                continue
        clean[qid] = value
    return clean, dropped
