// Simulated now-playing bar. There is no audio: the server keeps a queue in the session and
// records a play history; this script renders the bar and animates a fake progress meter.
(function () {
  const bar = document.getElementById("player-bar");
  if (!bar) return;

  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const el = {
    cover: document.getElementById("player-cover"),
    title: document.getElementById("player-title"),
    artist: document.getElementById("player-artist"),
    toggle: document.getElementById("player-toggle"),
    fill: document.getElementById("player-progress-fill"),
    progress: bar.querySelector(".player-progress"),
  };
  el.cover.addEventListener("error", () => { el.cover.hidden = true; });
  let current = null; // song payload from the server
  let playing = false;
  let elapsed = 0; // ms
  let timer = null;

  function storeElapsed() {
    try { sessionStorage.setItem("player-elapsed", JSON.stringify({ id: current && current.id, elapsed })); } catch (e) {}
  }
  function restoreElapsed(song) {
    try {
      const saved = JSON.parse(sessionStorage.getItem("player-elapsed") || "null");
      return saved && song && saved.id === song.id ? saved.elapsed : 0;
    } catch (e) { return 0; }
  }

  async function call(url, options = {}) {
    const response = await fetch(url, {
      method: options.method || "POST",
      headers: { "X-CSRFToken": csrf, "Content-Type": "application/x-www-form-urlencoded" },
      body: options.body,
    });
    if (!response.ok) throw new Error("player request failed");
    return response.json();
  }

  function render() {
    bar.hidden = !current;
    // Drives the spinning-record animation in app.css.
    document.body.classList.toggle("is-playing", Boolean(current && playing));
    if (!current) return;
    if (current.image) {
      el.cover.src = current.image;
      el.cover.hidden = false;
    } else {
      el.cover.hidden = true;
    }
    el.title.textContent = current.title;
    el.title.href = current.url;
    el.artist.textContent = current.artist;
    el.toggle.firstElementChild.className = playing ? "fa-solid fa-pause" : "fa-solid fa-play";
    const pct = Math.min(100, (elapsed / current.duration_ms) * 100);
    el.fill.style.width = pct + "%";
    el.progress.setAttribute("aria-valuenow", String(Math.round(pct)));
  }

  function tick() {
    elapsed += 500;
    if (current && elapsed >= current.duration_ms) {
      apply(call(bar.dataset.nextUrl), true);
      return;
    }
    storeElapsed();
    render();
  }

  function schedule() {
    clearInterval(timer);
    if (playing && current) timer = setInterval(tick, 500);
  }

  async function apply(promise, reset) {
    try {
      const data = await promise;
      const changed = !current || !data.song || current.id !== data.song.id;
      current = data.song;
      playing = data.playing;
      if (reset || changed) elapsed = reset ? 0 : restoreElapsed(current);
      storeElapsed();
      render();
      schedule();
    } catch (e) { /* leave the bar as it was */ }
  }

  function queueFromPage() {
    const ids = [...document.querySelectorAll(".js-play")].map((b) => b.dataset.song);
    return [...new Set(ids)].slice(0, 100).join(",");
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest(".js-play");
    if (!button) return;
    event.preventDefault();
    const url = bar.dataset.playUrl.replace(/0$/, button.dataset.song);
    apply(call(url, { body: new URLSearchParams({ queue: queueFromPage() }) }), true);
  });
  document.getElementById("player-next").addEventListener("click", () => apply(call(bar.dataset.nextUrl), true));
  document.getElementById("player-prev").addEventListener("click", () => apply(call(bar.dataset.prevUrl), true));
  el.toggle.addEventListener("click", () => apply(call(bar.dataset.toggleUrl), false));

  apply(call(bar.dataset.stateUrl, { method: "GET" }), false);
})();
