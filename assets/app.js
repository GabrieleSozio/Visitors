"use strict";

const MESI = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
              "Lug", "Ago", "Set", "Ott", "Nov", "Dic"];
const MESI_FULL = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
                   "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];
const BLUE = "#0b4cff";

let DATA = null;
let attrSelected = new Set();

const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

function esc(s) {
  return String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function digestCard(d) {
  return `<article class="card digest">
    <div class="meta">${esc(d.meta || "")}</div>
    ${d.html}
  </article>`;
}

function empty(msg) {
  return `<div class="empty">${esc(msg)}</div>`;
}

/* --- Tabs --- */
function initTabs() {
  $$(".tab").forEach(btn => {
    btn.addEventListener("click", () => {
      $$(".tab").forEach(b => b.classList.toggle("is-active", b === btn));
      const name = btn.dataset.tab;
      $$(".panel").forEach(p => p.classList.toggle("is-active", p.dataset.panel === name));
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });
}

/* --- Oggi --- */
function renderOggi() {
  const box = $("#oggi-content");
  const gen = DATA.digests.general;
  if (!gen.length) {
    box.innerHTML = empty("Nessun digest ancora. Verranno generati automaticamente ogni giorno.");
    return;
  }
  let html = digestCard(gen[0]);
  const w = DATA.digests.general_weekly;
  if (w.length) {
    html += `<div class="section-head"><h2>Ultima panoramica settimanale</h2></div>` + digestCard(w[0]);
  }
  box.innerHTML = html;
}

/* --- OTA --- */
function renderOta() {
  const sel = $("#ota-select");
  sel.innerHTML = DATA.otas.map(o => `<option value="${o.slug}">${esc(o.name)}</option>`).join("");
  const paint = () => {
    const slug = sel.value;
    const items = DATA.digests.ota[slug] || [];
    const box = $("#ota-content");
    if (!items.length) {
      box.innerHTML = empty("Ancora nessun approfondimento per questa OTA. Sono settimanali, a rotazione.");
      return;
    }
    let html = digestCard(items[0]);
    if (items.length > 1) {
      html += accordionList(items.slice(1), `Storico (${items.length - 1})`);
    }
    box.innerHTML = html;
    bindAccordions(box);
  };
  sel.addEventListener("change", paint);
  paint();
}

/* --- Accordion helpers (archivio + storico OTA) --- */
function accordionItem(d) {
  return `<div class="acc">
    <button class="acc-head">
      <span>${esc(d.title)}</span>
      <span class="chev">&rsaquo;</span>
    </button>
    <div class="acc-body"><div class="meta">${esc(d.meta || "")}</div>${d.html}</div>
  </div>`;
}
function accordionList(items, heading) {
  return `<div class="section-head"><h2>${esc(heading)}</h2></div>` +
    items.map(accordionItem).join("");
}
function bindAccordions(scope) {
  $$(".acc-head", scope).forEach(h => {
    h.addEventListener("click", () => h.parentElement.classList.toggle("open"));
  });
}

/* --- Attrazioni --- */
function renderAttrazioni() {
  const dg = $("#attr-digest");
  const items = DATA.digests.attractions;
  dg.innerHTML = items.length ? digestCard(items[0])
    : empty("Ancora nessun approfondimento attrazioni (settimanale).");

  const attrs = DATA.attractions;
  attrSelected = new Set(attrs.slice(0, 3).map(a => a.slug));

  const ctrl = $("#attr-controls");
  ctrl.innerHTML = attrs.map(a =>
    `<button class="chip ${attrSelected.has(a.slug) ? "on" : ""}" data-slug="${a.slug}">${esc(a.name)}</button>`
  ).join("");
  $$(".chip", ctrl).forEach(c => c.addEventListener("click", () => {
    const s = c.dataset.slug;
    if (attrSelected.has(s)) attrSelected.delete(s); else attrSelected.add(s);
    c.classList.toggle("on");
    drawLine();
  }));

  $("#bar-title").textContent = "Indice stimato — " + MESI_FULL[DATA.month_index];
  drawLine();
  drawBar();
}

/* --- Charts (SVG puri) --- */
function drawLine() {
  const attrs = DATA.attractions.filter(a => attrSelected.has(a.slug));
  const W = 720, H = 300, padL = 34, padR = 12, padT = 12, padB = 26;
  const iw = W - padL - padR, ih = H - padT - padB;
  const x = i => padL + (i / 11) * iw;
  const y = v => padT + (1 - v / 100) * ih;
  const palette = ["#0b4cff", "#1aa7ff", "#6b3cff", "#00b3a4", "#ff7a1a", "#e0397a", "#0b8a3e"];

  let g = "";
  for (let v = 0; v <= 100; v += 25) {
    g += `<line x1="${padL}" y1="${y(v)}" x2="${W - padR}" y2="${y(v)}" stroke="#eef1f7"/>`;
    g += `<text x="${padL - 6}" y="${y(v) + 3}" text-anchor="end" font-size="10" fill="#9aa3b2" font-family="monospace">${v}</text>`;
  }
  MESI.forEach((m, i) => {
    g += `<text x="${x(i)}" y="${H - 8}" text-anchor="middle" font-size="10" fill="#9aa3b2" font-family="monospace">${m}</text>`;
  });

  let paths = "", dots = "";
  attrs.forEach((a, k) => {
    const col = palette[k % palette.length];
    const d = a.seasonality.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
    paths += `<path d="${d}" fill="none" stroke="${col}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>`;
    const cx = x(DATA.month_index), cv = a.seasonality[DATA.month_index];
    dots += `<circle cx="${cx.toFixed(1)}" cy="${y(cv).toFixed(1)}" r="3.5" fill="${col}"/>`;
  });
  // marker mese corrente
  const mx = x(DATA.month_index);
  const marker = `<line x1="${mx}" y1="${padT}" x2="${mx}" y2="${padT + ih}" stroke="#c3d1ff" stroke-dasharray="3 3"/>`;

  let legend = attrs.map((a, k) =>
    `<span style="display:inline-flex;align-items:center;gap:6px;margin:2px 12px 2px 0;font-size:12px;color:#5b6472">
      <span style="width:12px;height:3px;background:${palette[k % palette.length]};border-radius:2px;display:inline-block"></span>${esc(a.name)}</span>`
  ).join("");

  $("#line-chart").innerHTML =
    (attrs.length ? `<svg viewBox="0 0 ${W} ${H}" role="img">${g}${marker}${paths}${dots}</svg>
     <div style="margin-top:10px">${legend}</div>`
      : empty("Seleziona almeno un'attrazione."));
}

function drawBar() {
  const mi = DATA.month_index;
  const rows = DATA.attractions.map(a => ({ name: a.name, v: a.seasonality[mi] }))
    .sort((a, b) => b.v - a.v);
  const rowH = 30, W = 720, padL = 4, padR = 44, labelW = 180;
  const H = rows.length * rowH + 6;
  const barX = padL + labelW, barW = W - barX - padR;
  let svg = "";
  rows.forEach((r, i) => {
    const cy = i * rowH + 6;
    const w = (r.v / 100) * barW;
    svg += `<text x="${padL}" y="${cy + 15}" font-size="12" fill="#26303f">${esc(r.name.length > 26 ? r.name.slice(0, 25) + "…" : r.name)}</text>`;
    svg += `<rect x="${barX}" y="${cy + 4}" width="${barW}" height="16" rx="8" fill="#eef3ff"/>`;
    svg += `<rect x="${barX}" y="${cy + 4}" width="${w.toFixed(1)}" height="16" rx="8" fill="${BLUE}"/>`;
    svg += `<text x="${barX + w + 6}" y="${cy + 16}" font-size="11" fill="#5b6472" font-family="monospace">${r.v}</text>`;
  });
  $("#bar-chart").innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img">${svg}</svg>`;
}

/* --- Archivio --- */
function allDigests() {
  const all = [...DATA.digests.general, ...DATA.digests.general_weekly, ...DATA.digests.attractions];
  Object.values(DATA.digests.ota).forEach(list => all.push(...list));
  return all;
}
function stripHtml(h) { return h.replace(/<[^>]+>/g, " ").toLowerCase(); }

function renderArchivio() {
  const input = $("#search");
  const box = $("#archivio-content");
  const count = $("#search-count");
  const all = allDigests().map(d => ({ ...d, _text: stripHtml(d.html) + " " + d.title.toLowerCase() }));

  const paint = () => {
    const q = input.value.trim().toLowerCase();
    const hits = q ? all.filter(d => d._text.includes(q)) : all;
    count.textContent = q ? `${hits.length} risultati` : `${all.length} digest in archivio. Digita per cercare.`;
    box.innerHTML = hits.slice(0, 60).map(accordionItem).join("") || empty("Nessun risultato.");
    bindAccordions(box);
  };
  input.addEventListener("input", paint);
  paint();
}

/* --- Boot --- */
async function boot() {
  initTabs();
  try {
    const res = await fetch("data/index.json?" + Date.now());
    if (!res.ok) throw new Error(res.status);
    DATA = await res.json();
  } catch (e) {
    $("#oggi-content").innerHTML = empty("Impossibile caricare i dati (data/index.json). "
      + "Esegui build_index.py o attendi il primo workflow.");
    return;
  }
  renderOggi();
  renderOta();
  renderAttrazioni();
  renderArchivio();
  const d = new Date(DATA.generated_at);
  $("#foot-meta").textContent = "aggiornato " + d.toLocaleString("it-IT");
}

boot();
