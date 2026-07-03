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


def run(pairs: list[tuple[str, str]], out_dir, update_market: bool = True) -> int:
    out = Path(out_dir)
    today = datetime.now(timezone.utc).date().isoformat()
    prev_latest = _load(out / "latest.json", {})
    prev = {s["ticker"]: s for s in prev_latest.get("stocks", [])}
    prev_dataasof = prev_latest.get("dataAsOf")

    stocks: list[dict] = []
    failures = 0
    total_call = total_put = 0

    for ticker, name in pairs:
        try:
            raw = fetch_ticker(ticker)
            ratio = scoring.pc_ratio(raw["callVol"], raw["putVol"])
            if ratio is None:
                stocks.append({
                    "ticker": ticker, "name": name, "price": raw["price"], "chg": raw["chg"],
                    "status": "insufficient", "stale": False,
                })
                continue

            score, mode, extreme, history = _scored(ratio, out / "history" / f"{ticker}.json", today)

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
            total_call += raw["callVol"]
            total_put += raw["putVol"]
        except Exception as e:  # noqa: BLE001 — 종목 단위 격리(수집·처리 모두)
            print(f"WARN {ticker}: {e}", file=sys.stderr)
            failures += 1
            if ticker in prev:
                stale = dict(prev[ticker])
                stale["stale"] = True
                stale.setdefault("staleSince", prev_dataasof)
                stocks.append(stale)
            continue

    if pairs and failures / len(pairs) > FAIL_LIMIT:
        print(f"ERROR: {failures}/{len(pairs)} 종목 실패 — 산출물 미생성", file=sys.stderr)
        return 1

    market_score = prev_latest.get("marketScore")
    if update_market:
        market_ratio = scoring.pc_ratio(total_call, total_put)
        market_score = None
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
    sys.exit(run(pairs, args.out, update_market=not args.tickers))


if __name__ == "__main__":
    main()
