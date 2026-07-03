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
