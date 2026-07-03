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


def score_percentile(ratio: float, history: list[float]) -> int:
    """당일 비율의 60일 이력 내 백분위 → 0~100 (낮은 비율=콜 우세=높은 점수)."""
    less = sum(1 for r in history if r < ratio)
    equal = sum(1 for r in history if r == ratio)
    p = (less + 0.5 * equal) / len(history)
    return round(100 * (1 - p))


def compute_score(ratio: float, history: list[float]) -> tuple[int, str]:
    """(점수, 모드) 반환. 이력 20일 이상이면 백분위, 아니면 절대값 매핑."""
    if len(history) >= COLD_START_MIN_DAYS:
        return score_percentile(ratio, history), "percentile"
    return score_cold_start(ratio), "absolute"


def label_for(score: int) -> str:
    """점수에 따른 심리 라벨."""
    if score >= 80:
        return "매우 강세"
    if score >= 60:
        return "강세"
    if score >= 40:
        return "중립"
    if score >= 20:
        return "약세"
    return "매우 약세"


def summary_text(call_vol: int, put_vol: int, score: int, extreme: bool) -> str:
    """(콜/풋 거래량, 점수) → 한 줄 해석."""
    if 40 <= score <= 59:
        return "상승·하락 베팅 비슷 — 관망 분위기"
    if score >= 60:
        mult = call_vol / max(put_vol, 1)
        suffix = "평소보다 훨씬 강세" if extreme else "강세 우위"
        return f"상승 베팅이 하락의 {mult:.1f}배 — {suffix}"
    mult = put_vol / max(call_vol, 1)
    suffix = "평소보다 뚜렷한 약세" if extreme else "약세 우위"
    return f"하락 베팅이 상승의 {mult:.1f}배 — {suffix}"
