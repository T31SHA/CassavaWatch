// CassavaWatch capture app (vanilla JS, no dependencies beyond icons.js)
const I18N = {
  en: {
    step1_of: "Step 1 of 3", step2_of: "Step 2 of 3", step3_of: "Step 3 of 3",
    instr: "Photograph the plant",
    instr2: "Take 3 to 6 photos of single leaves from one plant, in daylight.",
    tile: "Tap to add a leaf photo", tile_sub: "One leaf per photo",
    tile_full: "6 photos added", tile_full_sub: "Remove a photo to add another",
    slot: ["Top", "Top", "Middle", "Middle", "Bottom", "Bottom"],
    count: (n) => `<b>${n}</b> of 6 leaves · add top, middle and bottom leaves`,
    why: (k) => `Add ${k} more ${k === 1 ? "leaf" : "leaves"} to diagnose. Three or more give a reliable result.`,
    locating: "Finding your location", located: "Location found",
    noloc: "Location unavailable. Choose your district instead.", pick_label: "District", pick: "Choose district",
    submit: "Diagnose", sending: "Analysing", sending2: "Checking each leaf, then the whole plant.",
    online: "Online", offline: "Offline", queued: (n) => `${n} waiting to sync`,
    saved: "Saved offline — will sync", synced: (n) => `Synced ${n} ${n === 1 ? "report" : "reports"}`,
    need_loc: "Choose your district first.", storage_full: "Storage is full, so the report could not be saved.",
    single: "Only one leaf was checked, so this result may be wrong. Photograph 3 to 6 leaves next time.",
    chip_healthy: "Healthy", chip_disease: "Disease detected", chip_uncertain: "Uncertain",
    unsure: "Not sure yet", closest: (n) => `Closest match: ${n}`,
    unc_cbsd: "This may be CBSD. It often shows first on older, lower leaves.",
    unc_other: "The photos were not clear enough. Show this plant to an extension officer.",
    lower_hint: "Add 3 to 6 photos of older leaves from the lower part of the plant.",
    what_to_do: "What to do", conf: "Confidence", leaves_n: (n) => `Based on ${n} ${n === 1 ? "leaf" : "leaves"}`,
    details: "All results", src_llm: "AI-assisted · Qwen", src_template: "Standard guidance",
    again: "Report another plant", more_photos: "Add lower-leaf photos", officer: "Extension officer dashboard",
    err: "Something went wrong.", remove: "Remove photo",
  },
  sw: {
    step1_of: "Hatua 1 kati ya 3", step2_of: "Hatua 2 kati ya 3", step3_of: "Hatua 3 kati ya 3",
    instr: "Piga picha mmea",
    instr2: "Piga picha 3 hadi 6 za jani moja moja kutoka mmea mmoja, mchana.",
    tile: "Gusa kuongeza picha ya jani", tile_sub: "Jani moja kwa kila picha",
    tile_full: "Picha 6 zimeongezwa", tile_full_sub: "Ondoa picha ili kuongeza nyingine",
    slot: ["Juu", "Juu", "Kati", "Kati", "Chini", "Chini"],
    count: (n) => `<b>${n}</b> kati ya majani 6 · ongeza majani ya juu, kati na chini`,
    why: (k) => `Ongeza ${k === 1 ? "jani 1" : `majani ${k}`} zaidi ili kutambua. Matatu au zaidi hutoa matokeo ya uhakika.`,
    locating: "Inatafuta mahali ulipo", located: "Mahali pamepatikana",
    noloc: "Mahali hapajulikani. Chagua wilaya yako badala yake.", pick_label: "Wilaya", pick: "Chagua wilaya",
    submit: "Tambua", sending: "Inachambua", sending2: "Inakagua kila jani, kisha mmea mzima.",
    online: "Mtandaoni", offline: "Nje ya mtandao", queued: (n) => `${n} zinasubiri kutumwa`,
    saved: "Imehifadhiwa nje ya mtandao — itatumwa baadaye", synced: (n) => `Ripoti ${n} zimetumwa`,
    need_loc: "Chagua wilaya yako kwanza.", storage_full: "Hifadhi imejaa, ripoti haikuweza kuhifadhiwa.",
    single: "Jani moja tu limekaguliwa, hivyo matokeo yanaweza kuwa si sahihi. Piga picha majani 3 hadi 6 wakati ujao.",
    chip_healthy: "Mzima", chip_disease: "Ugonjwa umegunduliwa", chip_uncertain: "Haijulikani",
    unsure: "Bado haijulikani", closest: (n) => `Inakaribiana zaidi na: ${n}`,
    unc_cbsd: "Huenda ni CBSD. Mara nyingi huonekana kwanza kwenye majani ya zamani ya chini.",
    unc_other: "Picha hazikuwa wazi vya kutosha. Mwonyeshe afisa ugani mmea huu.",
    lower_hint: "Ongeza picha 3 hadi 6 za majani ya zamani kutoka sehemu ya chini ya mmea.",
    what_to_do: "Cha kufanya", conf: "Uhakika", leaves_n: (n) => `Kulingana na ${n === 1 ? "jani 1" : `majani ${n}`}`,
    details: "Matokeo yote", src_llm: "Kwa msaada wa AI · Qwen", src_template: "Mwongozo wa kawaida",
    again: "Ripoti mmea mwingine", more_photos: "Ongeza picha za majani ya chini", officer: "Dashibodi ya afisa ugani",
    err: "Kuna tatizo.", remove: "Ondoa picha",
  },
};
const CLASS_NAMES = {
  en: {cbb: "Bacterial blight", cbsd: "Brown streak", cgm: "Green mite", cmd: "Mosaic", healthy: "Healthy"},
  sw: {cbb: "Madoa ya bakteria", cbsd: "Michirizi ya kahawia", cgm: "Utitiri kijani", cmd: "Batobato", healthy: "Mzima"},
};
const MAX = 6, MIN = 3, QKEY = "cw_queue", LKEY = "cw_lang";
let lang = localStorage.getItem(LKEY) === "sw" ? "sw" : "en";
let files = [], urls = [], coords = null, lastResult = null, step = 1, msgKey = null, msgExtra = "";
const $ = id => document.getElementById(id);
const t = (k, ...a) => { const v = I18N[lang][k] ?? k; return typeof v === "function" ? v(...a) : v; };
const deviceId = localStorage.getItem("cw_dev") || (() => {
  const d = "web-" + Math.random().toString(36).slice(2, 10); localStorage.setItem("cw_dev", d); return d; })();

// ---------- rendering ----------
function render() {
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll(".lang button").forEach(b => b.setAttribute("aria-pressed", b.dataset.lang === lang));
  document.querySelectorAll(".progress span").forEach((s, i) => s.classList.toggle("on", i < step));
  ["s1", "s2", "s3"].forEach((id, i) => { $(id).hidden = step !== i + 1; });
  renderThumbs(); renderLoc(); renderNet(); renderMsg();
  if (lastResult) renderResult();
}
function setStep(n) { step = n; render(); window.scrollTo(0, 0); }
function showMsg(key, extra = "", kind = "error") {
  msgKey = key; msgExtra = extra; $("msg").className = "note" + (kind === "warn" ? " warn" : ""); renderMsg();
}
function clearMsg() { msgKey = null; renderMsg(); }
function renderMsg() {
  $("msg").hidden = !msgKey;
  if (msgKey) $("msg-text").textContent = msgExtra || t(msgKey);
}

let toastTimer;
function toast(text) {
  const el = $("toast");
  el.textContent = text; el.classList.add("show");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove("show"), 3000);
}

document.querySelectorAll(".lang button").forEach(b => b.onclick = () => {
  lang = b.dataset.lang; localStorage.setItem(LKEY, lang); render(); });

// ---------- photos ----------
$("photo").onchange = e => {
  for (const f of e.target.files) if (files.length < MAX) { files.push(f); urls.push(URL.createObjectURL(f)); }
  e.target.value = ""; clearMsg(); renderThumbs();
};
function removePhoto(i) {
  URL.revokeObjectURL(urls[i]); files.splice(i, 1); urls.splice(i, 1); renderThumbs();
}
function clearPhotos() { urls.forEach(u => URL.revokeObjectURL(u)); files = []; urls = []; }
function renderThumbs() {
  const ul = $("thumbs");
  ul.innerHTML = "";
  for (let i = 0; i < MAX; i++) {
    const li = document.createElement("li"); li.className = "slot";
    if (i < files.length) {
      const img = document.createElement("img"); img.src = urls[i]; img.alt = `${t("slot")[i]} ${i + 1}`;
      const x = document.createElement("button"); x.type = "button"; x.className = "remove";
      x.setAttribute("aria-label", `${t("remove")} ${i + 1}`);
      x.innerHTML = `<span>${icon("x")}</span>`;
      x.onclick = () => removePhoto(i);
      li.append(img, x);
    } else {
      li.textContent = t("slot")[i];
    }
    ul.appendChild(li);
  }
  const n = files.length, full = n >= MAX;
  $("photo").disabled = full;
  $("tile").classList.toggle("full", full);
  $("tile-title").textContent = full ? t("tile_full") : t("tile");
  $("tile-sub").textContent = full ? t("tile_full_sub") : t("tile_sub");
  $("count-line").innerHTML = t("count", n);
  $("submit").disabled = n < MIN;
  $("why").textContent = n < MIN ? t("why", MIN - n) : "";
}

// ---------- location ----------
function renderLoc() {
  const ok = !!coords;
  $("locstatus").classList.toggle("ok", ok);
  $("loctext").textContent = ok ? `${t("located")} · ${coords.lat.toFixed(3)}, ${coords.lon.toFixed(3)}`
    : coords === false ? t("noloc") : t("locating");
  $("district-wrap").hidden = coords !== false;
}
function locate() {
  if (!navigator.geolocation) { coords = false; renderLoc(); return; }
  navigator.geolocation.getCurrentPosition(
    p => { coords = {lat: p.coords.latitude, lon: p.coords.longitude}; renderLoc(); },
    () => { coords = false; renderLoc(); }, {timeout: 8000, enableHighAccuracy: true});
}
function getLatLon() {
  if (coords) return coords;
  const v = $("district").value;
  if (!v) return null;
  const [lat, lon] = v.split(",").map(Number); return {lat, lon};
}

// ---------- network pill + offline queue ----------
function getQueue() { try { return JSON.parse(localStorage.getItem(QKEY)) || []; } catch { return []; } }
function setQueue(q) {
  try { localStorage.setItem(QKEY, JSON.stringify(q)); } catch { showMsg("storage_full"); }
  renderNet();
}
function renderNet() {
  const on = navigator.onLine, n = getQueue().length;
  $("net").className = "pill net " + (on ? "on" : "off");
  $("net-text").textContent = (on ? t("online") : t("offline")) + (n ? ` · ${t("queued", n)}` : "");
}
window.addEventListener("offline", renderNet);
window.addEventListener("online", () => { renderNet(); syncQueue(); });

const readAsDataURL = b => new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(b); });
const dataURLToBlob = async u => (await fetch(u)).blob();

async function downscale(file) {  // smaller uploads + small offline queue; falls back to the raw file
  try {
    const img = await createImageBitmap(file);
    const s = Math.min(1, 512 / Math.max(img.width, img.height));
    const c = document.createElement("canvas"); c.width = Math.round(img.width * s); c.height = Math.round(img.height * s);
    c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
    return await new Promise(r => c.toBlob(r, "image/jpeg", 0.85));
  } catch { return file; }
}

class NetError extends Error {}
async function send(blobs, loc) {
  const fd = new FormData();
  blobs.forEach((b, i) => fd.append("images", b, b.name || `leaf${i}.jpg`));
  fd.append("lat", loc.lat); fd.append("lon", loc.lon); fd.append("lang", lang); fd.append("device_id", deviceId);
  let r;
  try { r = await fetch("/api/diagnose", {method: "POST", body: fd}); }
  catch { throw new NetError("network"); }
  if (r.status === 502 || r.status === 504) throw new NetError("gateway");
  const body = await r.json().catch(() => ({}));
  if (!r.ok) { const e = new Error(body.detail || `HTTP ${r.status}`); e.http = r.status; throw e; }
  return body;
}

$("submit").onclick = async () => {
  if (files.length < MIN) return;
  const loc = getLatLon();
  if (!loc) { if (coords !== false) { coords = false; renderLoc(); } return showMsg("need_loc"); }
  clearMsg(); setStep(2);
  const blobs = await Promise.all(files.map(downscale));
  try {
    lastResult = await send(blobs, loc);
    setStep(3);
  } catch (e) {
    setStep(1);
    if (e instanceof NetError) {
      const imgs = await Promise.all(blobs.map(readAsDataURL));
      setQueue([...getQueue(), {imgs, loc, ts: Date.now()}]);
      clearPhotos(); renderThumbs();
      toast(t("saved"));
    } else {
      showMsg("err", e.message);
    }
  }
};

let syncing = false;
async function syncQueue() {
  const q = getQueue();
  if (!q.length || syncing) return;
  syncing = true;
  const rest = [];
  let sent = 0;
  for (const item of q) {
    try { await send(await Promise.all(item.imgs.map(dataURLToBlob)), item.loc); sent++; }
    catch (e) { if (e instanceof NetError || e.http >= 500) rest.push(item); }  // 4xx: drop, would never succeed
  }
  setQueue(rest);
  syncing = false;
  if (sent) toast(t("synced", sent));
}

// ---------- result ----------
const CHIP_ICON = {healthy: "circle-check", uncertain: "circle-help", disease: "triangle-alert"};
function renderResult() {
  const r = lastResult, a = r.advice_all[lang], other = r.advice_all[lang === "en" ? "sw" : "en"];
  const kind = r.uncertain ? "uncertain" : r.label === "healthy" ? "healthy" : "disease";
  $("card").className = "card result " + kind;
  $("r-chip").className = "chip " + kind;
  $("r-chip").innerHTML = icon(CHIP_ICON[kind]) + `<span>${t("chip_" + kind)}</span>`;
  $("r-name").textContent = r.uncertain ? t("unsure") : a.name;
  $("r-name2").textContent = r.uncertain ? t("closest", CLASS_NAMES[lang][r.top_class]) : other.name;
  $("r-summary").textContent = a.summary;
  const pct = Math.round(r.confidence * 100);
  $("r-conf-num").textContent = `${pct}%`;
  $("r-bar").style.width = `${pct}%`;
  $("r-leaves").textContent = t("leaves_n", r.n_leaves);
  $("r-uncertain").hidden = !(r.uncertain && r.top_class === "cbsd");  // otherwise the bullets already say it
  $("r-uncertain-text").textContent = t("unc_cbsd");
  $("r-single").hidden = !r.single_leaf_unreliable;
  $("more-photos").hidden = !r.uncertain;
  $("r-bullets").innerHTML = "";
  for (const b of a.bullets.slice(0, 4)) {
    const li = document.createElement("li");
    li.innerHTML = icon("check"); li.append(document.createTextNode(b));
    $("r-bullets").appendChild(li);
  }
  const src = a.source === "llm" ? "llm" : "template";
  $("r-source").className = "source " + src;
  $("r-source").innerHTML = icon(src === "llm" ? "sparkles" : "book-open") + `<span>${t("src_" + src)}</span>`;
  $("r-probs").innerHTML = Object.entries(r.probs).sort((x, y) => y[1] - x[1]).map(([k, v]) =>
    `<tr><td>${CLASS_NAMES[lang][k]}</td><td><span class="pbar"><span style="width:${(v * 100).toFixed(0)}%"></span></span></td>` +
    `<td class="num">${(v * 100).toFixed(0)}%</td></tr>`).join("");
}
$("again").onclick = () => { clearPhotos(); lastResult = null; clearMsg(); setStep(1); };
$("more-photos").onclick = () => {
  clearPhotos(); lastResult = null; setStep(1);
  showMsg("lower_hint", "", "warn");
};

// ---------- boot ----------
locate(); render();
if (navigator.onLine) syncQueue();
