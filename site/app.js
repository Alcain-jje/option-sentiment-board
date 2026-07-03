const $ = (s) => document.querySelector(s);
const barColor = (s) => s >= 80 ? "var(--bull)" : s >= 60 ? "var(--bull-soft)"
  : s >= 40 ? "var(--neutral)" : s >= 20 ? "var(--bear-soft)" : "var(--bear)";
const numColor = (s) => s >= 60 ? "var(--bull-text)" : s >= 40 ? "var(--muted)" : "var(--bear-text)";

let stocks = [];
const state = { sort: "desc", sector: null };

function sectorBadgeHtml(s) {
  const sector = s.sector || "기타";
  return `<span class="badge badge-sector">${sector}</span>`;
}

function scoreChgHtml(s) {
  if (s.stale) return "";
  const c = s.scoreChg;
  if (c === undefined || c === null) return "";
  if (c === 0) return `<p class="score-chg" style="color:var(--muted)">전 거래일과 같음</p>`;
  if (c > 0) return `<p class="score-chg" style="color:var(--bull-text)">▲ 전 거래일보다 +${c}</p>`;
  return `<p class="score-chg" style="color:var(--bear-text)">▼ 전 거래일보다 ${c}</p>`;
}

function sparkHtml(s) {
  if (!Array.isArray(s.spark) || s.spark.length === 0) return "";
  const SLOTS = 10;
  const values = s.spark.slice(-SLOTS);
  const padCount = Math.max(SLOTS - values.length, 0);
  const empty = Array.from({ length: padCount }, () =>
    `<div class="spark-bar" style="height:15%;background:#EFEDE5"></div>`
  );
  const filled = values.map((v) =>
    `<div class="spark-bar" style="height:${Math.max(v, 12)}%;background:${barColor(v)}"></div>`
  );
  const bars = empty.concat(filled).join("");
  return `<div class="spark" title="최근 10일 심리 흐름 (매일 채워져요)">${bars}</div>`;
}

function cardHtml(s) {
  const staleBadge = s.stale ? `<span class="badge">${s.staleSince ? s.staleSince + " 데이터" : "지난 데이터"}</span>` : "";
  if (s.status === "insufficient") {
    return `<a class="card" href="stock.html?t=${s.ticker}">
      <div class="card-head">
        <div class="card-head-left">
          <span class="tkr">${s.ticker}<small>${s.name}</small></span>
          <div class="badges">${sectorBadgeHtml(s)}${staleBadge}</div>
        </div>
        <span class="score" style="color:var(--muted)">–</span>
      </div>
      <p class="desc">옵션 거래가 적어 심리 점수를 계산하지 않았어요</p></a>`;
  }
  const chgClass = s.chg >= 0 ? "chg-up" : "chg-down";
  const chg = s.chg >= 0 ? `+${s.chg.toFixed(2)}%` : `${s.chg.toFixed(2)}%`;
  return `<a class="card" href="stock.html?t=${s.ticker}">
    <div class="card-head">
      <div class="card-head-left">
        <span class="tkr">${s.ticker}<small>${s.name}</small></span>
        <div class="badges">${sectorBadgeHtml(s)}${staleBadge}</div>
      </div>
      <div class="card-head-right">
        <span class="score" style="color:${numColor(s.score)}">${s.score}</span>
        ${scoreChgHtml(s)}
      </div>
    </div>
    ${sparkHtml(s)}
    <p class="price">$${s.price.toLocaleString()} · <span class="${chgClass}">${chg}</span></p>
    <p class="desc">${s.ratioText}</p></a>`;
}

function sectorsBySummary() {
  const map = new Map();
  stocks.forEach((s) => {
    const sector = s.sector || "기타";
    if (!map.has(sector)) map.set(sector, { sector, okCount: 0, scoreSum: 0 });
    const entry = map.get(sector);
    if (s.status === "ok") {
      entry.okCount += 1;
      entry.scoreSum += s.score;
    }
  });
  return Array.from(map.values())
    .filter((e) => e.okCount > 0)
    .sort((a, b) => b.okCount - a.okCount);
}

function renderChips() {
  const sectors = sectorsBySummary();
  const chipHtml = (label, active, sector, avg) => {
    const avgHtml = avg !== undefined
      ? ` <span style="color:${active ? "#fff" : numColor(avg)}">${avg}</span>`
      : "";
    return `<button class="chip${active ? " on" : ""}" data-sector="${sector === null ? "" : sector}">${label}${avgHtml}</button>`;
  };
  const parts = [chipHtml("전체", state.sector === null, null)];
  sectors.forEach((e) => {
    const avg = Math.round(e.scoreSum / e.okCount);
    parts.push(chipHtml(e.sector, state.sector === e.sector, e.sector, avg));
  });
  $("#chips").innerHTML = parts.join("");
}

function renderSummary() {
  const ok = stocks.filter((s) => s.status === "ok");
  const bullCount = ok.filter((s) => s.score >= 60).length;
  const bearCount = ok.filter((s) => s.score <= 39).length;
  $("#cell-bull").innerHTML = `<span style="color:var(--bull-text)">${bullCount}</span><span class="metric-suffix"> / ${stocks.length}</span>`;
  $("#cell-bear").innerHTML = `<span style="color:var(--bear-text)">${bearCount}</span><span class="metric-suffix"> / ${stocks.length}</span>`;

  let extreme = null;
  ok.forEach((s) => {
    const dist = Math.abs(s.score - 50);
    if (!extreme || dist > Math.abs(extreme.score - 50)) extreme = s;
  });
  if (extreme) {
    $("#cell-extreme").href = `stock.html?t=${extreme.ticker}`;
    $("#cell-extreme-value").innerHTML =
      `<span style="color:${numColor(extreme.score)}">${extreme.ticker} ${extreme.score}점</span>`;
  } else {
    $("#cell-extreme-value").textContent = "–";
  }
}

function render() {
  const ok = stocks.filter((s) => s.status === "ok" && (!state.sector || (s.sector || "기타") === state.sector));
  const rest = stocks.filter((s) => s.status !== "ok" && (!state.sector || (s.sector || "기타") === state.sector));
  if (state.sort === "desc") ok.sort((a, b) => b.score - a.score);
  if (state.sort === "asc") ok.sort((a, b) => a.score - b.score);
  if (state.sort === "name") ok.sort((a, b) => a.ticker.localeCompare(b.ticker));
  $("#grid").innerHTML = ok.concat(rest).map(cardHtml).join("");
  renderChips();
}

async function main() {
  const d = await (await fetch("data/latest.json")).json();
  $("#asof").textContent =
    `${d.dataAsOf} 미국 장마감 기준 · 매일 아침 자동 업데이트 · ${d.stocks.length}종목`;
  if (Date.now() - Date.parse(d.updatedAt) > 48 * 3600 * 1000) {
    $("#banner").innerHTML =
      '<div class="banner">데이터가 48시간 이상 갱신되지 않았어요. 수집 파이프라인 점검이 필요할 수 있습니다.</div>';
  }
  if (d.marketScore !== null && d.marketScore !== undefined) {
    const label = d.marketScore >= 60 ? "강세" : d.marketScore >= 40 ? "중립" : "약세";
    $("#cell-gauge").hidden = false;
    $("#market-label").textContent = `${label} · ${d.marketScore}점`;
    $("#market-label").style.color = numColor(d.marketScore);
    $("#market-dot").style.left = `${d.marketScore}%`;
    $("#market-dot").style.background = barColor(d.marketScore);
  }
  stocks = d.stocks;
  renderSummary();
  render();
  $("#toolbar").addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    document.querySelectorAll("#toolbar button").forEach((b) => b.classList.remove("on"));
    btn.classList.add("on");
    state.sort = btn.dataset.sort;
    render();
  });
  $("#chips").addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    state.sector = btn.dataset.sector === "" ? null : btn.dataset.sector;
    render();
  });
}
main().catch(() => {
  document.getElementById("asof").textContent = "데이터를 불러오지 못했어요";
  document.getElementById("banner").innerHTML =
    '<div class="banner">데이터 파일을 읽을 수 없습니다. 잠시 후 새로고침해 보세요.</div>';
});
