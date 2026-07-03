from collector import scoring


def test_pc_ratio_guards():
    assert scoring.pc_ratio(300, 300) is None          # 총량 1000 미만 → 데이터 부족
    assert scoring.pc_ratio(0, 5000) == 99.0            # 콜 0 → 극단 약세 처리
    assert scoring.pc_ratio(4000, 2000) == 0.5


def test_cold_start_linear_mapping():
    assert scoring.score_cold_start(0.4) == 90
    assert scoring.score_cold_start(0.7) == 70
    assert scoring.score_cold_start(1.0) == 50
    assert scoring.score_cold_start(1.3) == 30
    assert scoring.score_cold_start(1.6) == 10
    assert scoring.score_cold_start(0.05) == 90         # 하한 클램프
    assert scoring.score_cold_start(5.0) == 10          # 상한 클램프


def test_percentile_score():
    hist = [0.5, 0.6, 0.7, 0.8, 0.9]
    assert scoring.score_percentile(0.45, hist) == 100   # 전부보다 낮은 비율 = 최강세
    assert scoring.score_percentile(0.95, hist) == 0
    assert scoring.score_percentile(0.7, hist) == 50     # 동률은 절반 가중


def test_compute_score_mode_switch():
    short_hist = [1.0] * (scoring.COLD_START_MIN_DAYS - 1)
    score, mode = scoring.compute_score(0.8, short_hist)
    assert mode == "absolute"

    long_hist = [0.5 + i * 0.05 for i in range(scoring.COLD_START_MIN_DAYS)]
    score, mode = scoring.compute_score(1.45, long_hist)
    assert mode == "percentile"
    assert score <= 5
