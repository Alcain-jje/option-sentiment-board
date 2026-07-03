from __future__ import annotations

COLD_START_MIN_DAYS = 20
MIN_TOTAL_VOLUME = 1000


def pc_ratio(call_vol: int, put_vol: int) -> float | None:
    """풋/콜 거래량 비율. 총거래량이 임계치 미만이면 None(데이터 부족)."""
    if call_vol + put_vol < MIN_TOTAL_VOLUME:
        return None
    if call_vol == 0:
        return 99.0
    return put_vol / call_vol


def score_cold_start(ratio: float) -> int:
    """이력 부족 시 절대값 선형 매핑: 0.4→90 ~ 1.6→10."""
    if ratio <= 0.4:
        return 90
    if ratio >= 1.6:
        return 10
    return round(90 - (ratio - 0.4) * (80 / 1.2))
