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

function priceLineSvg(trend) {
  const n = trend.length;
  if (n === 0) return { svg: "", legend: "" };
  const withPrice = trend
    .map((t, i) => ({ i, price: t.price }))
    .filter((p) => typeof p.price === "number" && p.price !== null && !Number.isNaN(p.price));
  if (withPrice.length < 2) return { svg: "", legend: "" };

  const prices = withPrice.map((p) => p.price);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const range = maxPrice - minPrice || 1;
  const pad = range * 0.1;
  const padMin = minPrice - pad;
  const padMax = maxPrice + pad;
  const padRange = padMax - padMin || 1;

  const W = 1000;
  const H = 130;
  const slotW = W / n;
  const xFor = (i) => slotW * i + slotW / 2;
  const yFor = (price) => H - ((price - padMin) / padRange) * H;

  const points = withPrice.map((p) => ({ x: xFor(p.i), y: yFor(p.price) }));
  const polyPoints = points.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  const dots = points.map((p) =>
    `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="2" fill="#5F5E5A"></circle>`
  ).join("");

  const svg = `<svg class="trend-line" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
    <polyline points="${polyPoints}" fill="none" stroke="#5F5E5A" stroke-width="1.5" vector-effect="non-scaling-stroke"></polyline>
    ${dots}
  </svg>`;
  const legend = `$${minPrice.toLocaleString()} ~ $${maxPrice.toLocaleString()}`;
  return { svg, legend };
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
          ${(() => {
            const trend = Array.isArray(d.trend) ? d.trend.slice(-30) : [];
            const { svg, legend } = priceLineSvg(trend);
            return `<div class="trend-wrap">
                <div class="trend">${trendBars(trend)}</div>
                ${svg}
              </div>
              <div class="trend-legend">
                <span>막대 = 심리 점수 · 선 = 종가</span>
                ${legend ? `<span>${legend}</span>` : ""}
              </div>`;
          })()}
          <div class="note">옵션 심리는 "예언"이 아니라 "지금 돈이 어느 쪽에 몰렸나"예요.
            극단적인 쏠림은 오히려 반대로 움직이는 계기가 되기도 합니다.</div>
        </div>
      </div>
      <p class="sub" style="margin-top:20px">기준: ${d.dataAsOf} 장마감 · 만기 60일 내 옵션 합산 · 현재가 ±20% 행사가 구간</p>
    </div>`;
}
main().catch(() => {
  document.getElementById("detail").innerHTML =
    '<div class="detail"><p>데이터를 불러오지 못했어요. 잠시 후 새로고침해 보세요.</p></div>';
});
