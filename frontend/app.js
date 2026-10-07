const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  try { tg.setHeaderColor("#030b14"); tg.setBackgroundColor("#030a12"); } catch (_) {}
}

let pair = "EUR/USD OTC";
let minutes = 2;

const $ = (id) => document.getElementById(id);
const home = $("home"), result = $("result"), error = $("error");

document.querySelectorAll(".pair").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".pair").forEach(x => x.classList.remove("selected"));
    btn.classList.add("selected");
    pair = btn.dataset.pair;
  });
});

document.querySelectorAll(".duration").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".duration").forEach(x => x.classList.remove("selected"));
    btn.classList.add("selected");
    minutes = Number(btn.dataset.minutes);
  });
});

async function analyze() {
  error.textContent = "";
  $("analyze").disabled = true;
  $("analyze").textContent = "ANALYZING…";
  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({pair, minutes, initData: tg?.initData || ""})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Signal unavailable");
    $("signal").textContent = data.signal;
    $("signal-icon").textContent = data.signal === "BUY" ? "↑" : "↓";
    $("result-meta").textContent = `${pair} · ${minutes} min`;
    $("signal-card").classList.toggle("sell", data.signal === "SELL");
    home.classList.remove("active");
    result.classList.add("active");
  } catch (e) {
    error.textContent = e.message;
  } finally {
    $("analyze").disabled = false;
    $("analyze").innerHTML = '<span class="magnify">⌕</span> ANALYZE';
  }
}

$("analyze").addEventListener("click", analyze);
$("again").addEventListener("click", analyze);
$("change").addEventListener("click", () => {
  result.classList.remove("active");
  home.classList.add("active");
});
