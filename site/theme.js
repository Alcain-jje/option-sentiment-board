/* 다크모드: pre-paint 초기화 + 토글 핸들러 (index.html/stock.html 공용) */
(function () {
  var KEY = "osb:theme";
  function preferredTheme() {
    try {
      var saved = localStorage.getItem(KEY);
      if (saved === "dark" || saved === "light") return saved;
    } catch (e) { /* localStorage unavailable */ }
    return (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches)
      ? "dark" : "light";
  }
  document.documentElement.setAttribute("data-theme", preferredTheme());
})();

function initThemeToggle() {
  var KEY = "osb:theme";
  var MOON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
  var SUN = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>';

  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
  }
  function render(btn) {
    var theme = currentTheme();
    btn.innerHTML = theme === "dark" ? SUN : MOON;
    btn.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
    btn.setAttribute("aria-label", theme === "dark" ? "라이트 모드로 전환" : "다크 모드로 전환");
    btn.title = theme === "dark" ? "라이트 모드로 전환" : "다크 모드로 전환";
  }
  var btn = document.getElementById("theme-toggle");
  if (!btn) return;
  render(btn);
  btn.addEventListener("click", function () {
    var next = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem(KEY, next); } catch (e) { /* ignore */ }
    render(btn);
  });
}
