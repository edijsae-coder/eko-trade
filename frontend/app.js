const tg = window.Telegram?.WebApp;

if (tg) {
  tg.ready();
  tg.expand();

  try {
    tg.setHeaderColor("#030b14");
    tg.setBackgroundColor("#030a12");
  } catch (_) {}
}

let pair = "EUR/USD OTC";
let duration = 2;

const $ = (id) => document.getElementById(id);

const home = $("home");
const result = $("result");
const error = $("error");

document.querySelectorAll(".pair").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".pair").forEach((x) => {
      x.classList.remove("selected");
    });

    btn.classList.add("selected");
    pair = btn.dataset.pair;
  });
});

document.querySelectorAll(".duration").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".duration").forEach((x) => {
      x.classList.remove("selected");
    });

    btn.classList.add("selected");
    duration = Number(btn.dataset.minutes);
  });
});

async function analyze() {
  error.textContent = "";

  $("analyze").disabled = true;
  $("analyze").textContent = "ANALYZING…";

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        pair: pair,
        duration: duration
      })
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Signal unavailable");
    }

    $("signal").textContent = data.signal;

    $("signal-icon").textContent =
      data.signal === "BUY" ? "↑" : "↓";

    $("result-meta").textContent =
      `${data.pair} · ${data.duration} min`;

    $("signal-card").classList.toggle(
      "sell",
      data.signal === "SELL"
    );

    if (data.signal === "SELL") {
  $("signal-card").style.borderColor = "#ff3b5c";
  $("signal-card").style.background =
    "linear-gradient(145deg, rgba(90, 8, 25, .85), rgba(25, 4, 12, .98))";

  $("signal-icon").style.borderColor = "#ff3b5c";
  $("signal-icon").style.color = "#ff3b5c";

  $("signal").style.color = "#ff3b5c";
} else {
  $("signal-card").style.borderColor = "#10ed9a";
  $("signal-card").style.background =
    "linear-gradient(145deg, rgba(0, 75, 59, .65), rgba(3, 16, 25, .98))";

  $("signal-icon").style.borderColor = "#18f4a0";
  $("signal-icon").style.color = "#18f4a0";

  $("signal").style.color = "#15efa0";
}
    home.classList.remove("active");
    result.classList.add("active");

  } catch (e) {
    error.textContent = e.message;

  } finally {
    $("analyze").disabled = false;

    $("analyze").innerHTML =
      '<span class="magnify">⌕</span> ANALYZE';
  }
}

$("analyze").addEventListener("click", analyze);

$("again").addEventListener("click", analyze);

$("change").addEventListener("click", () => {
  result.classList.remove("active");
  home.classList.add("active");
});
