from __future__ import annotations

import time
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

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


def max_pain(strike_call: dict, strike_put: dict) -> float | None:
    """옵션 보유자 총이익이 최소가 되는 만기 가격(맥스페인). OI가 전혀 없으면 None."""
    strikes = sorted(set(strike_call) | set(strike_put))
    if not strikes or (sum(strike_call.values()) + sum(strike_put.values())) == 0:
        return None
    best_k, best_pay = None, None
    for k in strikes:
        pay = sum(oi * max(k - s, 0) for s, oi in strike_call.items())
        pay += sum(oi * max(s - k, 0) for s, oi in strike_put.items())
        if best_pay is None or pay < best_pay:
            best_k, best_pay = k, pay
    return best_k


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
        "maxPain": max_pain(strike_call, strike_put),
    }


def fetch_ticker(symbol: str, retries: int = 2, sleep: float = 2.0, _yf=yf) -> dict:
    """한 종목의 주가 + 60일 내 만기 옵션체인 집계. 지수 백오프 재시도."""
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            t = _yf.Ticker(symbol)
            closes = t.history(period="5d")["Close"]
            if closes.empty:
                raise ValueError("시세 이력 없음")
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
            if attempt < retries:
                time.sleep(sleep * (attempt + 1))
    raise RuntimeError(f"{symbol}: 수집 실패") from last_err
