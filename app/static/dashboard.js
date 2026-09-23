// CassavaWatch officer dashboard (vanilla JS + Leaflet)
const $ = id => document.getElementById(id);
const DISEASES = ["cmd", "cbsd", "cgm", "cbb"];
const NAMES = {cmd: "Cassava mosaic", cbsd: "Brown streak", cgm: "Green mite", cbb: "Bacterial blight",
               healthy: "Healthy", uncertain: "Uncertain"};
const SHORT = {cmd: "CMD", cbsd: "CBSD", cgm: "CGM", cbb: "CBB", healthy: "Healthy", uncertain: "Uncertain"};
const FILTERS = ["all", ...DISEASES, "healthy", "uncertain"];
const CELL = 0.1;  // matches the 0.1° grid used by app/surveillance.py
// Fixed town list for labelling alert cells (no reverse geocoding).
const TOWNS = [
  ["Busia", 0.461, 34.112], ["Nambale", 0.456, 34.251], ["Butula", 0.339, 34.338], ["Malaba", 0.636, 34.281],
  ["Funyula", 0.296, 34.108], ["Port Victoria", 0.098, 33.976],
  ["Mwanza", -2.516, 32.917], ["Misungwi", -2.850, 33.083], ["Magu", -2.583, 33.433],
  ["Kisesa", -2.553, 33.041], ["Nyamagana", -2.530, 32.900], ["Igoma", -2.458, 32.960],
];

const state = {days: 7, filter: "all", reports: [], alerts: [], allAlerts: []};
const kindOf = d => d === "healthy" ? "healthy" : d === "uncertain" ? "uncertain" : "disease";
const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const parseTs = ts => Date.parse(ts.endsWith("Z") ? ts : ts + "Z");
const km = (a, b, c, d) => Math.round(Math.hypot((a - c) * 111, (b - d) * 111 * Math.cos(a * Math.PI / 180)));
function place(lat, lon) {
  let best = null;
  for (const [n, tl, tn] of TOWNS) { const d = km(lat, lon, tl, tn); if (!best || d < best[1]) best = [n, d]; }
  return best[1] <= 3 ? best[0] : `${best[1]} km from ${best[0]}`;
}
function age(ts) {
  const m = Math.max(0, (Date.now() - parseTs(ts)) / 6e4);
  return m < 60 ? `${Math.round(m)}m` : m < 1440 ? `${Math.round(m / 60)}h` : `${Math.floor(m / 1440)}d`;
}
const fmtDate = ts => new Date(parseTs(ts)).toLocaleString("en-GB", {day: "numeric", month: "short", hour: "2-digit", minute: "2-digit"});
const cellOf = r => `${Math.floor(r.lat / CELL)}_${Math.floor(r.lon / CELL)}`;

let toastTimer;
function toast(text) {
  const el = $("toast"); el.textContent = text; el.classList.add("show");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove("show"), 3000);
}

// ---------- map ----------
const dark = matchMedia("(prefers-color-scheme: dark)");
const map = L.map("map", {scrollWheelZoom: false, zoomControl: true, attributionControl: true,
  renderer: L.canvas({tolerance: 6})}).setView([-1.0, 33.5], 6);
map.attributionControl.setPrefix(false);
// Minimal grey basemap + label overlay. CARTO Positron / Dark Matter now watermark tiles unless an API key
// is supplied, so Esri's keyless Light / Dark Gray Canvas is used (same visual role).
const TILE = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_{v}_Gray_{l}/MapServer/tile/{z}/{y}/{x}";
const TILE_ATTR = 'Tiles © <a href="https://www.esri.com">Esri</a> — Esri, HERE, Garmin, © OpenStreetMap contributors';
map.createPane("labels").style.zIndex = 350;  // above the basemap, below markers and alert cells
map.getPane("labels").style.pointerEvents = "none";
let tiles = [];
function setTiles() {
  tiles.forEach(t => map.removeLayer(t));
  const v = dark.matches ? "Dark" : "Light";
  tiles = [L.tileLayer(TILE.replace("{v}", v).replace("{l}", "Base"), {maxZoom: 16, attribution: TILE_ATTR}),
           L.tileLayer(TILE.replace("{v}", v).replace("{l}", "Reference"), {maxZoom: 16, pane: "labels"})];
  tiles.forEach(t => t.addTo(map));
}
setTiles();
const reportLayer = L.layerGroup().addTo(map), alertLayer = L.layerGroup().addTo(map);
const legend = L.control({position: "bottomleft"});
legend.onAdd = () => {
  const d = L.DomUtil.create("div", "legend");
  d.innerHTML = `<div><i style="background:var(--healthy)"></i>Healthy</div><div><i style="background:var(--disease)"></i>Disease</div>`
    + `<div><i style="background:var(--uncertain)"></i>Uncertain</div><div><i class="sq"></i>Alert cell</div>`;
  return d;
};
legend.addTo(map);
dark.addEventListener("change", () => { setTiles(); drawMap(); });

let fitted = false;
const alertRects = new Map();
function drawMap() {
  const col = {healthy: css("--healthy"), disease: css("--disease"), uncertain: css("--uncertain")};
  reportLayer.clearLayers();
  const shown = filteredReports();
  for (const r of shown) {
    L.circleMarker([r.lat, r.lon], {radius: 3, stroke: false, fillOpacity: 0.7, fillColor: col[kindOf(r.disease)]})
      .bindPopup(`<div class="pop-title"><span class="dot" style="color:${col[kindOf(r.disease)]}"></span>${esc(NAMES[r.disease] || r.disease)}</div>
        <div class="pop-meta">${Math.round(r.confidence * 100)}% confidence · ${r.n_leaves} leaves · ${age(r.ts)} ago</div>`)
      .addTo(reportLayer);
  }
  $("map-empty").hidden = shown.length > 0;
  alertLayer.clearLayers(); alertRects.clear();
  for (const a of state.alerts) {
    const [[s, w], [n, e]] = a.bounds, where = place((s + n) / 2, (w + e) / 2);
    const rect = L.rectangle(a.bounds, {color: col.disease, weight: 1.5, fillColor: col.disease, fillOpacity: 0.1})
      .bindPopup(`<div class="pop-title">${esc(SHORT[a.disease] || a.disease)} alert · ${esc(where)}</div>
        <div class="pop-meta">${a.observed} observed · ${a.expected.toFixed(1)} expected · ×${a.ratio.toFixed(1)}</div>`)
      .addTo(alertLayer);
    alertRects.set(a.id, rect);
  }
  if (!fitted && state.reports.length) {
    map.fitBounds(state.reports.map(r => [r.lat, r.lon]), {paddingTopLeft: [24, 24], paddingBottomRight: [24, 140]}); fitted = true;  // clear of the legend
  }
}

// ---------- data ----------
const inRange = (r, from, to) => { const t = parseTs(r.ts); return t >= from && t < to; };
function periodReports(offset = 0) {
  const now = Date.now(), span = state.days * 864e5;
  return state.reports.filter(r => inRange(r, now - span * (offset + 1), now - span * offset));
}
function filteredReports() {
  return periodReports().filter(r => state.filter === "all" || r.disease === state.filter);
}

function setDelta(id, cur, prev, upIsGood, unit = null) {
  const el = $(id), label = `vs prior ${state.days}d`;
  if (!prev) { el.className = "delta neutral"; el.textContent = cur ? `No data for prior ${state.days}d` : ""; return; }
  const diff = cur - prev, pct = Math.round((diff / prev) * 100);
  if (diff === 0) { el.className = "delta neutral"; el.textContent = `No change ${label}`; return; }
  el.className = "delta " + (diff > 0 ? (upIsGood ? "up-good" : "up-bad") : (upIsGood ? "down-bad" : "down-good"));
  el.textContent = `${diff > 0 ? "+" : "−"}${unit ? `${Math.abs(diff)} ${unit(Math.abs(diff))}` : Math.abs(pct) + "%"} ${label}`;
}

function drawKpis() {
  const cur = periodReports(), prev = periodReports(1), d = state.days;
  $("k-reports-l").textContent = `Reports · ${d}d`;
  $("k-top-l").textContent = `Top disease · ${d}d`;
  $("k-cells-l").textContent = `Cells monitored · ${d}d`;
  $("k-reports").textContent = cur.length;
  setDelta("k-reports-d", cur.length, prev.length, true);

  $("k-alerts").textContent = state.alerts.length;
  const fresh = state.allAlerts.filter(a => Date.now() - parseTs(a.ts) < d * 864e5).length;
  $("k-alerts-d").className = "delta " + (fresh ? "up-bad" : "neutral");
  $("k-alerts-d").textContent = fresh ? `${fresh} raised in last ${d}d` : `None raised in last ${d}d`;

  const count = rs => rs.reduce((m, r) => (DISEASES.includes(r.disease) && (m[r.disease] = (m[r.disease] || 0) + 1), m), {});
  const cc = count(cur), pc = count(prev);
  const top = Object.keys(cc).sort((a, b) => cc[b] - cc[a])[0];
  if (top) {
    $("k-top").innerHTML = `${SHORT[top]}<small class="num">${cc[top]}</small>`;
    $("k-top").title = NAMES[top];
    setDelta("k-top-d", cc[top], pc[top] || 0, false, n => n === 1 ? "case" : "cases");
  } else { $("k-top").textContent = "None"; $("k-top-d").textContent = ""; }

  const cells = new Set(cur.map(cellOf)).size;
  $("k-cells").textContent = cells;
  setDelta("k-cells-d", cells, new Set(prev.map(cellOf)).size, true, n => n === 1 ? "cell" : "cells");
}

function drawAlerts() {
  const ul = $("alert-list");
  ul.innerHTML = "";
  $("alerts-empty").hidden = state.alerts.length > 0;
  $("nav-alerts").textContent = state.alerts.length || "";
  for (const a of state.alerts) {
    const [[s, w], [n, e]] = a.bounds, clat = (s + n) / 2, clon = (w + e) / 2, where = place(clat, clon);
    const li = document.createElement("li");
    li.className = "alert-card";
    li.innerHTML = `
      <div class="alert-top"><span class="chip disease">${esc(SHORT[a.disease] || a.disease)} · ${esc(NAMES[a.disease] || "")}</span>
        <span class="age num" title="${esc(fmtDate(a.ts))}">${age(a.ts)}</span></div>
      <button type="button" class="alert-place">${esc(where)}</button>
      <p class="coords num">${clat.toFixed(2)}, ${clon.toFixed(2)}</p>
      <p class="metrics num"><b>${a.observed}</b> observed · ${a.expected.toFixed(1)} expected · ×${a.ratio.toFixed(1)}</p>
      <div class="alert-foot"><span class="pval num">p = ${a.p_value.toExponential(1)}</span>
        <button type="button" class="btn btn-ghost review"><i data-icon="check" class="sm"></i>Mark reviewed</button></div>`;
    icons(li);
    const focus = () => {
      map.fitBounds(a.bounds, {maxZoom: 11, animate: !matchMedia("(prefers-reduced-motion: reduce)").matches});
      alertRects.get(a.id)?.openPopup();
      ul.querySelectorAll(".sel").forEach(x => x.classList.remove("sel")); li.classList.add("sel");
      if (innerWidth < 1180) document.querySelector(".map-card").scrollIntoView({behavior: "smooth", block: "center"});
    };
    li.onclick = focus;
    li.querySelector(".alert-place").setAttribute("aria-label", `Show ${where} alert on map`);
    li.querySelector(".review").onclick = async ev => {
      ev.stopPropagation();
      const r = await fetch(`/api/alerts/${a.id}/review`, {method: "POST"});
      toast(r.ok ? `Marked reviewed · ${SHORT[a.disease]} near ${where}` : "Could not update the alert");
      loadAlerts();
    };
    ul.appendChild(li);
  }
}

function drawTable() {
  const rows = filteredReports();
  $("reports-count").textContent = `${rows.length} in last ${state.days}d`;
  $("reports-empty").hidden = rows.length > 0;
  const col = {healthy: "var(--healthy)", disease: "var(--disease)", uncertain: "var(--uncertain)"};
  $("report-rows").innerHTML = rows.map(r => `<tr>
    <td class="num">${esc(fmtDate(r.ts))}</td>
    <td><span class="dis"><span class="dot" style="color:${col[kindOf(r.disease)]}"></span>${esc(NAMES[r.disease] || r.disease)}</span></td>
    <td class="r">${Math.round(r.confidence * 100)}%</td><td class="r">${r.n_leaves}</td>
    <td class="r">${r.lat.toFixed(3)}</td><td class="r">${r.lon.toFixed(3)}</td>
    <td class="dev">${esc(r.device_id || "—")}</td></tr>`).join("");
}

function drawChips() {
  $("chips").innerHTML = FILTERS.map(f => {
    const dot = f === "all" ? "" : `<span class="dot" style="color:var(--${kindOf(f)})"></span>`;
    return `<button type="button" class="filter" data-f="${f}" aria-pressed="${f === state.filter}">${dot}${f === "all" ? "All" : SHORT[f]}</button>`;
  }).join("");
  $("chips").querySelectorAll("button").forEach(b => b.onclick = () => {
    state.filter = b.dataset.f; drawChips(); drawMap(); drawTable(); });
}

function drawAll() { drawKpis(); drawAlerts(); drawMap(); drawTable(); }

async function loadAlerts() {
  const [active, all] = await Promise.all(["/api/alerts", "/api/alerts?status=all"].map(u => fetch(u).then(r => r.json())));
  state.alerts = active; state.allAlerts = all;
  drawKpis(); drawAlerts(); drawMap();
}
async function loadAll() {
  const [reports, active, all] = await Promise.all(
    ["/api/reports?days=120", "/api/alerts", "/api/alerts?status=all"].map(u => fetch(u).then(r => r.json())));
  Object.assign(state, {reports, alerts: active, allAlerts: all});
  $("updated").textContent = `Updated ${new Date().toLocaleTimeString("en-GB", {hour: "2-digit", minute: "2-digit"})}`;
  drawAll();
}
async function loadStatus() {
  try {
    const c = await (await fetch("/api/config")).json();
    $("st-model").textContent = c.model_backend === "none" ? "Not installed" : c.model_backend.toUpperCase();
    $("st-advice").textContent = c.advisory_mode === "llm" ? c.qwen_model.split("/").pop() : "Standard guidance";
    $("st-advice").title = c.advisory_mode === "llm" ? `AI-assisted: ${c.qwen_model}` : "Template advice";
  } catch { $("st-model").textContent = $("st-advice").textContent = "Unavailable"; }
}

// ---------- controls ----------
$("range").querySelectorAll("button").forEach(b => b.onclick = () => {
  state.days = +b.dataset.days;
  $("range").querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", x === b));
  drawKpis(); drawMap(); drawTable();
});
$("run").onclick = async () => {
  const r = await (await fetch("/api/surveillance/run", {method: "POST"})).json();
  toast(`Surveillance run · ${r.length} active ${r.length === 1 ? "alert" : "alerts"}`);
  loadAll();
};
const pop = $("info-pop"), infoBtn = $("info-btn");
function setPop(open) { pop.hidden = !open; infoBtn.setAttribute("aria-expanded", open); }
infoBtn.onclick = e => { e.stopPropagation(); setPop(pop.hidden); };
document.addEventListener("click", e => { if (!pop.hidden && !pop.contains(e.target)) setPop(false); });
document.addEventListener("keydown", e => { if (e.key === "Escape" && !pop.hidden) { setPop(false); infoBtn.focus(); } });

// nav: highlight the section in view
const navLinks = [...document.querySelectorAll(".nav a")];
const spy = new IntersectionObserver(entries => {
  for (const en of entries) if (en.isIntersecting) {
    navLinks.forEach(a => a.setAttribute("aria-current", a.getAttribute("href") === "#" + en.target.id));
  }
}, {rootMargin: "-30% 0px -60% 0px"});
["overview", "alerts", "reports"].forEach(id => spy.observe($(id)));

drawChips(); loadAll(); loadStatus();
