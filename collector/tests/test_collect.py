import json

from collector import collect


def _fake_fetch_ok(symbol, **kw):
    return {
        "callVol": 18000, "putVol": 10000, "callOi": 90000, "putOi": 60000,
        "price": 164.2, "chg": 1.8,
        "buckets": [{"strike": 150.0, "callOi": 100, "putOi": 200}],
    }


def _fake_fetch_fail(symbol, **kw):
    raise RuntimeError(f"{symbol}: down")


def test_run_happy_path(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "fetch_ticker", _fake_fetch_ok)
    rc = collect.run([("NVDA", "엔비디아"), ("AAPL", "애플")], tmp_path)
    assert rc == 0
    latest = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert len(latest["stocks"]) == 2
    s = latest["stocks"][0]
    # ratio 10000/18000 = 0.5556 → 90 - 0.1556×(80/1.2) = 79.6 → round 80
    assert s["score"] == 80 and s["scoreMode"] == "absolute"
    assert s["label"] == "매우 강세" and s["stale"] is False
    assert latest["marketScore"] == 80
    hist = json.loads((tmp_path / "history" / "NVDA.json").read_text(encoding="utf-8"))
    assert len(hist) == 1
    detail = json.loads((tmp_path / "detail" / "NVDA.json").read_text(encoding="utf-8"))
    assert detail["buckets"][0]["putOi"] == 200
    assert len(detail["trend"]) == 1


def test_run_same_day_rerun_no_duplicate_history(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "fetch_ticker", _fake_fetch_ok)
    collect.run([("NVDA", "엔비디아")], tmp_path)
    collect.run([("NVDA", "엔비디아")], tmp_path)
    hist = json.loads((tmp_path / "history" / "NVDA.json").read_text(encoding="utf-8"))
    assert len(hist) == 1                     # 같은 날 재실행 시 교체


def test_run_partial_failure_reuses_previous(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "fetch_ticker", _fake_fetch_ok)
    pairs = [(s, s) for s in ["A", "B", "C", "D"]]
    collect.run(pairs, tmp_path)

    def flaky(symbol, **kw):
        if symbol == "A":
            raise RuntimeError("down")
        return _fake_fetch_ok(symbol)

    monkeypatch.setattr(collect, "fetch_ticker", flaky)
    rc = collect.run(pairs, tmp_path)
    assert rc == 0                            # 1/4=25% < 30% → 성공
    latest = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    a = next(s for s in latest["stocks"] if s["ticker"] == "A")
    assert a["stale"] is True                 # 직전 데이터 재사용 + stale 표시


def test_run_too_many_failures_aborts(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "fetch_ticker", _fake_fetch_fail)
    rc = collect.run([("A", "A"), ("B", "B")], tmp_path)
    assert rc == 1
    assert not (tmp_path / "latest.json").exists()   # 커밋할 산출물 없음
