// CassavaWatch farmer capture app (vanilla JS)
const I18N = {
  en: {
    instr: "Photograph 3–6 leaves from the top, middle and bottom of ONE plant.",
    take: "📷 Take photo", leaves: "leaves", locating: "Getting location…",
    located: "Location: ", noloc: "Location unavailable — pick your district:", pick: "— district —",
    submit: "Diagnose plant", reset: "Start new plant", sending: "Analysing…",
    need: "Add at least 1 photo (3–6 recommended)", few: "Tip: 3–6 leaves give a much more reliable result.",
    uncertain: "Uncertain — ask an extension officer.", details: "Details", conf: "Confidence",
    saved: "Saved — will sync when online", queued: "reports waiting to sync", synced: "Synced queued reports",
    officer: "Extension officer dashboard →", backend: "Model",
  },
  sw: {
    instr: "Piga picha majani 3–6 ya juu, kati na chini ya mmea MMOJA.",
    take: "📷 Piga picha", leaves: "majani", locating: "Inatafuta mahali…",
    located: "Mahali: ", noloc: "Mahali hapajulikani — chagua wilaya yako:", pick: "— wilaya —",
    submit: "Tambua ugonjwa", reset: "Anza mmea mpya", sending: "Inachambua…",
    need: "Ongeza angalau picha 1 (3–6 zinapendekezwa)", few: "Kidokezo: majani 3–6 hutoa matokeo ya kuaminika zaidi.",
    uncertain: "Haijulikani — muulize afisa ugani.", details: "Maelezo", conf: "Uhakika",
    saved: "Imehifadhiwa — itatumwa ukiwa mtandaoni", queued: "ripoti zinasubiri kutumwa", synced: "Ripoti zimetumwa",
    officer: "Dashibodi ya afisa ugani →", backend: "Modeli",
  },
};
const MAX = 6, QKEY = "cw_queue", LKEY = "cw_lang";
let lang = localStorage.getItem(LKEY) || "en";
let files = [], coords = null;
const $ = id => document.getElementById(id);
const deviceId = localStorage.getItem("cw_dev") || (() => {
  const d = "web-" + Math.random().toString(36).slice(2, 10); localStorage.setItem("cw_dev", d); return d; })();
const t = k => I18N[lang][k] || k;

function applyLang() {
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach(el => el.textContent = t(el.dataset.i18n));
  document.querySelectorAll(".lang button").forEach(b => b.classList.toggle("on", b.dataset.lang === lang));
  showLoc(); showQueue();
}
document.querySelectorAll(".lang button").forEach(b => b.onclick = () => {
  lang = b.dataset.lang; localStorage.setItem(LKEY, lang); applyLang(); });

// ---- photos ----
$("photo").onchange = e => {
  for (const f of e.target.files) if (files.length < MAX) files.push(f);
  e.target.value = ""; renderThumbs();
};
function renderThumbs() {
  $("thumbs").innerHTML = "";
  files.forEach((f, i) => {
    const d = document.createElement("div"); d.className = "thumb";
    const img = document.createElement("img"); img.src = URL.createObjectURL(f);
    const x = document.createElement("button"); x.textContent = "×";
    x.onclick = () => { files.splice(i, 1); renderThumbs(); };
    d.append(img, x); $("thumbs").appendChild(d);
  });
  $("count").textContent = files.length;
  $("submit").disabled = files.length === 0;
}
$("reset").onclick = () => { files = []; renderThumbs(); $("result").hidden = true; };

// ---- location ----
function showLoc() {
  if (coords) { $("locstatus").textContent = t("located") + coords.lat.toFixed(4) + ", " + coords.lon.toFixed(4); $("district").hidden = true; }
  else if (coords === false) { $("locstatus").textContent = t("noloc"); $("district").hidden = false; }
}
if (navigator.geolocation) {
  navigator.geolocation.getCurrentPosition(
    p => { coords = {lat: p.coords.latitude, lon: p.coords.longitude}; showLoc(); },
    () => { coords = false; showLoc(); }, {timeout: 8000, enableHighAccuracy: true});
} else { coords = false; }
function getLatLon() {
  if (coords) return coords;
  const v = $("district").value;
  if (!v) return null;
  const [lat, lon] = v.split(",").map(Number); return {lat, lon};
}

// ---- offline queue (images stored as data URLs) ----
const readAsDataURL = f => new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(f); });
const dataURLToBlob = async u => (await fetch(u)).blob();
function getQueue() { try { return JSON.parse(localStorage.getItem(QKEY)) || []; } catch { return []; } }
function setQueue(q) {
  try { localStorage.setItem(QKEY, JSON.stringify(q)); }
  catch { alert("Storage full — could not queue report"); }
  showQueue();
}
function showQueue() {
  const n = getQueue().length;
  $("queue").hidden = n === 0; $("queue").textContent = `${n} ${t("queued")}`;
}
async function downscale(file) {  // keep queued payload small
  const img = await createImageBitmap(file);
  const s = Math.min(1, 512 / Math.max(img.width, img.height));
  const c = document.createElement("canvas"); c.width = img.width * s; c.height = img.height * s;
  c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
  return new Promise(r => c.toBlob(r, "image/jpeg", 0.85));
}

async function send(blobs, loc) {
  const fd = new FormData();
  blobs.forEach((b, i) => fd.append("images", b, `leaf${i}.jpg`));
  fd.append("lat", loc.lat); fd.append("lon", loc.lon); fd.append("lang", lang); fd.append("device_id", deviceId);
  const r = await fetch("/api/diagnose", {method: "POST", body: fd});
  if (!r.ok) { const e = new Error("HTTP " + r.status); e.http = r.status; throw e; }
  return r.json();
}

$("submit").onclick = async () => {
  if (!files.length) return alert(t("need"));
  const loc = getLatLon();
  if (!loc) { coords = false; showLoc(); return alert(t("noloc")); }
  if (files.length < 3 && !confirm(t("few"))) return;
  $("submit").disabled = true; $("submit").textContent = t("sending");
  const blobs = await Promise.all(files.map(downscale));
  try {
    showResult(await send(blobs, loc));
  } catch (e) {
    if (e.http && e.http < 500) { alert(e.message); }
    else {
      const imgs = await Promise.all(blobs.map(readAsDataURL));
      setQueue([...getQueue(), {imgs, loc, ts: Date.now()}]);
      alert(t("saved"));
      files = []; renderThumbs();
    }
  } finally { $("submit").textContent = t("submit"); $("submit").disabled = files.length === 0; }
};

async function syncQueue() {
  const q = getQueue(); if (!q.length) return;
  const rest = [];
  let last = null;
  for (const item of q) {
    try { last = await send(await Promise.all(item.imgs.map(dataURLToBlob)), item.loc); }
    catch (e) { if (!e.http || e.http >= 500) rest.push(item); }
  }
  setQueue(rest);
  if (last && rest.length < q.length) { showResult(last); $("r-backend").textContent += " · " + t("synced"); }
}
window.addEventListener("online", syncQueue);

function showResult(r) {
  $("result").hidden = false;
  $("result").className = r.uncertain ? "uncertain" : (r.label === "healthy" ? "healthy" : "sick");
  $("r-name").textContent = r.advice.name;
  $("r-conf").textContent = `${t("conf")}: ${(r.confidence * 100).toFixed(0)}% · ${r.n_leaves} ${t("leaves")}`;
  $("r-uncertain").hidden = !r.uncertain;
  $("r-advice").textContent = r.advice.text;
  $("r-probs").innerHTML = Object.entries(r.probs).sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `<tr><td>${k}</td><td>${(v * 100).toFixed(1)}%</td></tr>`).join("");
  $("r-backend").textContent = `${t("backend")}: ${r.backend}`;
  $("result").scrollIntoView({behavior: "smooth"});
}

applyLang(); renderThumbs(); if (navigator.onLine) syncQueue();
