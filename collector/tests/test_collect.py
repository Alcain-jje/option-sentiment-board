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
    rc = collect.run([("NVDA", "엔비디아", "반도체"), ("AAPL", "애플", "빅테크")], tmp_path)
    assert rc == 0
    latest = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert len(latest["stocks"]) == 2
    s = latest["stocks"][0]
    # ratio 10000/18000 = 0.5556 → 90 - 0.1556×(80/1.2) = 79.6 → round 80
    assert s["score"] == 80 and s["scoreMode"] == "absolute"
    assert s["label"] == "매우 강세" and s["stale"] is False
    assert s["sector"] == "반도체"
    assert s["spark"] == [80]
    assert s["scoreChg"] is None
    assert latest["marketScore"] == 80
    hist = json.loads((tmp_path / "history" / "NVDA.json").read_text(encoding="utf-8"))
    assert len(hist) == 1
    detail = json.loads((tmp_path / "detail" / "NVDA.json").read_text(encoding="utf-8"))
    assert detail["buckets"][0]["putOi"] == 200
    assert len(detail["trend"]) == 1


def test_run_same_day_rerun_no_duplicate_history(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "fetch_ticker", _fake_fetch_ok)
    collect.run([("NVDA", "엔비디아", "반도체")], tmp_path)
    collect.run([("NVDA", "엔비디아", "반도체")], tmp_path)
    hist = json.loads((tmp_path / "history" / "NVDA.json").read_text(encoding="utf-8"))
    assert len(hist) == 1                     # 같은 날 재실행 시 교체


def test_run_partial_failure_reuses_previous(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "fetch_ticker", _fake_fetch_ok)
    pairs = [(s, s, "테스트") for s in ["A", "B", "C", "D"]]
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
    rc = collect.run([("A", "A", "테스트"), ("B", "B", "테스트")], tmp_path)
    assert rc == 1
    assert not (tmp_path / "latest.json").exists()   # 커밋할 산출물 없음


def test_run_processing_error_isolated(tmp_path, monkeypatch):
    def bad_shape(symbol, **kw):
        if symbol == "B":
            return {"callVol": 18000, "putVol": 10000}   # price/chg/buckets 누락 → KeyError
        return _fake_fetch_ok(symbol)

    monkeypatch.setattr(collect, "fetch_ticker", bad_shape)
    pairs = [(s, s, "테스트") for s in ["A", "B", "C", "D"]]
    rc = collect.run(pairs, tmp_path)
    assert rc == 0                            # 1/4 실패 — 배치 전체가 죽지 않음
    latest = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert {s["ticker"] for s in latest["stocks"]} == {"A", "C", "D"}


def test_subset_run_preserves_market_history(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "fetch_ticker", _fake_fetch_ok)
    collect.run([(s, s, "테스트") for s in ["A", "B", "C"]], tmp_path)
    market_before = (tmp_path / "history" / "_MARKET.json").read_text(encoding="utf-8")
    latest_before = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))

    collect.run([("A", "A", "테스트")], tmp_path, update_market=False)
    market_after = (tmp_path / "history" / "_MARKET.json").read_text(encoding="utf-8")
    latest_after = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert market_after == market_before      # 부분 실행이 시장 이력을 건드리지 않음
    assert latest_after["marketScore"] == latest_before["marketScore"]  # 직전 값 유지


def test_multi_day_stale_keeps_stale_since(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "fetch_ticker", _fake_fetch_ok)
    pairs = [(s, s, "테스트") for s in ["A", "B", "C", "D"]]
    collect.run(pairs, tmp_path)

    def flaky(symbol, **kw):
        if symbol == "A":
            raise RuntimeError("down")
        return _fake_fetch_ok(symbol)

    monkeypatch.setattr(collect, "fetch_ticker", flaky)
    collect.run(pairs, tmp_path)
    collect.run(pairs, tmp_path)              # 이틀 연속 실패 시에도
    latest = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    a = next(s for s in latest["stocks"] if s["ticker"] == "A")
    assert a["stale"] is True
    assert a["staleSince"] is not None        # 최초 실패 시점 기록 유지


def test_spark_and_score_chg_accumulate(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "fetch_ticker", _fake_fetch_ok)
    pairs = [("NVDA", "엔비디아", "반도체")]
    collect.run(pairs, tmp_path)
    # 전일 이력을 인위 조작(오늘보다 하루 전 날짜, 점수 70)
    import json as _json
    hp = tmp_path / "history" / "NVDA.json"
    hist = _json.loads(hp.read_text(encoding="utf-8"))
    hist.insert(0, {"date": "2000-01-01", "pcRatio": 0.8, "score": 70})
    hp.write_text(_json.dumps(hist), encoding="utf-8")
    collect.run(pairs, tmp_path)
    latest = _json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    s = latest["stocks"][0]
    assert s["spark"] == [70, 80]
    assert s["scoreChg"] == 10
