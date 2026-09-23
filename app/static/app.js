// CassavaWatch farmer capture app (vanilla JS, no dependencies)
const I18N = {
  en: {
    step1: "Photograph", step2: "Diagnosing", step3: "Result",
    instr: "Photograph 3–6 leaves from ONE plant",
    instr2: "Take leaves from the top, middle and bottom of the plant. One leaf per photo, in daylight.",
    take: "📷 Take photo", leaves: "leaves", need_more: "— add more for a reliable result", enough: "— good",
    locating: "📍 Getting your location…", located: "📍 Location found",
    noloc: "📍 Location unavailable.", pick_label: "Choose your district:", pick: "— choose district —",
    submit: "Diagnose this plant", sending: "Diagnosing…", sending2: "Checking each leaf, then the whole plant.",
    online: "Online", offline: "Offline", queued: "queued",
    saved: "No connection. Report saved on this phone — it will be sent automatically when you are online.",
    synced: "Queued reports sent:", need_loc: "Please choose your district first.",
    few: "Only 1–2 leaves: the result may be wrong. Add more leaves for a reliable diagnosis, or continue anyway?",
    single: "Only one leaf was checked. One-leaf results are often wrong — photograph 3–6 leaves next time.",
    badge_healthy: "Healthy", badge_disease: "Disease found", badge_uncertain: "Not sure",
    unc_cbsd: "Possible CBSD. Photograph more leaves from LOWER on the plant — CBSD often shows on older leaves first.",
    unc_other: "Show this plant to an extension officer.",
    what_to_do: "What to do", conf: "Confidence", details: "Details",
    again: "Report another plant", officer: "Extension officer dashboard →",
    err: "Something went wrong:", remove: "Remove photo",
  },
  sw: {
    step1: "Piga picha", step2: "Inatambua", step3: "Matokeo",
    instr: "Piga picha majani 3–6 ya mmea MMOJA",
    instr2: "Chukua majani ya juu, kati na chini ya mmea. Jani moja kwa kila picha, mchana.",
    take: "📷 Piga picha", leaves: "majani", need_more: "— ongeza zaidi kwa matokeo ya uhakika", enough: "— vizuri",
    locating: "📍 Inatafuta mahali ulipo…", located: "📍 Mahali pamepatikana",
    noloc: "📍 Mahali hapajulikani.", pick_label: "Chagua wilaya yako:", pick: "— chagua wilaya —",
    submit: "Tambua ugonjwa wa mmea huu", sending: "Inatambua…", sending2: "Inakagua kila jani, kisha mmea mzima.",
    online: "Mtandaoni", offline: "Nje ya mtandao", queued: "zinasubiri",
    saved: "Hakuna mtandao. Ripoti imehifadhiwa kwenye simu — itatumwa yenyewe ukiwa mtandaoni.",
    synced: "Ripoti zilizosubiri zimetumwa:", need_loc: "Tafadhali chagua wilaya yako kwanza.",
    few: "Majani 1–2 tu: matokeo yanaweza kuwa si sahihi. Ongeza majani zaidi, au uendelee hivyo?",
    single: "Jani moja tu limekaguliwa. Matokeo ya jani moja mara nyingi si sahihi — piga picha majani 3–6 wakati ujao.",
    badge_healthy: "Mzima", badge_disease: "Ugonjwa umepatikana", badge_uncertain: "Haijulikani",
    unc_cbsd: "Huenda ni CBSD. Piga picha majani zaidi ya CHINI ya mmea — CBSD mara nyingi huonekana kwanza kwenye majani ya zamani.",
    unc_other: "Mwonyeshe afisa ugani mmea huu.",
    what_to_do: "Cha kufanya", conf: "Uhakika", details: "Maelezo",
    again: "Ripoti mmea mwingine", officer: "Dashibodi ya afisa ugani →",
    err: "Kuna tatizo:", remove: "Ondoa picha",
  },
};
const CLASS_NAMES = {
  en: {cbb: "Bacterial blight", cbsd: "Brown streak", cgm: "Green mite", cmd: "Mosaic", healthy: "Healthy"},
  sw: {cbb: "Madoa ya bakteria", cbsd: "Michirizi ya kahawia", cgm: "Utitiri kijani", cmd: "Batobato", healthy: "Mzima"},
};
const MAX = 6, QKEY = "cw_queue", LKEY = "cw_lang";
let lang = localStorage.getItem(LKEY) === "sw" ? "sw" : "en";
let files = [], coords = null, lastResult = null, step = 1, msgKey = null, msgExtra = "";
const $ = id => document.getElementById(id);
const t = k => I18N[lang][k] ?? k;
const deviceId = localStorage.getItem("cw_dev") || (() => {
  const d = "web-" + Math.random().toString(36).slice(2, 10); localStorage.setItem("cw_dev", d); return d; })();

// ---------- rendering ----------
function render() {
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll(".lang button").forEach(b => b.setAttribute("aria-pressed", b.dataset.lang === lang));
  document.querySelectorAll(".steps li").forEach(li => {
    const n = +li.dataset.step;
    li.className = n === step ? "on" : n < step ? "done" : "";
  });
  ["s1", "s2", "s3"].forEach((id, i) => { $(id).hidden = step !== i + 1; });
  renderCount(); renderLoc(); renderNet(); renderMsg();
  if (lastResult) renderResult();
}
function setStep(n) { step = n; render(); window.scrollTo(0, 0); }
function showMsg(key, extra = "", kind = "warn") { msgKey = key; msgExtra = extra; $("msg").dataset.kind = kind; renderMsg(); }
function clearMsg() { msgKey = null; renderMsg(); }
function renderMsg() {
  $("msg").hidden = !msgKey;
  if (msgKey) $("msg").textContent = t(msgKey) + (msgExtra ? " " + msgExtra : "");
}

document.querySelectorAll(".lang button").forEach(b => b.onclick = () => {
  lang = b.dataset.lang; localStorage.setItem(LKEY, lang); render(); });

// ---------- photos ----------
$("photo").onchange = e => {
  for (const f of e.target.files) if (files.length < MAX) files.push(f);
  e.target.value = ""; clearMsg(); renderThumbs();
};
function renderThumbs() {
  $("thumbs").innerHTML = "";
  files.forEach((f, i) => {
    const d = document.createElement("div"); d.className = "thumb";
    const img = document.createElement("img"); img.src = URL.createObjectURL(f); img.alt = "";
    const x = document.createElement("button"); x.type = "button"; x.textContent = "×";
    x.setAttribute("aria-label", t("remove"));
    x.onclick = () => { files.splice(i, 1); renderThumbs(); };
    d.append(img, x); $("thumbs").appendChild(d);
  });
  renderCount();
}
function renderCount() {
  $("count").textContent = files.length;
  $("count-hint").textContent = files.length === 0 ? "" : files.length < 3 ? t("need_more") : t("enough");
  $("count-hint").className = "hint " + (files.length >= 3 ? "ok" : "");
  $("submit").disabled = files.length === 0;
}

// ---------- location ----------
function renderLoc() {
  if (coords) $("locstatus").textContent = `${t("located")} (${coords.lat.toFixed(3)}, ${coords.lon.toFixed(3)})`;
  else if (coords === false) $("locstatus").textContent = t("noloc");
  else $("locstatus").textContent = t("locating");
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
  try { localStorage.setItem(QKEY, JSON.stringify(q)); } catch { alert("Storage full — could not save report"); }
  renderNet();
}
function renderNet() {
  const on = navigator.onLine, n = getQueue().length;
  $("net").className = "pill " + (on ? "on" : "off");
  $("net").textContent = `${on ? t("online") : t("offline")}` + (n ? ` · ${n} ${t("queued")}` : "");
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
  if (!files.length) return;
  const loc = getLatLon();
  if (!loc) { if (coords !== false) { coords = false; renderLoc(); } return showMsg("need_loc"); }
  if (files.length < 3 && !confirm(t("few"))) return;
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
      files = []; renderThumbs();
      showMsg("saved", "", "info");
    } else {
      showMsg("err", e.message, "warn");
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
  if (sent) showMsg("synced", String(sent), "ok");
}

// ---------- result ----------
function renderResult() {
  const r = lastResult, a = r.advice_all[lang], other = r.advice_all[lang === "en" ? "sw" : "en"];
  const kind = r.uncertain ? "uncertain" : r.label === "healthy" ? "healthy" : "disease";
  $("card").className = "card " + kind;
  $("r-badge").textContent = t("badge_" + kind);
  $("r-name").textContent = a.name;
  $("r-name2").textContent = other.name;
  $("r-summary").textContent = a.summary;
  $("r-uncertain").hidden = !r.uncertain;
  $("r-uncertain").textContent = r.top_class === "cbsd" ? t("unc_cbsd") : t("unc_other");
  $("r-single").hidden = !r.single_leaf_unreliable;
  $("r-bullets").innerHTML = "";
  for (const b of a.bullets.slice(0, 4)) {
    const li = document.createElement("li"); li.textContent = b; $("r-bullets").appendChild(li);
  }
  $("r-conf").textContent = `${t("conf")}: ${Math.round(r.confidence * 100)}% · ${r.n_leaves} ${t("leaves")}`;
  $("r-probs").innerHTML = Object.entries(r.probs).sort((x, y) => y[1] - x[1])
    .map(([k, v]) => `<tr><td>${CLASS_NAMES[lang][k]}</td><td>${(v * 100).toFixed(0)}%</td></tr>`).join("");
}
$("again").onclick = () => { files = []; lastResult = null; renderThumbs(); clearMsg(); setStep(1); };

// ---------- boot ----------
locate(); render(); renderThumbs();
if (navigator.onLine) syncQueue();
