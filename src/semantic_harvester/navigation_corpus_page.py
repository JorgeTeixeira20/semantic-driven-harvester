"""Página do protótipo do corpus da Fase 1 (HTML, CSS e JavaScript sem dependências).

Organização (revista em 2026-10-23, depois do feedback do autor): pesquisa no
topo, barra que diz o que está a ser mostrado, separadores Notícias e
Estatísticas, e "Sobre os dados" (versão do site e texto) em linguagem simples.

Lê `data.js` (`window.SDH_DATA`, escrito por `navigation_corpus.py`) por
`<script>`, o que funciona aberto do disco (`file://`), ao contrário de `fetch`.
"""

PAGE = r"""<!doctype html>
<html lang="pt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Record no Arquivo.pt</title>
<style>
:root {
  --bg: #f5f4f1; --panel: #ffffff; --ink: #1d1d1b; --muted: #6b6b66; --line: #e3e2dd;
  --accent: #b3261e; --accent-soft: #f6e1df; --bar: #d9a19c; --bar-on: #b3261e; --chip: #efeee9;
  --top: #1d1d1b; --top-ink: #f5f4f1; --top-muted: #b9b8b1; --top-field: #2c2c29;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #161615; --panel: #1f1f1d; --ink: #ecebe6; --muted: #a3a29b; --line: #34342f;
    --accent: #ef8a80; --accent-soft: #3d2422; --bar: #7a4540; --bar-on: #ef8a80; --chip: #2b2b28;
    --top: #0e0e0d; --top-ink: #ecebe6; --top-muted: #a3a29b; --top-field: #24241f;
  }
}
:root[data-theme="dark"] {
  --bg: #161615; --panel: #1f1f1d; --ink: #ecebe6; --muted: #a3a29b; --line: #34342f;
  --accent: #ef8a80; --accent-soft: #3d2422; --bar: #7a4540; --bar-on: #ef8a80; --chip: #2b2b28;
  --top: #0e0e0d; --top-ink: #ecebe6; --top-muted: #a3a29b; --top-field: #24241f;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
.wrap { max-width: 1180px; margin: 0 auto; padding: 0 16px; }
header.top { background: var(--top); color: var(--top-ink); border-bottom: 4px solid var(--accent); }
header.top .wrap { padding-top: 20px; padding-bottom: 18px; }
h1 { font-size: 1.5rem; margin: 0 0 2px; }
h1 span { color: var(--accent); }
.sub { color: var(--top-muted); margin: 0 0 14px; font-size: .9rem; }
.search { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); gap: 8px; }
.search input { width: 100%; padding: 11px 14px; border-radius: 8px; border: 1px solid transparent;
  background: var(--top-field); color: var(--top-ink); font: inherit; font-size: 1rem; min-width: 0; }
.search input::placeholder { color: var(--top-muted); }
.search input:focus { outline: 2px solid var(--accent); }
.bar { position: sticky; top: 0; z-index: 5; background: var(--bg); border-bottom: 1px solid var(--line); }
.bar .wrap { padding-top: 10px; padding-bottom: 10px; }
.filters { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
.filters select, button.btn { width: 100%; padding: 8px 10px; border: 1px solid var(--line);
  border-radius: 8px; background: var(--panel); color: var(--ink); font: inherit; min-width: 0;
  text-overflow: ellipsis; white-space: nowrap; overflow: hidden; }
button.btn { width: auto; cursor: pointer; }
.context { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 10px;
  padding: 8px 12px; border-radius: 8px; background: var(--accent-soft); font-size: .92rem; }
.context.none { background: transparent; padding-left: 0; color: var(--muted); }
.context b { font-variant-numeric: tabular-nums; }
.tabs { display: flex; gap: 4px; margin: 16px 0 12px; border-bottom: 1px solid var(--line); }
.tab { border: 0; background: none; font: inherit; padding: 8px 14px; cursor: pointer; color: var(--muted);
  border-bottom: 3px solid transparent; margin-bottom: -1px; }
.tab.on { color: var(--ink); border-bottom-color: var(--accent); font-weight: 600; }
h2 { font-size: .8rem; text-transform: uppercase; letter-spacing: .06em; color: var(--muted);
  margin: 0 0 10px; font-weight: 600; }
.kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
.kpi, .panel { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; }
.kpi { padding: 12px 14px; border-top: 3px solid var(--accent); }
.kpi b { display: block; font-size: 1.45rem; font-variant-numeric: tabular-nums; }
.kpi span { color: var(--muted); font-size: .85rem; }
.panel { padding: 14px; margin-bottom: 16px; min-width: 0; }
.grid2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-bottom: 16px; }
.grid2 > .panel { margin-bottom: 0; }
.years { display: flex; align-items: flex-end; gap: 2px; height: 90px; overflow-x: auto; }
.ycol { flex: 1 0 9px; display: flex; flex-direction: column; justify-content: flex-end;
  align-items: stretch; height: 100%; cursor: pointer; border: 0; background: none; padding: 0; }
.ycol i { display: block; background: var(--bar); border-radius: 2px 2px 0 0; min-height: 1px; }
.ycol.on i, .ycol:hover i { background: var(--bar-on); }
.ycol.empty { cursor: default; }
.ycol.empty i { background: transparent; border-bottom: 1px dashed var(--line); }
.ylabels { display: flex; gap: 2px; font-size: .68rem; color: var(--muted); overflow: hidden; }
.ylabels span { flex: 1 0 9px; text-align: center; white-space: nowrap; }
.note { margin: 8px 0 0; font-size: .8rem; color: var(--muted); }
.rank { list-style: none; margin: 0; padding: 0; }
.rank li { display: grid; grid-template-columns: minmax(0, 1fr) auto; column-gap: 8px; row-gap: 3px;
  align-items: baseline; padding: 4px 0; cursor: pointer; }
.rank li:hover .nm { color: var(--accent); }
.rank.static li { cursor: default; }
.rank.static li:hover .nm { color: inherit; }
.nm { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank .bar { grid-column: 1 / -1; height: 6px; background: var(--bar); border-radius: 3px; position: static; }
.rank li.on .bar { background: var(--bar-on); }
.rank .n { font-size: .75rem; color: var(--muted); font-variant-numeric: tabular-nums; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { display: inline-flex; align-items: center; gap: 4px; padding: 2px 9px; border-radius: 999px;
  background: var(--chip); font-size: .78rem; color: var(--ink); border: 1px solid transparent; cursor: pointer;
  text-decoration: none; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chip.club { background: var(--accent-soft); }
.chip.ent { background: transparent; border-color: var(--line); }
.chip.active { background: var(--accent); color: #fff; }
.chip small { color: var(--muted); }
.chip.active small { color: inherit; }
.card { border-left: 4px solid var(--accent); }
.card h3 { margin: 0 0 4px; font-size: 1.2rem; }
.meta { color: var(--muted); font-size: .85rem; }
.list { list-style: none; margin: 0; padding: 0; }
.list li { padding: 12px 0; border-top: 1px solid var(--line); }
.list li:first-child { border-top: 0; }
.list a.t { color: var(--ink); font-weight: 600; text-decoration: none; }
.list a.t:hover { color: var(--accent); text-decoration: underline; }
.list .chips { margin-top: 6px; }
.tag { font-size: .72rem; padding: 0 6px; border-radius: 4px; border: 1px solid var(--line); color: var(--muted); }
.pager { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-top: 12px; }
.count { color: var(--muted); }
a { color: var(--accent); }
footer { color: var(--muted); font-size: .85rem; padding-bottom: 32px; }
footer details { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 10px 14px; margin-bottom: 10px; }
footer summary { cursor: pointer; color: var(--ink); font-weight: 600; }
footer p { margin: 8px 0; }
@media (max-width: 820px) {
  .kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .grid2, .search { grid-template-columns: minmax(0, 1fr); }
  .filters { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .bar { position: static; }
}
</style>
</head>
<body>
<header class="top"><div class="wrap">
  <h1>Record <span>no Arquivo.pt</span></h1>
  <p class="sub" id="sub"></p>
  <div class="search">
    <input type="search" id="q" placeholder="Pesquisar no título das notícias…" aria-label="Pesquisar no título">
    <input id="fEnt" list="entList" placeholder="Atleta, clube, treinador, estádio…" aria-label="Entidade">
    <datalist id="entList"></datalist>
  </div>
</div></header>
<div class="bar"><div class="wrap">
  <div class="filters">
    <select id="fAno" aria-label="Ano"></select>
    <select id="fMod" aria-label="Modalidade"></select>
    <select id="fClube" aria-label="Clube"></select>
    <select id="sort" aria-label="Ordenação"><option value="desc">Mais recentes primeiro</option><option value="asc">Mais antigas primeiro</option></select>
  </div>
  <div class="context" id="context"></div>
</div></div>
<main class="wrap">
  <section class="panel card" id="card" hidden style="margin-top:16px"></section>
  <section class="panel" style="margin:16px 0 0">
    <h2>Notícias por ano (clique num ano para filtrar)</h2>
    <div class="years" id="years"></div>
    <div class="ylabels" id="ylabels"></div>
    <p class="note" id="gaps"></p>
  </section>
  <nav class="tabs" role="tablist">
    <button class="tab" id="tabList" role="tab" data-v="">Notícias</button>
    <button class="tab" id="tabStats" role="tab" data-v="estatisticas">Estatísticas</button>
  </nav>
  <section id="viewList">
    <ul class="list" id="list"></ul>
    <div class="pager"><button class="btn" id="prev">← Anteriores</button><span class="count" id="pageInfo"></span><button class="btn" id="next">Seguintes →</button></div>
  </section>
  <section id="viewStats" hidden>
    <div class="kpis" id="kpis"></div>
    <div class="grid2">
      <section class="panel"><h2 id="clubsTitle"></h2><ul class="rank" id="topClubs"></ul></section>
      <section class="panel"><h2 id="athTitle"></h2><ul class="rank" id="topAth"></ul></section>
    </div>
    <div class="grid2">
      <section class="panel" id="otherPanel" hidden><h2 id="otherTitle"></h2><ul class="rank" id="topOther"></ul></section>
      <section class="panel"><h2 id="modsTitle"></h2><ul class="rank" id="mods"></ul></section>
    </div>
  </section>
</main>
<footer class="wrap">
  <details>
    <summary>Sobre os dados</summary>
    <p id="about"></p>
    <div class="grid2" style="margin:10px 0 0">
      <section><h2>Versão do site do Record</h2><ul class="rank" id="eras"></ul></section>
      <section><h2>Texto da notícia</h2><ul class="rank static" id="bodies"></ul></section>
    </div>
  </details>
  <span id="foot"></span>
</footer>
<script src="data.js"></script>
<script>
(function () {
  "use strict";
  const D = window.SDH_DATA;
  const A = D.articles;
  const PAGE = 50;
  const WAYBACK = "https://arquivo.pt/wayback/";
  const T = 0, TI = 1, U = 2, ERA = 3, MOD = 4, MODO = 5, CLU = 6, CLUO = 7, ENT = 8, BODY = 9;
  const fold = s => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const esc = s => String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const fmt = n => n.toLocaleString("pt-PT");
  const titles = A.map(r => fold(r[TI]));
  const clubIdx = new Map(D.clubs.map((c, i) => [c.k, i]));
  const entIdx = new Map(D.entities.map((e, i) => [e.k, i]));
  const entByName = new Map(D.entities.map((e, i) => [fold(e.n), i]));
  const years = [...new Set(A.map(r => r[T].slice(0, 4)))].filter(Boolean).sort();
  const y0 = +years[0], y1 = +years[years.length - 1];
  const allYears = []; for (let y = y0; y <= y1; y++) allYears.push(String(y));
  const yearCount = new Map();
  for (const r of A) { const y = r[T].slice(0, 4); yearCount.set(y, (yearCount.get(y) || 0) + 1); }
  function gapText() {
    const runs = []; let start = null;
    allYears.concat([""]).forEach((y, i, all) => {
      const empty = y && !yearCount.get(y);
      if (empty && start === null) start = y;
      if (!empty && start !== null) { const end = all[i - 1]; runs.push(start === end ? start : start + "–" + end); start = null; }
    });
    return runs.length ? "Sem nenhum artigo na recolha em: " + runs.join(", ") + "." : "";
  }
  const OTHER = new Set(["treinador", "estadio", "competicao"]);
  const CAT = { treinador: "treinador", estadio: "estádio", competicao: "competição", clube: "clube", jogador: "atleta" };
  const ORIGIN = { lista_fechada: "lista fechada da Wikidata", candidato: "detetado no texto e confirmado na Wikidata (abordagem híbrida)",
    "lista_fechada+candidato": "lista fechada da Wikidata, com uma forma nova vinda do texto" };
  const S = { ano: "", era: "", mod: "", clube: "", ent: "", q: "", sort: "desc", p: 0, v: "" };
  const ERA_LABEL = { "1999–2000": "Primeiro site (1999–2000)", "2000–2015 (ASP.NET)": "Site de 2000 a 2015 (ASP.NET)",
    "2015–2024": "Site atual (2015–2024)", outro: "Outras páginas" };
  const eraLabel = e => ERA_LABEL[e] || e;
  function bodyLabel(b) {
    if (b === "c′") return "Texto completo";
    if (b.startsWith("html:")) return "Texto completo (recuperado da página guardada)";
    if (b === "premium") return "Notícia Premium (texto pago, não incluído)";
    return "Sem texto (só título)";
  }

  function readHash() {
    const h = new URLSearchParams(location.hash.slice(1));
    S.ano = h.get("ano") || ""; S.era = h.get("epoca") || ""; S.mod = h.get("modalidade") || "";
    S.clube = h.get("clube") || ""; S.ent = h.get("entidade") || ""; S.q = h.get("q") || "";
    S.sort = h.get("ordem") === "asc" ? "asc" : "desc"; S.p = Math.max(0, (+h.get("p") || 1) - 1);
    S.v = h.get("vista") === "estatisticas" ? "estatisticas" : "";
  }
  function writeHash() {
    const h = new URLSearchParams();
    if (S.ano) h.set("ano", S.ano); if (S.era) h.set("epoca", S.era); if (S.mod) h.set("modalidade", S.mod);
    if (S.clube) h.set("clube", S.clube); if (S.ent) h.set("entidade", S.ent); if (S.q) h.set("q", S.q);
    if (S.sort === "asc") h.set("ordem", "asc"); if (S.p) h.set("p", S.p + 1); if (S.v) h.set("vista", S.v);
    const next = "#" + h.toString();
    if (location.hash !== next) location.hash = next; else render();
  }
  function set(k, v) { S[k] = S[k] === v ? "" : v; S.p = 0; writeHash(); }

  function matcher(skip) {
    const pos = (list, v) => v === "" ? -1 : (list.indexOf(v) >= 0 ? list.indexOf(v) : -2);
    const era = pos(D.eras, S.era), mod = pos(D.modalidades, S.mod);
    const clu = S.clube === "" ? -1 : (clubIdx.has(S.clube) ? clubIdx.get(S.clube) : -2);
    const ent = S.ent === "" ? -1 : (entIdx.has(S.ent) ? entIdx.get(S.ent) : -2);
    const q = fold(S.q.trim());
    return (r, i) =>
      (skip === "ano" || !S.ano || r[T].startsWith(S.ano)) &&
      (skip === "era" || era === -1 || r[ERA] === era) &&
      (skip === "mod" || mod === -1 || r[MOD].includes(mod)) &&
      (skip === "clube" || clu === -1 || r[CLU].includes(clu)) &&
      (skip === "ent" || ent === -1 || r[ENT].includes(ent)) &&
      (!q || titles[i].includes(q));
  }
  function count(rows, get) {
    const c = new Map();
    for (const r of rows) for (const v of get(r)) c.set(v, (c.get(v) || 0) + 1);
    return c;
  }
  function filtered(skip) { const m = matcher(skip); const out = []; for (let i = 0; i < A.length; i++) if (m(A[i], i)) out.push(i); return out; }

  function rank(el, entries, label, isOn, onClick, extra) {
    const max = Math.max(1, ...entries.map(e => e[1]));
    el.innerHTML = entries.length ? entries.map(([k, n], j) =>
      `<li data-j="${j}" class="${isOn(k) ? "on" : ""}" title="${esc(label(k))}: ${fmt(n)}">` +
      `<span class="nm">${esc(label(k))}${extra ? extra(k) : ""}</span><span class="n">${fmt(n)}</span>` +
      `<span class="bar" style="width:${Math.max(2, 100 * n / max)}%"></span></li>`).join("") : `<li class="meta">Sem dados com estes filtros.</li>`;
    el.querySelectorAll("li[data-j]").forEach(li => li.onclick = () => onClick(entries[+li.dataset.j][0]));
  }

  function renderYears() {
    const rows = filtered("ano").map(i => A[i]);
    const c = count(rows, r => [r[T].slice(0, 4)]);
    const max = Math.max(1, ...c.values());
    const box = document.getElementById("years");
    box.innerHTML = allYears.map(y => {
      const n = c.get(y) || 0;
      return `<button class="ycol ${n ? "" : "empty"} ${S.ano === y ? "on" : ""}" data-y="${y}" title="${y}: ${fmt(n)} artigos" ${n ? "" : "disabled"}>` +
        `<i style="height:${n ? Math.max(2, 100 * n / max) : 0}%"></i></button>`;
    }).join("");
    box.querySelectorAll("button[data-y]").forEach(b => b.onclick = () => set("ano", b.dataset.y));
    document.getElementById("ylabels").innerHTML = allYears.map(y =>
      `<span>${(+y % 5 === 0 || y === allYears[0]) ? "'" + y.slice(2) : ""}</span>`).join("");
  }

  function anyFilter() { return !!(S.ano || S.era || S.mod || S.clube || S.ent || S.q); }

  function render() {
    const idx = filtered(null);
    const rows = idx.map(i => A[i]);
    const sel = S.ent && entIdx.has(S.ent) ? entIdx.get(S.ent) : -1;
    document.getElementById("tabList").textContent = `Notícias (${fmt(rows.length)})`;
    document.getElementById("tabList").classList.toggle("on", !S.v);
    document.getElementById("tabStats").classList.toggle("on", !!S.v);
    document.getElementById("viewList").hidden = !!S.v;
    document.getElementById("viewStats").hidden = !S.v;
    renderCard(sel, rows.length);
    renderYears();
    renderFilters(rows);
    renderContext(rows.length);
    if (S.v) renderStats(rows, sel); else renderList(idx);
    renderAbout(rows);
  }

  function renderStats(rows, sel) {
    const withEnt = rows.filter(r => r[ENT].length).length;
    const ys = rows.map(r => r[T].slice(0, 4)).filter(Boolean).sort();
    document.getElementById("kpis").innerHTML = [
      [fmt(rows.length), "notícias"],
      [ys.length ? (ys[0] === ys[ys.length - 1] ? ys[0] : ys[0] + "–" + ys[ys.length - 1]) : "—", "anos"],
      [fmt(new Set(rows.flatMap(r => r[ENT])).size), "atletas, clubes e outras entidades"],
      [rows.length ? Math.round(100 * withEnt / rows.length) + "%" : "—", "das notícias com pelo menos uma"],
    ].map(([b, s]) => `<div class="kpi"><b>${b}</b><span>${s}</span></div>`).join("");
    const ec = count(rows, r => r[ENT]);
    ec.delete(sel);
    const ents = [...ec.entries()].sort((a, b) => b[1] - a[1]);
    const isClub = e => D.entities[e].c === "clube";
    const isOther = e => OTHER.has(D.entities[e].c);
    const where = anyFilter() ? " nestas notícias" : "";
    document.getElementById("clubsTitle").textContent = "Clubes mais mencionados" + where;
    document.getElementById("athTitle").textContent = "Atletas mais mencionados" + where;
    document.getElementById("otherTitle").textContent = "Treinadores, estádios e competições" + where;
    document.getElementById("modsTitle").textContent = "Modalidades" + where;
    const entOn = e => D.entities[e].k === S.ent, entClick = e => set("ent", D.entities[e].k);
    rank(document.getElementById("topClubs"), ents.filter(e => isClub(e[0])).slice(0, 10), e => D.entities[e].n, entOn, entClick);
    rank(document.getElementById("topAth"), ents.filter(e => !isClub(e[0]) && !isOther(e[0])).slice(0, 10), e => D.entities[e].n, entOn, entClick,
      e => D.entities[e].m ? ` <small class="meta">${esc(D.entities[e].m)}</small>` : "");
    rank(document.getElementById("topOther"), ents.filter(e => isOther(e[0])).slice(0, 10), e => D.entities[e].n, entOn, entClick,
      e => ` <small class="meta">${esc(CAT[D.entities[e].c] || D.entities[e].c)}</small>`);
    const mc = count(filtered("mod").map(i => A[i]), r => r[MOD]);
    rank(document.getElementById("mods"), [...mc.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10),
      m => D.modalidades[m], m => D.modalidades[m] === S.mod, m => set("mod", D.modalidades[m]));
  }

  function renderAbout(rows) {
    const erc = count(filtered("era").map(i => A[i]), r => [r[ERA]]);
    rank(document.getElementById("eras"), [...erc.entries()].sort((a, b) => a[0] - b[0]),
      e => eraLabel(D.eras[e]), e => D.eras[e] === S.era, e => set("era", D.eras[e]));
    const bc = new Map();
    for (const r of rows) { const l = bodyLabel(D.bodies[r[BODY]]); bc.set(l, (bc.get(l) || 0) + 1); }
    rank(document.getElementById("bodies"), [...bc.entries()].sort((a, b) => b[1] - a[1]), l => l, () => false, () => {});
  }

  function renderCard(sel, n) {
    const card = document.getElementById("card");
    if (sel < 0) { card.hidden = true; return; }
    const e = D.entities[sel];
    card.hidden = false;
    card.innerHTML = `<h3>${esc(e.n)}</h3><div class="meta">${esc(CAT[e.c] || e.c)}${e.m ? " · " + esc(e.m) : ""} · ` +
      `${fmt(n)} notícias · ` +
      (e.q ? `<a href="https://www.wikidata.org/wiki/${esc(e.q)}" target="_blank" rel="noopener">ver na Wikidata (${esc(e.q)})</a>`
           : "nome partilhado por várias pessoas: sem ligação à Wikidata") +
      (e.o ? `<br>Como foi identificado: ${esc(ORIGIN[e.o] || e.o)}.` : "") + `</div>`;
  }

  function options(el, entries, current, all) {
    el.innerHTML = `<option value="">${all}</option>` + entries.map(([v, label]) =>
      `<option value="${esc(v)}" ${v === current ? "selected" : ""}>${esc(label)}</option>`).join("");
  }
  function renderFilters(rows) {
    const yc = count(filtered("ano").map(i => A[i]), r => [r[T].slice(0, 4)]);
    options(document.getElementById("fAno"), allYears.slice().reverse().filter(y => yc.get(y) || y === S.ano)
      .map(y => [y, `${y} (${fmt(yc.get(y) || 0)})`]), S.ano, "Todos os anos");
    const mc = count(filtered("mod").map(i => A[i]), r => r[MOD]);
    const mods = [...mc.entries()].sort((a, b) => b[1] - a[1]).map(([m, n]) => [D.modalidades[m], `${D.modalidades[m]} (${fmt(n)})`]);
    if (S.mod && !mods.some(m => m[0] === S.mod)) mods.unshift([S.mod, S.mod]);
    options(document.getElementById("fMod"), mods, S.mod, "Todas as modalidades");
    const cc = count(filtered("clube").map(i => A[i]), r => r[CLU]);
    const clubs = [...cc.entries()].sort((a, b) => b[1] - a[1]).map(([c, n]) => [D.clubs[c].k, `${D.clubs[c].n} (${fmt(n)})`]);
    if (S.clube && !clubs.some(c => c[0] === S.clube)) clubs.unshift([S.clube, S.clube]);
    options(document.getElementById("fClube"), clubs, S.clube, "Todos os clubes");
    const fEnt = document.getElementById("fEnt");
    if (document.activeElement !== fEnt) fEnt.value = S.ent && entIdx.has(S.ent) ? D.entities[entIdx.get(S.ent)].n : "";
    const q = document.getElementById("q");
    if (document.activeElement !== q) q.value = S.q;
    document.getElementById("sort").value = S.sort;
  }

  function renderContext(n) {
    const act = [];
    if (S.q) act.push(["q", "título com “" + S.q + "”"]);
    if (S.ent) act.push(["ent", entIdx.has(S.ent) ? D.entities[entIdx.get(S.ent)].n : S.ent]);
    if (S.clube) act.push(["clube", clubIdx.has(S.clube) ? D.clubs[clubIdx.get(S.clube)].n : S.clube]);
    if (S.mod) act.push(["mod", S.mod]);
    if (S.ano) act.push(["ano", S.ano]);
    if (S.era) act.push(["era", eraLabel(S.era)]);
    const box = document.getElementById("context");
    box.classList.toggle("none", !act.length);
    box.innerHTML = act.length
      ? `A mostrar <b>${fmt(n)}</b> notícias de: ` +
        act.map(([k, l]) => `<button class="chip active" data-k="${k}" title="Retirar">${esc(l)} ×</button>`).join("") +
        `<button class="chip" data-k="*">Limpar tudo</button>`
      : `A mostrar todas as <b>${fmt(n)}</b> notícias. Pesquise ou escolha um ano, uma modalidade ou um clube.`;
    box.querySelectorAll("button").forEach(b => b.onclick = () => {
      if (b.dataset.k === "*") Object.assign(S, { ano: "", era: "", mod: "", clube: "", ent: "", q: "", p: 0 });
      else { S[b.dataset.k] = ""; S.p = 0; }
      writeHash();
    });
  }

  function dateOf(t) { return t.length >= 8 ? `${t.slice(6, 8)}/${t.slice(4, 6)}/${t.slice(0, 4)}` : "—"; }
  function renderList(idx) {
    const order = S.sort === "asc" ? idx : idx.slice().reverse();
    const pages = Math.max(1, Math.ceil(order.length / PAGE));
    if (S.p >= pages) S.p = pages - 1;
    const slice = order.slice(S.p * PAGE, S.p * PAGE + PAGE);
    document.getElementById("pageInfo").textContent = `página ${S.p + 1} de ${fmt(pages)}`;
    document.getElementById("prev").disabled = S.p === 0;
    document.getElementById("next").disabled = S.p >= pages - 1;
    const list = document.getElementById("list");
    list.innerHTML = slice.map(i => {
      const r = A[i];
      const mods = r[MOD].map(m => `<button class="chip" data-mod="${esc(D.modalidades[m])}">${esc(D.modalidades[m])}${r[MODO] === 2 ? " <small>· provável</small>" : ""}</button>`);
      const clubs = r[CLU].map(c => `<button class="chip club" data-clube="${esc(D.clubs[c].k)}">${esc(D.clubs[c].n)}${r[CLUO] === 2 ? " <small>· no texto</small>" : ""}</button>`);
      const shownClubs = new Set(r[CLU].map(c => D.clubs[c].k));
      const ents = r[ENT].filter(e => !shownClubs.has(D.entities[e].k)).map(e => `<button class="chip ent ${D.entities[e].k === S.ent ? "active" : ""}" data-ent="${esc(D.entities[e].k)}">${esc(D.entities[e].n)}</button>`);
      const body = D.bodies[r[BODY]];
      const tag = body === "premium" ? ` <span class="tag">Premium</span>` : (body === "c′" || body.startsWith("html:") ? "" : ` <span class="tag">só título</span>`);
      return `<li><div class="meta">${dateOf(r[T])}${tag}</div>` +
        `<a class="t" href="${esc(WAYBACK + r[T] + "/" + r[U])}" target="_blank" rel="noopener">${esc(r[TI])}</a>` +
        `<div class="chips">${mods.join("")}${clubs.join("")}${ents.join("")}</div></li>`;
    }).join("") || `<li class="meta">Nenhum artigo com estes filtros.</li>`;
    list.querySelectorAll("button[data-mod]").forEach(b => b.onclick = () => set("mod", b.dataset.mod));
    list.querySelectorAll("button[data-clube]").forEach(b => b.onclick = () => set("clube", b.dataset.clube));
    list.querySelectorAll("button[data-ent]").forEach(b => b.onclick = () => set("ent", b.dataset.ent));
  }

  document.getElementById("sub").textContent =
    `${fmt(A.length)} notícias do jornal Record guardadas no Arquivo.pt, de ${y0} a ${y1}.`;
  document.getElementById("about").textContent =
    "Cada notícia aparece uma vez, com a data da cópia mais antiga guardada no Arquivo.pt. " +
    "A modalidade e o clube vêm do endereço da notícia; quando o endereço não os tem, vêm do texto " +
    "(assinalado com «no texto» ou «provável»). Atletas, clubes, treinadores, estádios e competições " +
    "foram reconhecidos no texto e ligados à Wikidata. " + gapText();
  document.getElementById("foot").textContent =
    "Semantic Driven Harvester · cada vista é um endereço: copie-o para a guardar ou partilhar.";
  document.getElementById("gaps").textContent = gapText();
  document.getElementById("otherPanel").hidden = !D.entities.some(e => OTHER.has(e.c));
  document.getElementById("entList").innerHTML = D.entities.map(e => `<option value="${esc(e.n)}"></option>`).join("");
  let timer;
  document.getElementById("q").oninput = ev => { clearTimeout(timer); timer = setTimeout(() => { S.q = ev.target.value; S.p = 0; writeHash(); }, 250); };
  document.getElementById("fAno").onchange = ev => { S.ano = ev.target.value; S.p = 0; writeHash(); };
  document.querySelectorAll(".tab").forEach(t => t.onclick = () => { S.v = t.dataset.v; writeHash(); });
  document.getElementById("fMod").onchange = ev => { S.mod = ev.target.value; S.p = 0; writeHash(); };
  document.getElementById("fClube").onchange = ev => { S.clube = ev.target.value; S.p = 0; writeHash(); };
  document.getElementById("fEnt").onchange = ev => {
    const i = entByName.get(fold(ev.target.value.trim()));
    S.ent = i === undefined ? "" : D.entities[i].k; S.p = 0; writeHash();
  };
  document.getElementById("sort").onchange = ev => { S.sort = ev.target.value; S.p = 0; writeHash(); };
  document.getElementById("prev").onclick = () => { S.p--; writeHash(); window.scrollTo(0, document.getElementById("list").offsetTop - 120); };
  document.getElementById("next").onclick = () => { S.p++; writeHash(); window.scrollTo(0, document.getElementById("list").offsetTop - 120); };
  window.addEventListener("hashchange", () => { readHash(); render(); });
  readHash();
  render();
})();
</script>
</body>
</html>
"""
