import pandas as pd

from collector.fetch import aggregate_chain, bucket_strikes


def _df(rows):
    return pd.DataFrame(rows, columns=["strike", "volume", "openInterest"])


def test_aggregate_chain_sums_and_buckets():
    calls = _df([(95, 100, 1000), (100, 200, 2000), (110, float("nan"), 3000)])
    puts = _df([(90, 50, 500), (100, 150, 1500)])
    out = aggregate_chain([(calls, puts)], price=100.0)
    assert out["callVol"] == 300           # NaN volume은 0 처리
    assert out["putVol"] == 200
    assert out["callOi"] == 6000
    assert out["putOi"] == 2000
    assert len(out["buckets"]) == 7
    assert sum(b["callOi"] for b in out["buckets"]) == 6000  # ±20% 안의 OI 전부 포함
    assert sum(b["putOi"] for b in out["buckets"]) == 2000


def test_bucket_strikes_ignores_out_of_band():
    buckets = bucket_strikes({50.0: 999, 100.0: 10}, {200.0: 999}, price=100.0)
    assert sum(b["callOi"] for b in buckets) == 10   # ±20% 밖(50, 200)은 제외
    assert sum(b["putOi"] for b in buckets) == 0
