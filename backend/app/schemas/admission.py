from datetime import datetime

ADMISSION_YEAR_MIN = 2000


def check_admission_year(value: int | None) -> int | None:
    """입학년도 4자리 검증 (설계 §4.2).

    상한이 현재 연도가 아니라 +1인 것은 신입생이 입학 전 학기에 가입할 수 있어서다.
    """
    if value is None:
        return None
    upper = datetime.utcnow().year + 1
    if not (ADMISSION_YEAR_MIN <= value <= upper):
        raise ValueError(f"학번은 {ADMISSION_YEAR_MIN}~{upper} 사이여야 합니다")
    return value
