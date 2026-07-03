const $ = (s) => document.querySelector(s);
const barColor = (s) => s >= 80 ? "var(--bull)" : s >= 60 ? "var(--bull-soft)"
  : s >= 40 ? "var(--neutral)" : s >= 20 ? "var(--bear-soft)" : "var(--bear)";
const numColor = (s) => s >= 60 ? "var(--bull-text)" : s >= 40 ? "var(--muted)" : "var(--bear-text)";

let stocks = [];

function cardHtml(s) {
  const badge = s.stale ? `<span class="badge">${s.staleSince ? s.staleSince + " 데이터" : "지난 데이터"}</span>` : "";
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
