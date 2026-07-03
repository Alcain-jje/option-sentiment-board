# 옵션 심리 보드 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 미국 대장주 52종목의 옵션 데이터를 매일 수집해 0~100 심리 점수로 보여주는 정적 사이트 + GitHub Actions 자동화.

**Architecture:** Python 수집기(yfinance)가 `site/data/*.json`을 생성하고 GitHub Actions가 매일 커밋, GitHub Pages가 `site/`를 정적 서빙. 프론트는 빌드 없는 vanilla HTML/CSS/JS.

**Tech Stack:** Python 3.12, yfinance, pandas, pytest / vanilla JS / GitHub Actions + Pages

**작업 디렉토리:** `C:\workspace\option-sentiment-board` (모든 명령은 여기서 실행)

**스펙:** `docs/superpowers/specs/2026-07-03-option-sentiment-board-design.md`

---

### Task 1: 프로젝트 스캐폴드 + 종목 정의

**Files:**
- Create: `requirements.txt`, `.gitignore`, `pytest.ini`, `collector/__init__.py`, `collector/tickers.py`, `collector/tests/__init__.py`, `collector/tests/test_tickers.py`

- [ ] **Step 1: 기반 파일 작성**

`requirements.txt`:
```
yfinance>=0.2.50
pandas>=2.0
pytest>=8.0
```

`.gitignore`:
```
__pycache__/
.pytest_cache/
*.pyc
.venv/
```

`pytest.ini`:
```ini
[pytest]
testpaths = collector/tests
```

`collector/__init__.py`, `collector/tests/__init__.py`: 빈 파일.

- [ ] **Step 2: 실패하는 테스트 작성** — `collector/tests/test_tickers.py`

```python
from collector.tickers import TICKERS


def test_ticker_count():
    assert len(TICKERS) == 52


def test_tickers_unique_and_named():
    symbols = [t for t, _ in TICKERS]
    assert len(set(symbols)) == 52
    assert all(name for _, name in TICKERS)
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `python -m pytest -q`  → Expected: FAIL (`ModuleNotFoundError: collector.tickers`)

- [ ] **Step 4: `collector/tickers.py` 작성**

```python
# (심볼, 한글 표시명) — 옵션 유동성 높은 미국 대장주 52종목
TICKERS = [
    ("AAPL", "애플"), ("MSFT", "마이크로소프트"), ("NVDA", "엔비디아"),
    ("AMZN", "아마존"), ("GOOGL", "알파벳"), ("META", "메타"),
    ("TSLA", "테슬라"), ("AVGO", "브로드컴"), ("AMD", "AMD"),
    ("QCOM", "퀄컴"), ("INTC", "인텔"), ("MU", "마이크론"),
    ("TXN", "텍사스인스트루먼트"), ("ARM", "Arm"), ("SMCI", "슈퍼마이크로"),
    ("ORCL", "오라클"), ("CRM", "세일즈포스"), ("ADBE", "어도비"),
    ("NFLX", "넷플릭스"), ("CSCO", "시스코"),
    ("JPM", "JP모건"), ("BAC", "뱅크오브아메리카"), ("GS", "골드만삭스"),
    ("V", "비자"), ("MA", "마스터카드"), ("BRK-B", "버크셔해서웨이"),
    ("LLY", "일라이릴리"), ("UNH", "유나이티드헬스"), ("JNJ", "존슨앤드존슨"),
    ("ABBV", "애브비"), ("MRK", "머크"), ("PFE", "화이자"),
    ("WMT", "월마트"), ("COST", "코스트코"), ("HD", "홈디포"),
    ("PG", "P&G"), ("KO", "코카콜라"), ("PEP", "펩시코"),
    ("DIS", "디즈니"), ("NKE", "나이키"), ("MCD", "맥도날드"),
    ("BA", "보잉"), ("CAT", "캐터필러"), ("GE", "GE에어로스페이스"),
    ("XOM", "엑슨모빌"), ("CVX", "셰브론"),
    ("PLTR", "팔란티어"), ("COIN", "코인베이스"), ("GME", "게임스톱"),
    ("MSTR", "스트래티지"), ("HOOD", "로빈후드"), ("UBER", "우버"),
]
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `python -m pytest -q`  → Expected: 2 passed

- [ ] **Step 6: 커밋**

```bash
git add -A && git commit -m "feat: 프로젝트 스캐폴드 + 52종목 정의"
```

---

### Task 2: 점수 계산 — 비율 가드 + 콜드스타트 매핑

**Files:**
- Create: `collector/scoring.py`, `collector/tests/test_scoring.py`

- [ ] **Step 1: 실패하는 테스트 작성** — `collector/tests/test_scoring.py`

```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest collector/tests/test_scoring.py -q`  → Expected: FAIL (no module `scoring`)

- [ ] **Step 3: `collector/scoring.py` 작성 (최소 구현)**

```python
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
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest collector/tests/test_scoring.py -q` → 2 passed

- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat: 풋콜비율 가드 + 콜드스타트 점수 매핑"`

---

### Task 3: 점수 계산 — 백분위 모드 + 모드 자동 선택

**Files:**
- Modify: `collector/scoring.py`
- Test: `collector/tests/test_scoring.py` (추가)

- [ ] **Step 1: 실패하는 테스트 추가**

```python
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
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest collector/tests/test_scoring.py -q` → FAIL (`score_percentile` 없음)

- [ ] **Step 3: `scoring.py`에 추가**

```python
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
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest -q` → all passed

- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat: 백분위 점수 + 콜드스타트 자동 전환"`

---

### Task 4: 라벨 + 한 줄 해석 생성

**Files:**
- Modify: `collector/scoring.py`
- Test: `collector/tests/test_scoring.py` (추가)

- [ ] **Step 1: 실패하는 테스트 추가**

```python
def test_label_bands():
    assert scoring.label_for(85) == "매우 강세"
    assert scoring.label_for(60) == "강세"
    assert scoring.label_for(50) == "중립"
    assert scoring.label_for(25) == "약세"
    assert scoring.label_for(5) == "매우 약세"


def test_summary_text():
    assert scoring.summary_text(1800, 1000, 78, extreme=False) == "상승 베팅이 하락의 1.8배 — 강세 우위"
    assert scoring.summary_text(1800, 1000, 92, extreme=True) == "상승 베팅이 하락의 1.8배 — 평소보다 훨씬 강세"
    assert scoring.summary_text(1000, 1500, 21, extreme=False) == "하락 베팅이 상승의 1.5배 — 약세 우위"
    assert scoring.summary_text(1000, 1500, 8, extreme=True) == "하락 베팅이 상승의 1.5배 — 평소보다 뚜렷한 약세"
    assert scoring.summary_text(1000, 1050, 50, extreme=False) == "상승·하락 베팅 비슷 — 관망 분위기"
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest collector/tests/test_scoring.py -q` → FAIL

- [ ] **Step 3: `scoring.py`에 추가**

```python
def label_for(score: int) -> str:
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
    if 40 <= score <= 59:
        return "상승·하락 베팅 비슷 — 관망 분위기"
    if score >= 60:
        mult = call_vol / max(put_vol, 1)
        suffix = "평소보다 훨씬 강세" if extreme else "강세 우위"
        return f"상승 베팅이 하락의 {mult:.1f}배 — {suffix}"
    mult = put_vol / max(call_vol, 1)
    suffix = "평소보다 뚜렷한 약세" if extreme else "약세 우위"
    return f"하락 베팅이 상승의 {mult:.1f}배 — {suffix}"
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest -q` → all passed

- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat: 심리 라벨 + 한글 한 줄 해석"`

---

### Task 5: 옵션체인 집계 (순수함수)

**Files:**
- Create: `collector/fetch.py`, `collector/tests/test_fetch.py`

- [ ] **Step 1: 실패하는 테스트 작성** — `collector/tests/test_fetch.py`

```python
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
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest collector/tests/test_fetch.py -q` → FAIL

- [ ] **Step 3: `collector/fetch.py` 작성 (집계 부분만)**

```python
from __future__ import annotations

import time
from datetime import date, timedelta

import pandas as pd

EXPIRY_WINDOW_DAYS = 60
PRICE_BAND = 0.20
N_BUCKETS = 7


def bucket_strikes(strike_call: dict, strike_put: dict, price: float) -> list[dict]:
    """현재가 ±20%를 7개 구간으로 나눠 행사가별 OI를 집계 (상세화면 '베팅 지도'용)."""
    lo, hi = price * (1 - PRICE_BAND), price * (1 + PRICE_BAND)
    width = (hi - lo) / N_BUCKETS
    buckets = [
        {"strike": round(lo + width * (i + 0.5), 1), "callOi": 0, "putOi": 0}
        for i in range(N_BUCKETS)
    ]
    for src, key in ((strike_call, "callOi"), (strike_put, "putOi")):
        for strike, oi in src.items():
            if lo <= strike < hi:
                idx = min(int((strike - lo) // width), N_BUCKETS - 1)
                buckets[idx][key] += oi
    return buckets


def aggregate_chain(frames: list[tuple[pd.DataFrame, pd.DataFrame]], price: float) -> dict:
    """만기별 (calls, puts) 데이터프레임들을 합산해 거래량/OI/행사가 분포를 만든다."""
    call_vol = put_vol = call_oi = put_oi = 0
    strike_call: dict[float, int] = {}
    strike_put: dict[float, int] = {}
    for calls, puts in frames:
        for df, is_call in ((calls, True), (puts, False)):
            df = df[["strike", "volume", "openInterest"]].fillna(0)
            vol = int(df["volume"].sum())
            oi = int(df["openInterest"].sum())
            target = strike_call if is_call else strike_put
            for strike, s_oi in zip(df["strike"], df["openInterest"]):
                target[float(strike)] = target.get(float(strike), 0) + int(s_oi)
            if is_call:
                call_vol += vol
                call_oi += oi
            else:
                put_vol += vol
                put_oi += oi
    return {
        "callVol": call_vol, "putVol": put_vol,
        "callOi": call_oi, "putOi": put_oi,
        "buckets": bucket_strikes(strike_call, strike_put, price),
    }
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest -q` → all passed

- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat: 옵션체인 집계 + 행사가 버킷"`

---

### Task 6: yfinance 수집 래퍼 (재시도 포함)

**Files:**
- Modify: `collector/fetch.py`
- Test: `collector/tests/test_fetch.py` (추가)

- [ ] **Step 1: 실패하는 테스트 추가** — 가짜 yfinance 모듈로 재시도 검증

```python
class _FakeChain:
    def __init__(self):
        self.calls = _df([(100, 10, 100)])
        self.puts = _df([(100, 5, 50)])


class _FakeTicker:
    def __init__(self, fail_times):
        self._fails = fail_times
        self.options = ["2099-01-01"]          # 항상 60일 밖 → 아래에서 window 조정

    def history(self, period):
        if self._fails[0] > 0:
            self._fails[0] -= 1
            raise ConnectionError("boom")
        return pd.DataFrame({"Close": [100.0, 102.0]})

    def option_chain(self, exp):
        return _FakeChain()


class _FakeYf:
    def __init__(self, fail_times):
        self._fails = [fail_times]

    def Ticker(self, symbol):
        return _FakeTicker(self._fails)


def test_fetch_ticker_retries_then_succeeds(monkeypatch):
    from collector import fetch
    monkeypatch.setattr(fetch, "EXPIRY_WINDOW_DAYS", 100000)  # 가짜 만기 포함되게
    out = fetch.fetch_ticker("TEST", retries=2, sleep=0, _yf=_FakeYf(fail_times=2))
    assert out["price"] == 102.0
    assert out["chg"] == 2.0
    assert out["callVol"] == 10


def test_fetch_ticker_raises_after_retries():
    from collector import fetch
    import pytest
    with pytest.raises(RuntimeError):
        fetch.fetch_ticker("TEST", retries=1, sleep=0, _yf=_FakeYf(fail_times=99))
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest collector/tests/test_fetch.py -q` → FAIL (`fetch_ticker` 없음)

- [ ] **Step 3: `fetch.py`에 추가**

```python
import yfinance as yf


def fetch_ticker(symbol: str, retries: int = 2, sleep: float = 2.0, _yf=yf) -> dict:
    """한 종목의 주가 + 60일 내 만기 옵션체인 집계. 지수 백오프 재시도."""
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            t = _yf.Ticker(symbol)
            closes = t.history(period="5d")["Close"]
            price = float(closes.iloc[-1])
            prev = float(closes.iloc[-2]) if len(closes) > 1 else price
            cutoff = date.today() + timedelta(days=EXPIRY_WINDOW_DAYS)
            frames = []
            for exp in t.options:
                if date.fromisoformat(exp) <= cutoff:
                    oc = t.option_chain(exp)
                    frames.append((oc.calls, oc.puts))
            if not frames:
                raise ValueError("60일 내 만기 없음")
            agg = aggregate_chain(frames, price)
            agg["price"] = round(price, 2)
            agg["chg"] = round((price / prev - 1) * 100, 2) if prev else 0.0
            return agg
        except Exception as e:  # noqa: BLE001 — 종목 단위 격리를 위해 광범위 캐치
            last_err = e
            time.sleep(sleep * (attempt + 1))
    raise RuntimeError(f"{symbol}: 수집 실패") from last_err
```

주의: `EXPIRY_WINDOW_DAYS`를 모듈 변수로 읽도록 `cutoff` 계산에서 직접 참조한다(테스트가 monkeypatch로 바꾸므로 함수 기본 인자로 굳히면 안 됨). 위 코드가 이미 그렇게 되어 있다.

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest -q` → all passed

- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat: yfinance 수집 래퍼(재시도·만기 필터)"`

---

### Task 7: 오케스트레이터 collect.py (이력·latest·detail·시장점수·실패 임계치)

**Files:**
- Create: `collector/collect.py`, `collector/tests/test_collect.py`

- [ ] **Step 1: 실패하는 테스트 작성** — `collector/tests/test_collect.py`

```python
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
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest collector/tests/test_collect.py -q` → FAIL

- [ ] **Step 3: `collector/collect.py` 작성**

```python
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import scoring
from .fetch import fetch_ticker
from .tickers import TICKERS

HISTORY_KEEP = 120
TREND_DAYS = 30
FAIL_LIMIT = 0.30
MARKET_KEY = "_MARKET"


def _load(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def _save(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def _upsert(history: list[dict], entry: dict) -> list[dict]:
    """같은 날짜 항목은 교체, 아니면 추가. 최근 HISTORY_KEEP일만 유지."""
    history = [h for h in history if h["date"] != entry["date"]]
    history.append(entry)
    return history[-HISTORY_KEEP:]


def _scored(ratio: float, hist_path: Path, today: str) -> tuple[int, str, bool, list[dict]]:
    """이력 갱신 포함 점수 계산. (score, mode, extreme, new_history) 반환."""
    history = _load(hist_path, [])
    past = [h["pcRatio"] for h in history if h["date"] != today]
    score, mode = scoring.compute_score(ratio, past)
    extreme = mode == "percentile" and (score >= 90 or score <= 10)
    history = _upsert(history, {"date": today, "pcRatio": round(ratio, 4), "score": score})
    _save(hist_path, history)
    return score, mode, extreme, history


def run(pairs: list[tuple[str, str]], out_dir) -> int:
    out = Path(out_dir)
    today = datetime.now(timezone.utc).date().isoformat()
    prev = {s["ticker"]: s for s in _load(out / "latest.json", {}).get("stocks", [])}

    stocks: list[dict] = []
    failures = 0
    total_call = total_put = 0

    for ticker, name in pairs:
        try:
            raw = fetch_ticker(ticker)
        except Exception as e:  # noqa: BLE001
            print(f"WARN {ticker}: {e}", file=sys.stderr)
            failures += 1
            if ticker in prev:
                stale = dict(prev[ticker])
                stale["stale"] = True
                stocks.append(stale)
            continue

        ratio = scoring.pc_ratio(raw["callVol"], raw["putVol"])
        if ratio is None:
            stocks.append({
                "ticker": ticker, "name": name, "price": raw["price"], "chg": raw["chg"],
                "status": "insufficient", "stale": False,
            })
            continue

        score, mode, extreme, history = _scored(ratio, out / "history" / f"{ticker}.json", today)
        total_call += raw["callVol"]
        total_put += raw["putVol"]

        _save(out / "detail" / f"{ticker}.json", {
            "ticker": ticker, "name": name, "price": raw["price"], "dataAsOf": today,
            "score": score, "label": scoring.label_for(score),
            "ratioText": scoring.summary_text(raw["callVol"], raw["putVol"], score, extreme),
            "buckets": raw["buckets"],
            "trend": [{"date": h["date"], "score": h["score"]} for h in history[-TREND_DAYS:]],
        })
        stocks.append({
            "ticker": ticker, "name": name, "price": raw["price"], "chg": raw["chg"],
            "score": score, "label": scoring.label_for(score), "scoreMode": mode,
            "callVol": raw["callVol"], "putVol": raw["putVol"],
            "ratioText": scoring.summary_text(raw["callVol"], raw["putVol"], score, extreme),
            "status": "ok", "stale": False,
        })

    if pairs and failures / len(pairs) > FAIL_LIMIT:
        print(f"ERROR: {failures}/{len(pairs)} 종목 실패 — 산출물 미생성", file=sys.stderr)
        return 1

    market_score = None
    market_ratio = scoring.pc_ratio(total_call, total_put)
    if market_ratio is not None:
        market_score, _, _, _ = _scored(market_ratio, out / "history" / f"{MARKET_KEY}.json", today)

    _save(out / "latest.json", {
        "updatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataAsOf": today,
        "marketScore": market_score,
        "stocks": stocks,
    })
    print(f"OK: {len(stocks)}종목 (실패 {failures})")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", help="쉼표 구분 심볼 (기본: 전체 52종목)")
    ap.add_argument("--out", default="site/data")
    args = ap.parse_args()
    pairs = TICKERS
    if args.tickers:
        want = set(args.tickers.upper().split(","))
        pairs = [(t, n) for t, n in TICKERS if t in want]
    sys.exit(run(pairs, args.out))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest -q` → all passed

- [ ] **Step 5: 커밋** — `git add -A && git commit -m "feat: 수집 오케스트레이터(이력·시장점수·부분실패 허용)"`

---

### Task 8: 실데이터 스모크 테스트

**Files:** 없음 (검증만). 산출물: `site/data/*.json`

- [ ] **Step 1: 의존성 설치 후 2종목 실수집**

```bash
pip install -r requirements.txt
python -m collector.collect --tickers NVDA,AAPL --out site/data
```
Expected: `OK: 2종목 (실패 0)` / 실패 시 yfinance 버전·네트워크 확인

- [ ] **Step 2: 산출물 검증**

`site/data/latest.json`을 열어 확인: 점수 0~100 범위, `scoreMode: "absolute"`(첫날), `ratioText` 한글 정상, `buckets` 7개, 가격이 상식적 범위인지.

- [ ] **Step 3: 전체 52종목 수집 (소요 3~5분)**

```bash
python -m collector.collect --out site/data
```
Expected: `OK: 52종목 (실패 0~2)` — 일부 실패는 허용(30% 미만)

- [ ] **Step 4: 커밋** — `git add site/data && git commit -m "data: 최초 수집 데이터"`

---

### Task 9: 프론트 — 메인 보드

**Files:**
- Create: `site/index.html`, `site/style.css`, `site/app.js`

- [ ] **Step 1: `site/style.css` 작성**

```css
:root {
  --bull: #E24B4A; --bull-soft: #F09595; --bull-text: #A32D2D;
  --bear: #378ADD; --bear-soft: #85B7EB; --bear-text: #185FA5;
  --neutral: #B4B2A9;
  --bg: #FAF9F5; --card: #FFFFFF; --border: #E7E4DC;
  --text: #1F1F1D; --muted: #85837B;
}
* { box-sizing: border-box; margin: 0; }
body {
  font-family: "Pretendard Variable", Pretendard, "Apple SD Gothic Neo",
    "Malgun Gothic", system-ui, sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.65;
}
.wrap { max-width: 1080px; margin: 0 auto; padding: 56px 28px 96px; }
header h1 { font-size: 27px; font-weight: 700; letter-spacing: -0.02em; }
.sub { color: var(--muted); font-size: 14px; margin-top: 8px; }
.banner { background: #FAEEDA; color: #854F0B; border-radius: 12px;
  padding: 14px 20px; font-size: 14px; margin-top: 24px; }
.market { background: var(--card); border: 1px solid var(--border);
  border-radius: 18px; padding: 30px 36px; margin: 36px 0 44px; }
.market-head { display: flex; justify-content: space-between; align-items: baseline;
  margin-bottom: 18px; }
.market-head h2 { font-size: 16px; font-weight: 600; color: var(--muted); }
.market-head strong { font-size: 18px; }
.gauge { position: relative; height: 10px; border-radius: 5px;
  background: linear-gradient(to right, #B5D4F4, #EFEDE5 45%, #EFEDE5 55%, #F7C1C1); }
.gauge-dot { position: absolute; top: -6px; width: 22px; height: 22px;
  border-radius: 50%; border: 3.5px solid #fff; box-shadow: 0 1px 5px rgba(0,0,0,.18);
  transform: translateX(-11px); }
.gauge-legend { display: flex; justify-content: space-between; margin-top: 10px;
  font-size: 13px; }
.toolbar { display: flex; gap: 10px; margin-bottom: 24px; }
.toolbar button { border: 1px solid var(--border); background: var(--card);
  border-radius: 999px; padding: 9px 20px; font-size: 14px; cursor: pointer;
  color: var(--muted); }
.toolbar button.on { background: var(--text); color: #fff; border-color: var(--text); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
  gap: 22px; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 18px;
  padding: 26px 28px; text-decoration: none; color: inherit; display: block;
  transition: border-color .15s, transform .15s; }
.card:hover { border-color: #C9C6BB; transform: translateY(-2px); }
.card-head { display: flex; justify-content: space-between; align-items: baseline; }
.tkr { font-size: 17px; font-weight: 700; }
.tkr small { font-weight: 400; font-size: 13px; color: var(--muted); margin-left: 6px; }
.score { font-size: 26px; font-weight: 700; }
.price { font-size: 13px; color: var(--muted); margin-top: 4px; }
.bar { height: 8px; border-radius: 4px; background: #F0EEE6; margin: 18px 0 14px; }
.bar > div { height: 8px; border-radius: 4px; }
.desc { font-size: 13.5px; color: #5C5A53; }
.badge { display: inline-block; font-size: 11px; background: #F0EEE6;
  color: var(--muted); border-radius: 5px; padding: 2px 8px; margin-left: 8px;
  vertical-align: 2px; }
footer { margin-top: 72px; color: var(--muted); font-size: 12.5px; line-height: 1.9;
  border-top: 1px solid var(--border); padding-top: 24px; }
@media (max-width: 680px) { .grid { grid-template-columns: 1fr; } .wrap { padding: 32px 18px 64px; } }
```

- [ ] **Step 2: `site/index.html` 작성**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>옵션 심리 보드</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<div class="wrap">
  <header>
    <h1>옵션 심리 보드</h1>
    <p class="sub" id="asof">불러오는 중…</p>
  </header>
  <div id="banner"></div>
  <section class="market" id="market" hidden>
    <div class="market-head">
      <h2>오늘 미국 시장 전체 분위기</h2>
      <strong id="market-label"></strong>
    </div>
    <div class="gauge"><div class="gauge-dot" id="market-dot"></div></div>
    <div class="gauge-legend">
      <span style="color:var(--bear-text)">하락 베팅 우세</span>
      <span style="color:var(--muted)">중립</span>
      <span style="color:var(--bull-text)">상승 베팅 우세</span>
    </div>
  </section>
  <div class="toolbar" id="toolbar">
    <button data-sort="desc" class="on">강세순</button>
    <button data-sort="asc">약세순</button>
    <button data-sort="name">이름순</button>
  </div>
  <main class="grid" id="grid"></main>
  <footer>
    본 사이트는 개인 학습용이며 투자 조언이 아닙니다. 옵션 심리 점수는 풋/콜 거래량
    비율 기반의 시장 분위기 지표로, 주가 방향을 보장하지 않습니다.<br>
    데이터: Yahoo Finance · 장마감 기준 하루 1회 갱신 · 미결제약정은 전일 정산치일 수 있음
  </footer>
</div>
<script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 3: `site/app.js` 작성**

```javascript
const $ = (s) => document.querySelector(s);
const barColor = (s) => s >= 80 ? "var(--bull)" : s >= 60 ? "var(--bull-soft)"
  : s >= 40 ? "var(--neutral)" : s >= 20 ? "var(--bear-soft)" : "var(--bear)";
const numColor = (s) => s >= 60 ? "var(--bull-text)" : s >= 40 ? "var(--muted)" : "var(--bear-text)";

let stocks = [];

function cardHtml(s) {
  const badge = s.stale ? '<span class="badge">어제 데이터</span>' : "";
  if (s.status === "insufficient") {
    return `<a class="card" href="stock.html?t=${s.ticker}">
      <div class="card-head"><span class="tkr">${s.ticker}<small>${s.name}</small></span>
        <span class="score" style="color:var(--muted)">–</span></div>
      <div class="bar"><div style="width:0"></div></div>
      <p class="desc">옵션 거래가 적어 심리 점수를 계산하지 않았어요</p></a>`;
  }
  const chg = s.chg >= 0 ? `+${s.chg.toFixed(2)}%` : `${s.chg.toFixed(2)}%`;
  return `<a class="card" href="stock.html?t=${s.ticker}">
    <div class="card-head">
      <span class="tkr">${s.ticker}<small>${s.name}</small>${badge}</span>
      <span class="score" style="color:${numColor(s.score)}">${s.score}</span>
    </div>
    <p class="price">$${s.price.toLocaleString()} · ${chg}</p>
    <div class="bar"><div style="width:${s.score}%;background:${barColor(s.score)}"></div></div>
    <p class="desc">${s.ratioText}</p></a>`;
}

function render(order) {
  const ok = stocks.filter((s) => s.status === "ok");
  const rest = stocks.filter((s) => s.status !== "ok");
  if (order === "desc") ok.sort((a, b) => b.score - a.score);
  if (order === "asc") ok.sort((a, b) => a.score - b.score);
  if (order === "name") ok.sort((a, b) => a.ticker.localeCompare(b.ticker));
  $("#grid").innerHTML = ok.concat(rest).map(cardHtml).join("");
}

async function main() {
  const d = await (await fetch("data/latest.json")).json();
  $("#asof").textContent =
    `${d.dataAsOf} 미국 장마감 기준 · 매일 아침 자동 업데이트 · ${d.stocks.length}종목`;
  if (Date.now() - Date.parse(d.updatedAt) > 48 * 3600 * 1000) {
    $("#banner").innerHTML =
      '<div class="banner">데이터가 48시간 이상 갱신되지 않았어요. 수집 파이프라인 점검이 필요할 수 있습니다.</div>';
  }
  if (d.marketScore !== null) {
    const label = d.marketScore >= 60 ? "강세" : d.marketScore >= 40 ? "중립" : "약세";
    $("#market").hidden = false;
    $("#market-label").textContent = `${label} · ${d.marketScore}점`;
    $("#market-label").style.color = numColor(d.marketScore);
    $("#market-dot").style.left = `${d.marketScore}%`;
    $("#market-dot").style.background = barColor(d.marketScore);
  }
  stocks = d.stocks;
  render("desc");
  $("#toolbar").addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    document.querySelectorAll("#toolbar button").forEach((b) => b.classList.remove("on"));
    btn.classList.add("on");
    render(btn.dataset.sort);
  });
}
main();
```

- [ ] **Step 4: 로컬 서빙 + 브라우저 검증**

```bash
python -m http.server 8123 -d site
```
Claude Preview(또는 브라우저)로 `http://localhost:8123` 접속 확인:
콘솔 에러 0건 / 카드 52장 렌더 / 정렬 토글 동작 / 시장 게이지 점 위치·색.

- [ ] **Step 5: 커밋** — `git add site && git commit -m "feat: 메인 보드 프론트"`

---

### Task 10: 프론트 — 상세 화면

**Files:**
- Create: `site/stock.html`, `site/stock.js`

- [ ] **Step 1: `site/stock.html` 작성**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>종목 상세 — 옵션 심리 보드</title>
<link rel="stylesheet" href="style.css">
<style>
  .back { font-size: 14px; color: var(--muted); text-decoration: none; }
  .detail { background: var(--card); border: 1px solid var(--border);
    border-radius: 18px; padding: 32px 36px; margin-top: 24px; }
  .detail-head { display: flex; justify-content: space-between; align-items: baseline;
    flex-wrap: wrap; gap: 8px; }
  .cols { display: grid; grid-template-columns: 1fr 1fr; gap: 36px; margin-top: 28px; }
  .col h3 { font-size: 14px; color: var(--muted); font-weight: 600; margin-bottom: 14px; }
  .oi-row { display: flex; align-items: center; gap: 8px; margin-bottom: 7px;
    font-size: 12px; }
  .oi-strike { width: 52px; text-align: right; color: var(--muted); flex-shrink: 0; }
  .oi-track { flex: 1; display: flex; }
  .oi-half { width: 50%; display: flex; }
  .oi-half.put { justify-content: flex-end; }
  .oi-bar { height: 13px; }
  .oi-bar.put { background: var(--bear-soft); border-radius: 3px 0 0 3px; }
  .oi-bar.call { background: var(--bull); border-radius: 0 3px 3px 0; }
  .oi-legend { display: flex; justify-content: space-between; margin-top: 12px;
    font-size: 12px; padding-left: 60px; }
  .trend { display: flex; align-items: flex-end; gap: 4px; height: 110px; }
  .trend > div { flex: 1; border-radius: 3px 3px 0 0; min-height: 4px; }
  .note { margin-top: 22px; padding: 14px 18px; background: #F6F4EC;
    border-radius: 12px; font-size: 13px; color: #5C5A53; }
  @media (max-width: 680px) { .cols { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="wrap">
  <a class="back" href="index.html">&larr; 전체 보드로</a>
  <div id="detail"></div>
  <footer>본 사이트는 개인 학습용이며 투자 조언이 아닙니다. 데이터: Yahoo Finance</footer>
</div>
<script src="stock.js"></script>
</body>
</html>
```

- [ ] **Step 2: `site/stock.js` 작성**

```javascript
const barColor = (s) => s >= 80 ? "var(--bull)" : s >= 60 ? "var(--bull-soft)"
  : s >= 40 ? "var(--neutral)" : s >= 20 ? "var(--bear-soft)" : "var(--bear)";
const numColor = (s) => s >= 60 ? "var(--bull-text)" : s >= 40 ? "var(--muted)" : "var(--bear-text)";

function oiRows(buckets) {
  const max = Math.max(...buckets.map((b) => Math.max(b.callOi, b.putOi)), 1);
  return buckets.slice().reverse().map((b) => `
    <div class="oi-row">
      <span class="oi-strike">$${b.strike.toLocaleString()}</span>
      <div class="oi-track">
        <div class="oi-half put"><div class="oi-bar put" style="width:${(b.putOi / max) * 100}%"></div></div>
        <div class="oi-half"><div class="oi-bar call" style="width:${(b.callOi / max) * 100}%"></div></div>
      </div>
    </div>`).join("");
}

function trendBars(trend) {
  return trend.map((t) => `
    <div style="height:${Math.max(t.score, 4)}%;background:${barColor(t.score)}"
      title="${t.date} · ${t.score}점"></div>`).join("");
}

async function main() {
  const ticker = new URLSearchParams(location.search).get("t");
  const box = document.getElementById("detail");
  if (!ticker) { box.innerHTML = "<p>종목이 지정되지 않았어요.</p>"; return; }
  const res = await fetch(`data/detail/${ticker}.json`);
  if (!res.ok) {
    box.innerHTML = `<div class="detail"><p>${ticker}의 상세 데이터가 아직 없어요.
      옵션 거래가 적거나 최근 수집에 실패한 종목일 수 있습니다.</p></div>`;
    return;
  }
  const d = await res.json();
  document.title = `${d.ticker} ${d.name} — 옵션 심리 보드`;
  box.innerHTML = `
    <div class="detail">
      <div class="detail-head">
        <span class="tkr" style="font-size:20px">${d.ticker}<small>${d.name} · $${d.price.toLocaleString()}</small></span>
        <strong style="color:${numColor(d.score)}">심리 점수 ${d.score} · ${d.label}</strong>
      </div>
      <p class="desc" style="margin-top:10px">${d.ratioText}</p>
      <div class="cols">
        <div class="col">
          <h3>베팅 지도 — 어느 가격에 돈이 몰렸나 (미결제약정)</h3>
          ${oiRows(d.buckets)}
          <div class="oi-legend">
            <span style="color:var(--bear-text)">&larr; 하락 베팅(풋)</span>
            <span style="color:var(--bull-text)">상승 베팅(콜) &rarr;</span>
          </div>
        </div>
        <div class="col">
          <h3>최근 30일 심리 흐름</h3>
          <div class="trend">${trendBars(d.trend)}</div>
          <div class="note">옵션 심리는 "예언"이 아니라 "지금 돈이 어느 쪽에 몰렸나"예요.
            극단적인 쏠림은 오히려 반대로 움직이는 계기가 되기도 합니다.</div>
        </div>
      </div>
      <p class="sub" style="margin-top:20px">기준: ${d.dataAsOf} 장마감 · 만기 60일 내 옵션 합산 · 현재가 ±20% 행사가 구간</p>
    </div>`;
}
main();
```

- [ ] **Step 3: 브라우저 검증**

`http://localhost:8123/stock.html?t=NVDA` 접속: 나비 차트 좌우 대칭 렌더, 30일 흐름(첫날은 막대 1개), 없는 티커(`?t=ZZZZ`)에서 안내 문구.

- [ ] **Step 4: 커밋** — `git add site && git commit -m "feat: 종목 상세 화면(베팅 지도·30일 흐름)"`

---

### Task 11: GitHub Actions 워크플로 + README

**Files:**
- Create: `.github/workflows/collect.yml`, `.github/workflows/pages.yml`, `README.md`

- [ ] **Step 1: `.github/workflows/collect.yml` 작성**

```yaml
name: daily-collect
on:
  schedule:
    - cron: "10 21 * * 1-5"   # KST 화~토 06:10 (미 장마감 후)
  workflow_dispatch:

permissions:
  contents: write
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  collect:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: python -m pytest -q
      - run: python -m collector.collect
      - name: Commit data
        run: |
          git config user.name "collector-bot"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add site/data
          git diff --cached --quiet || git commit -m "data: $(date -u +%F) 자동 수집"
          git push
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site

  deploy:
    needs: collect
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: `.github/workflows/pages.yml` 작성** (사람이 프론트 수정을 push했을 때 재배포 — 봇 커밋은 `on: push`를 트리거하지 않으므로 collect.yml이 자체 배포를 겸함)

```yaml
name: deploy-pages
on:
  push:
    branches: [main]
    paths: ["site/**"]
  workflow_dispatch:

permissions:
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 3: `README.md` 작성**

```markdown
# 옵션 심리 보드

미국 대장주 52종목의 옵션 풋/콜 데이터를 매일 수집해, 초보자도 시장 심리를
한눈에 볼 수 있게 만든 정적 사이트. 개인 학습용이며 투자 조언이 아닙니다.

## 구조
- `collector/` — Python 수집기 (yfinance → 심리 점수 → `site/data/*.json`)
- `site/` — 정적 프론트 (GitHub Pages 서빙 루트)
- `.github/workflows/collect.yml` — 매일 KST 06:10 자동 수집 + 배포

## 로컬 실행
pip install -r requirements.txt
python -m pytest -q
python -m collector.collect --tickers NVDA,AAPL   # 부분 수집
python -m http.server 8123 -d site                 # http://localhost:8123

## 점수 체계
풋/콜 거래량 비율을 종목별 최근 60일 백분위로 정규화한 0~100점.
이력 20거래일 미만이면 절대값 매핑(0.4→90 ~ 1.6→10) 콜드스타트.
```

- [ ] **Step 4: 로컬 YAML 문법 확인**

Run: `python -c "import yaml,glob; [yaml.safe_load(open(f,encoding='utf-8')) for f in glob.glob('.github/workflows/*.yml')]; print('ok')"`
(PyYAML 없으면 `pip install pyyaml`) → Expected: `ok`

- [ ] **Step 5: 커밋** — `git add -A && git commit -m "ci: 일일 수집·배포 워크플로 + README"`

---

### Task 12: GitHub 배포 (사용자 확인 필요)

**⚠ 이 태스크는 외부 공개 행위이므로 각 단계 전 사용자 확인을 받는다.**

- [ ] **Step 1: 사용자에게 push 승인 요청** — repo 이름(제안: `option-sentiment-board`), public 공개 여부 재확인

- [ ] **Step 2: 개인 GitHub 계정에 repo 생성 + push**

```bash
gh auth status || gh auth login          # 개인 계정 로그인 확인
gh repo create option-sentiment-board --public --source . --push
```
(`gh` 미설치/미로그인이면 github.com에서 수동 생성 후 `git remote add origin ... && git push -u origin main`)

- [ ] **Step 3: Pages 활성화** — repo Settings → Pages → Source를 **GitHub Actions**로 설정
  CLI 대안: `gh api repos/{owner}/option-sentiment-board/pages -X POST -f build_type=workflow`

- [ ] **Step 4: 수동 1회 실행으로 파이프라인 검증**

```bash
gh workflow run daily-collect
gh run watch                              # 성공 확인
```
Expected: collect·deploy 잡 모두 green

- [ ] **Step 5: 라이브 확인** — `https://<계정>.github.io/option-sentiment-board/` 접속, 메인 보드·상세 화면·데이터 날짜 확인. 결과 URL을 사용자에게 보고.

---

## 셀프 리뷰 체크 결과

- 스펙 커버리지: §2 데이터소스(T5·6), §3 종목(T1), §4 알고리즘(T2~4), §5 아키텍처(T7·11), §6 오류처리(T6·7·9), §7 UI(T9·10), §8 테스트(각 태스크 TDD + T8 스모크) — 커버됨. §9 Phase 2(한국)는 범위 외.
- Task 7 happy-path 기대 점수 재계산으로 수정 완료(0.5556 → 80점 "매우 강세").
- 타입/필드명 일관성: `latest.json`·`detail/*.json` 필드명이 collect.py와 app.js/stock.js 간 일치 확인(camelCase).
