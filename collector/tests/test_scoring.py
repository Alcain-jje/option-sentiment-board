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
