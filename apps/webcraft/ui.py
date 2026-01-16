# -*- coding: utf-8 -*-
from __future__ import annotations

from html import escape

# NOTE:
# - Keep HTML/JS as a normal triple-quoted string.
# - Do NOT use Python f-strings here: the template contains many `{}` (CSS/JS/template literals).

_INDEX_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="app-root" content="__WAGSTAFF_APP_ROOT__" />
  <title>Wagstaff WebCraft</title>
  <style>
    :root {
      --bg: #0b0f14;
      --panel: #0f1722;
      --panel2: #111b29;
      --text: #e6edf3;
      --muted: #9fb0c0;
      --border: #233042;
      --accent: #79c0ff;
      --accent2: #a5d6ff;
      --bad: #ff7b72;
      --ok: #7ee787;
    }
    html, body {
      margin: 0; padding: 0;
      background: var(--bg);
      color: var(--text);
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
    }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }

    .nav {
      font-size: 12px;
      color: var(--muted);
      padding: 4px 10px;
      border: 1px solid var(--border);
      border-radius: 999px;
      background: rgba(17,27,41,0.6);
    }
    .nav:hover {
      text-decoration: none;
      border-color: #3b4b63;
      color: var(--text);
    }
    .nav.active {
      color: var(--text);
      border-color: rgba(121, 192, 255, 0.45);
      background: rgba(121, 192, 255, 0.10);
    }

    .topbar {
      position: sticky;
      top: 0;
      z-index: 10;
      display: flex;
      gap: 12px;
      align-items: center;
      padding: 10px 12px;
      border-bottom: 1px solid var(--border);
      background: rgba(11, 15, 20, 0.92);
      backdrop-filter: blur(8px);
    }
    .topbar h1 {
      font-size: 14px;
      margin: 0;
      font-weight: 650;
      letter-spacing: .3px;
      color: var(--accent2);
    }
    .search {
      flex: 1;
      display: flex;
      gap: 8px;
      align-items: center;
    }
    input[type="text"], textarea {
      width: 100%;
      background: var(--panel);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 10px;
      outline: none;
    }
    textarea {
      min-height: 60px;
      resize: vertical;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    }
    select {
      background: var(--panel2);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 6px 8px;
      font-size: 12px;
      outline: none;
    }
    button {
      background: var(--panel2);
      border: 1px solid var(--border);
      color: var(--text);
      border-radius: 8px;
      padding: 8px 10px;
      cursor: pointer;
    }
    button:hover { border-color: #3b4b63; }
    button.primary {
      background: rgba(121, 192, 255, 0.12);
      border-color: rgba(121, 192, 255, 0.25);
    }
    button.primary:hover {
      border-color: rgba(121, 192, 255, 0.45);
    }
    .layout {
      display: grid;
      grid-template-columns: 260px 1fr 420px;
      gap: 10px;
      padding: 10px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 10px;
      overflow: hidden;
      min-height: calc(100vh - 62px);
    }
    .panel h2 {
      margin: 0;
      padding: 10px 12px;
      font-size: 13px;
      border-bottom: 1px solid var(--border);
      color: var(--muted);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .list {
      max-height: calc(100vh - 62px - 44px);
      overflow: auto;
    }
    .item {
      padding: 8px 12px;
      border-bottom: 1px solid rgba(35, 48, 66, 0.65);
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      gap: 10px;
    }
    .item:hover { background: rgba(255,255,255,0.03); }
    .item.active { background: rgba(121,192,255,0.08); }
    .item .name { font-weight: 560; }
    .item .meta { color: var(--muted); font-size: 12px; }
    .detail {
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .kv {
      display: grid;
      grid-template-columns: 120px 1fr;
      gap: 6px 10px;
      font-size: 13px;
    }
    .kv .k { color: var(--muted); }
    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .chip {
      font-size: 12px;
      color: var(--muted);
      padding: 3px 8px;
      border: 1px solid rgba(35,48,66,0.9);
      border-radius: 999px;
      background: rgba(17,27,41,0.8);
    }
    .grid2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .err {
      color: var(--bad);
      font-size: 12px;
      white-space: pre-wrap;
    }
    .ok {
      color: var(--ok);
      font-size: 12px;
    }
    .muted { color: var(--muted); }
    .small { font-size: 12px; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
    .itemRef {
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .itemIcon {
      width: 18px;
      height: 18px;
      border-radius: 4px;
      border: 1px solid rgba(35,48,66,0.9);
      background: rgba(17,27,41,0.8);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      flex: 0 0 auto;
    }
    .itemIconImg {
      width: 100%;
      height: 100%;
      object-fit: contain;
      image-rendering: pixelated;
      display: block;
    }
    .itemIconFallback {
      width: 100%;
      height: 100%;
      display: none;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      color: var(--muted);
    }
    .itemLabel {
      color: var(--text);
    }
  </style>
</head>
<body>
  <div class="topbar">
    <h1>Wagstaff WebCraft</h1>
    <a id="navCraft" class="nav active" href="#">Craft</a>
    <a id="navCooking" class="nav" href="#">Cooking</a>
    <a id="navCatalog" class="nav" href="#">Catalog</a>
    <div class="small" style="display:flex; align-items:center; gap:6px;">
      <span class="muted" id="labelModeLabel">Label</span>
      <select id="labelMode">
        <option value="en">EN</option>
        <option value="zh">中文</option>
        <option value="id">ID</option>
      </select>
    </div>
    <div class="search">
      <input id="q" type="text" placeholder="Search: axe | ing:twigs | tag:bookbuilder | filter:TOOLS | tab:LIGHT" />
      <button id="btnSearch" class="primary">Search</button>
    </div>
    <div class="small muted" id="meta"></div>
  </div>

  <div class="layout">
    <div class="panel">
      <h2>
        <span id="groupTitle">Filters</span>
        <button id="btnToggle">Toggle</button>
      </h2>
      <div class="list" id="groupList"></div>
    </div>

    <div class="panel">
      <h2>
        <span id="listTitle">Recipes</span>
        <span class="small muted" id="listCount"></span>
      </h2>
      <div class="list" id="recipeList"></div>
    </div>

    <div class="panel">
      <h2 id="detailTitle">Details</h2>
      <div class="detail">
        <div id="detail"></div>

        <div>
          <div class="small muted" id="inventoryHelp">Inventory (for missing/planning)</div>
          <textarea id="inv" placeholder="twigs=2, flint=1
rocks=10"></textarea>
          <div class="grid2" style="margin-top:8px;">
            <div>
              <div class="small muted" id="builderTagLabel">builder_tag (optional)</div>
              <input id="builderTag" type="text" placeholder="bookbuilder / handyperson / ..." />
            </div>
            <div style="display:flex; gap:8px; align-items:flex-end;">
              <button id="btnPlan" class="primary" style="flex:1;">Plan</button>
              <button id="btnMissing" style="flex:1;">Missing</button>
            </div>
          </div>
          <div id="planOut" class="small" style="margin-top:8px;"></div>
        </div>

        <div class="err" id="err"></div>
      </div>
    </div>
  </div>

  <script>
    const APP_ROOT = (document.querySelector('meta[name="app-root"]')?.content || '').replace(/\/+$/,'');
    const api = (path) => APP_ROOT + path;

    const navCraft = document.getElementById('navCraft');
    if (navCraft) navCraft.href = APP_ROOT + '/';

    const navCooking = document.getElementById('navCooking');
    if (navCooking) navCooking.href = APP_ROOT + '/cooking';

    const navCatalog = document.getElementById('navCatalog');
    if (navCatalog) navCatalog.href = APP_ROOT + '/catalog';

    const el = (id) => document.getElementById(id);
    const state = {
      mode: 'filters', // filters | tabs | tags
      groups: [],
      activeGroup: null,
      recipes: [],
      activeRecipe: null,
      activeRecipeData: null,
      assets: {},
      icon: null, // {mode, static_base, api_base}

      // label mode: en | zh | id (persisted in localStorage)
      labelMode: localStorage.getItem('ws_label_mode') || 'en',
      i18n: null,         // meta from /api/v1/meta (set in loadMeta)
      i18nNames: {},      // {lang: {id: name}}
      i18nLoaded: {},     // {lang: true}
      uiStrings: {},      // {lang: {key: text}}
      uiLoaded: {},       // {lang: true}
    };

    function setError(msg) {
      el('err').textContent = msg || '';
    }

    function parseInventory(text) {
      const out = {};
      const raw = (text || '').trim();
      if (!raw) return out;

      const parts = raw
        .split(/[,\n]/g)
        .map(s => s.trim())
        .filter(Boolean);

      for (const p of parts) {
        const m = p.match(/^([^=\s]+)\s*(?:=|\s)\s*([0-9]+(?:\.[0-9]+)?)$/);
        if (!m) continue;
        const k = m[1].trim();
        const v = parseFloat(m[2]);
        if (!k || !Number.isFinite(v) || v <= 0) continue;
        out[k] = v;
      }
      return out;
    }

    async function fetchJson(url, opts) {
      const r = await fetch(url, opts || {});
      if (!r.ok) {
        const t = await r.text();
        throw new Error(`HTTP ${r.status} ${r.statusText}\n${t}`);
      }
      return await r.json();
    }

    function escHtml(s) {
      return String(s ?? '').replace(/[&<>"']/g, (c) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      }[c]));
    }

    async function loadAssets() {
      try {
        const res = await fetchJson(api('/api/v1/assets'));
        state.assets = res.assets || {};
        state.icon = res.icon || null;
      } catch (e) {
        state.assets = {};
        state.icon = null;
      }
    }

    function _iconUrls(iid) {
      const cfg = state.icon || {};
      const mode = String(cfg.mode || 'off');
      const enc = encodeURIComponent(iid);
      const staticBaseRaw = String(cfg.static_base || '/static/icons');
      const staticBase = (APP_ROOT && staticBaseRaw.startsWith('/') && !staticBaseRaw.startsWith(APP_ROOT + '/'))
        ? (APP_ROOT + staticBaseRaw)
        : staticBaseRaw;
      const apiBase = String(cfg.api_base || '/api/v1/icon');
      const staticUrl = api(`${staticBase}/${enc}.png`);
      const apiUrl = api(`${apiBase}/${enc}.png`);

      if (mode === 'dynamic') return { src: apiUrl, fallback: '' };
      if (mode === 'static') return { src: staticUrl, fallback: apiUrl };
      if (mode === 'auto') return { src: staticUrl, fallback: apiUrl };
      return { src: '', fallback: '' };
    }

    function iconError(img) {
      try {
        const fb = img?.dataset?.fallback || '';
        const tried = img?.dataset?.fallbackTried || '';
        if (fb && !tried) {
          img.dataset.fallbackTried = '1';
          img.src = fb;
          return;
        }
        img.style.display = 'none';
        const nxt = img.nextElementSibling;
        if (nxt) nxt.style.display = 'flex';
      } catch (e) {
        // ignore
      }
    }

    function _altId(iid) {
      if (!iid) return '';
      const s = String(iid);
      if (s.includes('_')) return s.replace(/_/g,'');
      return '';
    }

    function getI18nName(iid) {
      const mp = (state.i18nNames && state.i18nNames.zh) ? state.i18nNames.zh : null;
      if (!mp) return '';
      const k = String(iid || '').trim();
      if (!k) return '';
      const lo = k.toLowerCase();
      const a1 = _altId(k);
      const a2 = _altId(lo);
      return mp[k] || mp[lo] || (a1 ? mp[a1] : '') || (a2 ? mp[a2] : '') || '';
    }

    async function ensureI18nNames(mode) {
      if (String(mode || '') !== 'zh') return;
      if (state.i18nLoaded && state.i18nLoaded.zh) return;
      const enabled = Boolean(state.i18n && state.i18n.enabled);
      if (!enabled) return;
      try {
        const res = await fetchJson(api('/api/v1/i18n/names/zh'));
        state.i18nNames.zh = res.names || {};
        state.i18nLoaded.zh = true;
      } catch (e) {
        state.i18nLoaded.zh = false;
      }
    }

    function uiLang() {
      return (state.labelMode === 'zh') ? 'zh' : 'en';
    }

    async function ensureUiStrings(lang) {
      const l = String(lang || '').trim();
      if (!l) return;
      if (state.uiLoaded && state.uiLoaded[l]) return;
      try {
        const res = await fetchJson(api(`/api/v1/i18n/ui/${encodeURIComponent(l)}`));
        state.uiStrings[l] = res.strings || {};
        state.uiLoaded[l] = true;
      } catch (e) {
        state.uiStrings[l] = {};
        state.uiLoaded[l] = false;
      }
    }

    function t(key, fallback) {
      const l = uiLang();
      const mp = (state.uiStrings && state.uiStrings[l]) ? state.uiStrings[l] : {};
      return (mp && mp[key]) ? mp[key] : (fallback || key || '');
    }

    function applyUiStrings() {
      const navCraft = el('navCraft');
      if (navCraft) navCraft.textContent = t('nav.craft', 'Craft');
      const navCooking = el('navCooking');
      if (navCooking) navCooking.textContent = t('nav.cooking', 'Cooking');
      const navCatalog = el('navCatalog');
      if (navCatalog) navCatalog.textContent = t('nav.catalog', 'Catalog');
      const label = el('labelModeLabel');
      if (label) label.textContent = t('label.mode', 'Label');
      const btnSearch = el('btnSearch');
      if (btnSearch) btnSearch.textContent = t('btn.search', 'Search');
      const btnPlan = el('btnPlan');
      if (btnPlan) btnPlan.textContent = t('btn.plan', 'Plan');
      const btnMissing = el('btnMissing');
      if (btnMissing) btnMissing.textContent = t('btn.missing', 'Missing');
      const btnToggle = el('btnToggle');
      if (btnToggle) btnToggle.textContent = t('btn.toggle', 'Toggle');
      const listTitle = el('listTitle');
      if (listTitle) {
        const txt = listTitle.textContent || '';
        if (!txt.includes(':') && !txt.includes('(')) {
          listTitle.textContent = t('craft.list.recipes', txt || 'Recipes');
        }
      }
      const groupTitle = el('groupTitle');
      if (groupTitle) {
        if (state.mode === 'filters') groupTitle.textContent = t('craft.group.filters', 'Filters');
        else if (state.mode === 'tabs') groupTitle.textContent = t('craft.group.tabs', 'Tabs');
        else groupTitle.textContent = t('craft.group.tags', 'Tags');
      }
      const detailTitle = el('detailTitle');
      if (detailTitle) detailTitle.textContent = t('craft.detail.title', 'Details');
      const invHelp = el('inventoryHelp');
      if (invHelp) invHelp.textContent = t('craft.inventory.help', 'Inventory (for missing/planning)');
      const builderLabel = el('builderTagLabel');
      if (builderLabel) builderLabel.textContent = t('craft.builder_tag.label', 'builder_tag (optional)');
      const input = el('q');
      if (input) input.placeholder = t('craft.search.placeholder', input.placeholder || '');
      const inv = el('inv');
      if (inv) inv.placeholder = t('craft.inventory.placeholder', inv.placeholder || '');
      const builderTag = el('builderTag');
      if (builderTag) builderTag.placeholder = t('craft.builder_tag.placeholder', builderTag.placeholder || '');
    }

    async function fetchTuningTrace(prefix) {
      if (!state.tuningTraceEnabled) return {};
      const pfx = String(prefix || '').trim();
      if (!pfx) return {};
      const res = await fetchJson(api(`/api/v1/tuning/trace?prefix=${encodeURIComponent(pfx)}`));
      const traces = res.traces || {};
      for (const k in traces) {
        if (!Object.prototype.hasOwnProperty.call(traces, k)) continue;
        state.tuningTrace[k] = traces[k];
      }
      return traces;
    }

    function applyLabelModeUI() {
      const sel = el('labelMode');
      if (!sel) return;
      const enabled = Boolean(state.i18n && state.i18n.enabled);
      const optZh = sel.querySelector('option[value="zh"]');
      if (optZh) optZh.disabled = !enabled;
      if (!enabled && state.labelMode === 'zh') {
        state.labelMode = 'en';
        try { localStorage.setItem('ws_label_mode', state.labelMode); } catch (e) {}
      }
      sel.value = state.labelMode || 'en';
    }

    function resolveLabel(iid, enName, zhName) {
      const mode = String(state.labelMode || 'en');
      if (mode === 'id') return iid;
      if (mode === 'zh' && zhName) return zhName;
      return enName || iid;
    }

    async function setLabelMode(mode) {
      state.labelMode = String(mode || 'en');
      try { localStorage.setItem('ws_label_mode', state.labelMode); } catch (e) {}
      applyLabelModeUI();
      await ensureI18nNames(state.labelMode);
      await ensureUiStrings(uiLang());
      applyUiStrings();
      renderRecipeList();
      renderRecipeDetail(state.activeRecipeData);
    }

    function renderItem(id) {
      const iid = String(id || '').trim();
      if (!iid) return '';
      const m = (state.assets && state.assets[iid]) ? state.assets[iid] : null;
      const enName = (m && m.name) ? m.name : iid;
      const zhName = getI18nName(iid);
      const name = resolveLabel(iid, enName, zhName);

      const tipParts = [`id:${iid}`];
      if (enName && enName !== iid) tipParts.push(`en:${enName}`);
      if (zhName && zhName !== enName && zhName !== iid) tipParts.push(`zh:${zhName}`);
      if (m && m.image) tipParts.push(`img:${m.image}`);
      if (m && m.atlas) tipParts.push(`atlas:${m.atlas}`);
      const tip = escHtml(tipParts.join(' | '));

      const { src, fallback } = _iconUrls(iid);
      const iconChar = (m && (m.image || m.atlas)) ? '🖼️' : '📦';

      if (!src) {
        return `<span class="itemRef" title="${tip}">` +
          `<span class="itemIcon"><span class="itemIconFallback" style="display:flex;">${iconChar}</span></span>` +
          `<span class="itemLabel">${escHtml(name)}</span></span>`;
      }

      const fbAttr = fallback ? ` data-fallback="${escHtml(fallback)}"` : '';
      return `<span class="itemRef" title="${tip}">` +
        `<span class="itemIcon">` +
          `<img class="itemIconImg" src="${escHtml(src)}"${fbAttr} onerror="iconError(this)" alt="" />` +
          `<span class="itemIconFallback">${iconChar}</span>` +
        `</span>` +
        `<span class="itemLabel">${escHtml(name)}</span>` +
      `</span>`;
    }


    function renderGroupList() {
      const box = el('groupList');
      box.innerHTML = '';
      for (const g of state.groups) {
        const div = document.createElement('div');
        div.className = 'item' + (state.activeGroup === g.name ? ' active' : '');
        div.innerHTML = `<span class="name">${g.name}</span><span class="meta">${g.count ?? ''}</span>`;
        div.onclick = () => selectGroup(g.name);
        box.appendChild(div);
      }
    }

    function renderRecipeList() {
      const box = el('recipeList');
      box.innerHTML = '';
      el('listCount').textContent = state.recipes.length ? `${state.recipes.length}` : '';
      for (const nm of state.recipes) {
        const div = document.createElement('div');
        div.className = 'item' + (state.activeRecipe === nm ? ' active' : '');
        div.innerHTML = `<span class="name">${renderItem(nm)}</span><span class="meta"></span>`;
        div.onclick = () => selectRecipe(nm);
        box.appendChild(div);
      }
    }

    function renderRecipeDetail(rec) {
      if (!rec) {
        el('detail').innerHTML = `<div class="muted">${escHtml(t('craft.detail.empty', 'Select a recipe.'))}</div>`;
        return;
      }
      const filters = (rec.filters || []).map(x => `<span class="chip">${x}</span>`).join('');
      const tags = (rec.builder_tags || []).map(x => `<span class="chip">${x}</span>`).join('');
      const ings = (rec.ingredients || []).map(i => {
        const item = i.item;
        const amt = i.amount ?? '';
        const num = i.amount_num;
        const extra = (num === null || num === undefined) ? ' <span class="muted">(?)</span>' : '';
        return `<div>• ${renderItem(item)} <span class="mono">x${escHtml(amt)}</span>${extra}</div>`;
      }).join('');

      el('detail').innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:baseline; gap:10px;">
          <div style="font-size:16px; font-weight:650;">${renderItem(rec.name)}</div>
          <div class="small muted">${String(rec.tab || '').replace('RECIPETABS.','')}</div>
        </div>
        <div class="kv">
          <div class="k">${escHtml(t('craft.detail.product', 'Product'))}</div><div>${rec.product ? renderItem(rec.product) : ''}</div>
          <div class="k">${escHtml(t('craft.detail.tech', 'Tech'))}</div><div class="mono">${String(rec.tech || '').replace('TECH.','')}</div>
          <div class="k">${escHtml(t('craft.detail.station', 'Station'))}</div><div class="mono">${rec.station_tag || ''}</div>
          <div class="k">${escHtml(t('craft.detail.builder_skill', 'Builder skill'))}</div><div class="mono">${rec.builder_skill || ''}</div>
        </div>
        <div>
          <div class="small muted">${escHtml(t('craft.detail.filters', 'Filters'))}</div>
          <div class="chips">${filters || '<span class="muted">-</span>'}</div>
        </div>
        <div>
          <div class="small muted">${escHtml(t('craft.detail.builder_tags', 'Builder tags'))}</div>
          <div class="chips">${tags || '<span class="muted">-</span>'}</div>
        </div>
        <div>
          <div class="small muted">${escHtml(t('craft.detail.ingredients', 'Ingredients'))}</div>
          ${ings || '<div class="muted">-</div>'}
          ${(rec.ingredients_unresolved && rec.ingredients_unresolved.length)
            ? `<div class="muted small">${escHtml(t('craft.detail.unresolved', 'Unresolved'))}: ${rec.ingredients_unresolved.join(', ')}</div>`
            : ''}
        </div>
      `;
    }

    async function loadMeta() {
      const m = await fetchJson(api('/api/v1/meta'));
      state.i18n = (m && m.i18n) ? m.i18n : { enabled: false };
      state.tuningTraceEnabled = Boolean(m && m.tuning_trace_enabled);
      applyLabelModeUI();
      await ensureUiStrings(uiLang());
      applyUiStrings();
      const sha = m.scripts_sha256_12 ? `sha:${m.scripts_sha256_12}` : '';
      const ae = m.analyzer_enabled ? 'analyzer:on' : 'analyzer:off';
      const te = m.tuning_enabled ? 'tuning:on' : 'tuning:off';
      el('meta').textContent = `${sha} | mode:${m.engine_mode || ''} | files:${m.scripts_file_count || ''} | ${ae} | ${te}`;
    }

    async function loadGroups() {
      setError('');
      if (state.mode === 'filters') {
        el('groupTitle').textContent = t('craft.group.filters', 'Filters');
        const res = await fetchJson(api('/api/v1/craft/filters'));
        const order = res.order || [];
        state.groups = order.map(n => ({ name: n, count: '' }));
      } else if (state.mode === 'tabs') {
        el('groupTitle').textContent = t('craft.group.tabs', 'Tabs');
        const res = await fetchJson(api('/api/v1/craft/tabs'));
        state.groups = (res.tabs || []).map(t => ({ name: t.name, count: t.count }));
      } else {
        el('groupTitle').textContent = t('craft.group.tags', 'Tags');
        const res = await fetchJson(api('/api/v1/craft/tags'));
        state.groups = (res.tags || []).map(t => ({ name: t.name, count: t.count }));
      }

      state.activeGroup = null;
      state.recipes = [];
      state.activeRecipe = null;
      state.activeRecipeData = null;
      renderGroupList();
      renderRecipeList();
      renderRecipeDetail(null);
    }

    async function selectGroup(name) {
      setError('');
      state.activeGroup = name;
      renderGroupList();

      let url = '';
      if (state.mode === 'filters') url = api(`/api/v1/craft/filters/${encodeURIComponent(name)}/recipes`);
      else if (state.mode === 'tabs') url = api(`/api/v1/craft/tabs/${encodeURIComponent(name)}/recipes`);
      else url = api(`/api/v1/craft/tags/${encodeURIComponent(name)}/recipes`);

      const res = await fetchJson(url);
      state.recipes = (res.recipes || []);
      state.activeRecipe = null;
      state.activeRecipeData = null;

      el('listTitle').textContent = t('craft.list.recipes', 'Recipes');
      renderRecipeList();
      renderRecipeDetail(null);
    }

    async function selectRecipe(name) {
      setError('');
      state.activeRecipe = name;
      renderRecipeList();
      const res = await fetchJson(api(`/api/v1/craft/recipes/${encodeURIComponent(name)}`));
      state.activeRecipeData = res.recipe || null;
      renderRecipeDetail(state.activeRecipeData);
    }

    async function doSearch() {
      setError('');
      const q = el('q').value.trim();
      if (!q) return;
      const res = await fetchJson(api(`/api/v1/craft/recipes/search?q=${encodeURIComponent(q)}&limit=200`));
      const results = (res.results || []).map(r => r.name).filter(Boolean);
      state.recipes = results;
      state.activeGroup = null;
      state.activeRecipe = null;
      state.activeRecipeData = null;
      renderGroupList();
      renderRecipeList();
      renderRecipeDetail(null);
      el('listTitle').textContent = `${t('label.search', 'Search')}: ${q}`;
    }

    async function doPlan() {
      setError('');
      const inv = parseInventory(el('inv').value);
      const builderTag = el('builderTag').value.trim() || null;
      const payload = { inventory: inv, builder_tag: builderTag, strict: false, limit: 200 };
      const res = await fetchJson(api('/api/v1/craft/plan'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const craftable = res.craftable || [];
      el('planOut').innerHTML = craftable.length
        ? `<div class="ok">${escHtml(t('craft.plan.craftable', 'Craftable'))} (${craftable.length})</div><div>${craftable.slice(0,120).map(n => renderItem(n)).join(', ')}</div>`
        : `<div class="muted">${escHtml(t('craft.plan.none', 'No craftable recipes with current inventory.'))}</div>`;
    }

    async function doMissing() {
      setError('');
      const nm = state.activeRecipe;
      if (!nm) {
        setError(t('craft.error.select_recipe', 'Select a recipe first.'));
        return;
      }
      const inv = parseInventory(el('inv').value);
      const res = await fetchJson(api('/api/v1/craft/missing'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: nm, inventory: inv }),
      });
      const miss = res.missing || [];
      if (!miss.length) {
        el('planOut').innerHTML = `<div class="ok">${escHtml(t('craft.missing.none', 'No missing materials.'))}</div>`;
        return;
      }
      const needLabel = t('label.need', 'need');
      const haveLabel = t('label.have', 'have');
      const reasonLabel = t('label.reason', 'reason');
      const lines = miss.map(m => `• ${renderItem(m.item)} ${escHtml(needLabel)}:${escHtml(m.need)} ${escHtml(haveLabel)}:${escHtml(m.have)} (${escHtml(reasonLabel)}:${escHtml(m.reason)})`).join('<br/>');
      el('planOut').innerHTML = `<div class="muted">${escHtml(t('craft.missing.title', 'Missing'))} (${miss.length})</div><div class="mono">${lines}</div>`;
    }

    function toggleMode() {
      if (state.mode === 'filters') state.mode = 'tabs';
      else if (state.mode === 'tabs') state.mode = 'tags';
      else state.mode = 'filters';
      loadGroups().catch(e => setError(String(e)));
    }

    // wire
    el('btnToggle').onclick = toggleMode;
    el('btnSearch').onclick = () => doSearch().catch(e => setError(String(e)));
    el('q').addEventListener('keydown', (e) => { if (e.key === 'Enter') doSearch().catch(err => setError(String(err))); });
    el('btnPlan').onclick = () => doPlan().catch(e => setError(String(e)));
    el('btnMissing').onclick = () => doMissing().catch(e => setError(String(e)));

    const labelSel = el('labelMode');
    if (labelSel) {
      try { labelSel.value = state.labelMode || 'en'; } catch (e) {}
      labelSel.onchange = () => setLabelMode(labelSel.value).catch(e => setError(String(e)));
    }

    function initFromUrl() {
      const params = new URLSearchParams(window.location.search || '');
      const recipe = params.get('recipe');
      const q = params.get('q');
      if (recipe) {
        selectRecipe(recipe).catch(e => setError(String(e)));
        return;
      }
      if (q) {
        el('q').value = q;
        doSearch().catch(e => setError(String(e)));
      }
    }

    // init
    (async () => {
      try {
        await loadMeta();
        await ensureI18nNames(state.labelMode);
        await loadAssets();
        await loadGroups();
        initFromUrl();
      } catch (e) {
        setError(String(e));
      }
    })();
  </script>
</body>
</html>
"""


_CATALOG_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta name="app-root" content="__WAGSTAFF_APP_ROOT__" />
  <title>Wagstaff Catalog</title>
  <style>
    :root {
      --bg: #0f172a;
      --panel: #111827;
      --panel2: #0b1220;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --border: rgba(255,255,255,0.08);
      --chip: rgba(255,255,255,0.10);
      --warn: #f59e0b;
      --err: #ef4444;
    }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
      background: linear-gradient(180deg, #0b1220 0%, #0f172a 70%);
      color: var(--text);
    }
    a { color: inherit; text-decoration: none; }
    .topbar {
      display:flex;
      align-items:center;
      gap: 12px;
      padding: 10px 14px;
      border-bottom: 1px solid var(--border);
      background: rgba(0,0,0,0.20);
      position: sticky;
      top: 0;
      backdrop-filter: blur(6px);
      z-index: 5;
    }
    .brand { font-weight: 700; letter-spacing: 0.3px; }
    .nav { display:flex; gap: 8px; margin-left: 8px; }
    .btn {
      display:inline-flex;
      align-items:center;
      gap: 6px;
      padding: 6px 10px;
      border: 1px solid var(--border);
      border-radius: 999px;
      background: rgba(255,255,255,0.03);
      font-size: 13px;
      cursor: pointer;
      user-select: none;
    }
    .btn.active { border-color: rgba(255,255,255,0.22); background: rgba(255,255,255,0.06); }
    select {
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.03);
      color: var(--text);
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
      outline: none;
      cursor: pointer;
    }
    .meta { margin-left:auto; font-size: 12px; color: var(--muted); white-space: nowrap; overflow:hidden; text-overflow: ellipsis; max-width: 45vw; }

    .wrap {
      display:flex;
      gap: 12px;
      padding: 12px;
    }
    .panel {
      border: 1px solid var(--border);
      border-radius: 12px;
      background: rgba(17,24,39,0.75);
      box-shadow: 0 20px 80px rgba(0,0,0,0.35);
      overflow: hidden;
    }
    .left { width: 42%; min-width: 360px; }
    .right { flex: 1; min-width: 420px; }
    .phead { padding: 10px 12px; border-bottom: 1px solid var(--border); background: rgba(0,0,0,0.12); }
    .pbody { padding: 12px; }
    .row { display:flex; gap: 8px; align-items:center; }
    input[type="text"] {
      flex: 1;
      padding: 8px 10px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: rgba(0,0,0,0.18);
      color: var(--text);
      outline: none;
      font-size: 14px;
    }
    .small { font-size: 12px; color: var(--muted); }
    .muted { color: var(--muted); }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
    .list { max-height: calc(100vh - 190px); overflow:auto; }
    .li {
      display:flex;
      align-items:center;
      gap: 8px;
      padding: 8px 10px;
      border-bottom: 1px solid var(--border);
      cursor: pointer;
    }
    .li:hover { background: rgba(255,255,255,0.04); }
    .li.active { background: rgba(255,255,255,0.07); }
    .icon { width: 28px; height: 28px; border-radius: 6px; border: 1px solid var(--border); background: rgba(255,255,255,0.05); object-fit: contain; }
    .icon.placeholder { display:inline-block; }
    .item { display:inline-flex; align-items:center; gap: 8px; }
    .chips { display:flex; gap: 6px; flex-wrap: wrap; }
    .chip { padding: 2px 8px; border: 1px solid var(--border); border-radius: 999px; background: var(--chip); font-size: 12px; color: var(--muted); }
    .section { margin-top: 14px; }
    pre {
      margin: 0;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid var(--border);
      background: rgba(0,0,0,0.22);
      overflow:auto;
      max-height: 520px;
      font-size: 12px;
      line-height: 1.35;
    }
    details summary { cursor: pointer; color: var(--muted); }
    .err {
      position: fixed;
      bottom: 12px;
      left: 12px;
      right: 12px;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid rgba(239,68,68,0.35);
      background: rgba(239,68,68,0.09);
      color: #fecaca;
      display:none;
      white-space: pre-wrap;
      z-index: 50;
    }
  </style>
</head>
<body>
  <div class="topbar">
    <div class="brand">Wagstaff</div>
    <div class="nav">
      <a class="btn" id="navCraft" href="__WAGSTAFF_APP_ROOT__/">Craft</a>
      <a class="btn" id="navCooking" href="__WAGSTAFF_APP_ROOT__/cooking">Cooking</a>
      <a class="btn active" id="navCatalog" href="__WAGSTAFF_APP_ROOT__/catalog">Catalog</a>
    </div>
    <div class="small" style="display:flex; align-items:center; gap:6px;">
      <span class="muted" id="labelModeLabel">Label</span>
      <select id="labelMode">
        <option value="en">EN</option>
        <option value="zh">中文</option>
        <option value="id">ID</option>
      </select>
    </div>
    <div class="meta" id="meta">…</div>
  </div>

  <div class="wrap">
    <div class="panel left">
      <div class="phead">
        <div class="row">
          <input id="q" type="text" placeholder="Search item id / name. Examples: beefalo, axe, spear, monstermeat" />
          <button class="btn" id="btnSearch">Search</button>
          <button class="btn" id="btnAll">All</button>
        </div>
        <div class="small muted" id="searchHelp">Hints: kind:structure cat:weapon src:craft tag:monster comp:equippable slot:head</div>
        <div class="small" id="stats"></div>
      </div>
      <div class="list" id="list"></div>
    </div>

    <div class="panel right">
      <div class="pbody" id="detail">
        <div class="muted" id="detailEmpty">Select an item.</div>
      </div>
    </div>
  </div>

  <div class="err" id="err"></div>

  <script>
    const APP_ROOT = (document.querySelector('meta[name="app-root"]')?.content || '').replace(/\/+$/,'');
    const api = (path) => APP_ROOT + path;

    const el = (id) => document.getElementById(id);

    function setError(msg) {
      const box = el('err');
      if (!msg) { box.style.display = 'none'; box.textContent = ''; return; }
      box.style.display = 'block';
      box.textContent = String(msg);
    }

    async function fetchJson(url, opts) {
      const r = await fetch(url, opts || {});
      if (!r.ok) {
        const t = await r.text();
        throw new Error(`HTTP ${r.status} ${r.statusText}\n${t}`);
      }
      return await r.json();
    }

    function escHtml(s) {
      return String(s ?? '').replace(/[&<>"']/g, (c) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      }[c]));
    }

    let meta = {};
    let assets = {};
    let icon = null; // {mode, static_base, api_base}
    let activeId = null;

    const state = {
      labelMode: localStorage.getItem('ws_label_mode') || 'en',
      i18n: null,         // meta from /api/v1/meta (set in loadMeta)
      i18nNames: {},      // {lang: {id: name}}
      i18nLoaded: {},     // {lang: true}
      tuningTrace: {},    // {trace_key: trace}
      tuningTraceEnabled: false,
      uiStrings: {},      // {lang: {key: text}}
      uiLoaded: {},       // {lang: true}
    };

    // list render state (supports full catalog without freezing)
    let allKeys = [];
    let viewKeys = [];
    let renderPos = 0;
    const CHUNK = 240;

    function _iconUrls(iid) {
      const cfg = icon || {};
      const mode = String(cfg.mode || 'off');
      const enc = encodeURIComponent(iid);
      const staticBaseRaw = String(cfg.static_base || '/static/icons');
      const staticBase = (APP_ROOT && staticBaseRaw.startsWith('/') && !staticBaseRaw.startsWith(APP_ROOT + '/'))
        ? (APP_ROOT + staticBaseRaw)
        : staticBaseRaw;
      const apiBase = String(cfg.api_base || '/api/v1/icon');
      const staticUrl = api(`${staticBase}/${enc}.png`);
      const apiUrl = api(`${apiBase}/${enc}.png`);

      if (mode === 'dynamic') return { src: apiUrl, fallback: '' };
      if (mode === 'static') return { src: staticUrl, fallback: apiUrl };
      if (mode === 'auto') return { src: staticUrl, fallback: apiUrl };
      return { src: '', fallback: '' };
    }

    function iconError(img) {
      try {
        const fb = img?.dataset?.fallback || '';
        const tried = img?.dataset?.fallbackTried || '';
        if (fb && !tried) {
          img.dataset.fallbackTried = '1';
          img.src = fb;
          return;
        }
        img.style.display = 'none';
        const nxt = img.nextElementSibling;
        if (nxt) nxt.style.display = 'inline-block';
      } catch (e) {
        // ignore
      }
    }

    function _altId(iid) {
      if (!iid) return '';
      const s = String(iid);
      if (s.includes('_')) return s.replace(/_/g,'');
      return '';
    }

    function getI18nName(iid) {
      const mp = (state.i18nNames && state.i18nNames.zh) ? state.i18nNames.zh : null;
      if (!mp) return '';
      const k = String(iid || '').trim();
      if (!k) return '';
      const lo = k.toLowerCase();
      const a1 = _altId(k);
      const a2 = _altId(lo);
      return mp[k] || mp[lo] || (a1 ? mp[a1] : '') || (a2 ? mp[a2] : '') || '';
    }

    async function ensureI18nNames(mode) {
      if (String(mode || '') !== 'zh') return;
      if (state.i18nLoaded && state.i18nLoaded.zh) return;
      const enabled = Boolean(state.i18n && state.i18n.enabled);
      if (!enabled) return;
      try {
        const res = await fetchJson(api('/api/v1/i18n/names/zh'));
        state.i18nNames.zh = res.names || {};
        state.i18nLoaded.zh = true;
      } catch (e) {
        state.i18nLoaded.zh = false;
      }
    }
    // ui i18n (catalog)
    function uiLang() {
      return (state.labelMode === 'zh') ? 'zh' : 'en';
    }

    async function ensureUiStrings(lang) {
      const l = String(lang || '').trim();
      if (!l) return;
      if (state.uiLoaded && state.uiLoaded[l]) return;
      try {
        const res = await fetchJson(api(`/api/v1/i18n/ui/${encodeURIComponent(l)}`));
        state.uiStrings[l] = res.strings || {};
        state.uiLoaded[l] = true;
      } catch (e) {
        state.uiStrings[l] = {};
        state.uiLoaded[l] = false;
      }
    }

    function t(key, fallback) {
      const l = uiLang();
      const mp = (state.uiStrings && state.uiStrings[l]) ? state.uiStrings[l] : {};
      return (mp && mp[key]) ? mp[key] : (fallback || key || '');
    }

    function applyUiStrings() {
      const navCraft = el('navCraft');
      if (navCraft) navCraft.textContent = t('nav.craft', 'Craft');
      const navCooking = el('navCooking');
      if (navCooking) navCooking.textContent = t('nav.cooking', 'Cooking');
      const navCatalog = el('navCatalog');
      if (navCatalog) navCatalog.textContent = t('nav.catalog', 'Catalog');
      const label = el('labelModeLabel');
      if (label) label.textContent = t('label.mode', 'Label');
      const btnSearch = el('btnSearch');
      if (btnSearch) btnSearch.textContent = t('btn.search', 'Search');
      const btnAll = el('btnAll');
      if (btnAll) btnAll.textContent = t('btn.all', 'All');
      const input = el('q');
      if (input) input.placeholder = t('catalog.search.placeholder', input.placeholder || '');
      const hint = el('searchHelp');
      if (hint) hint.textContent = t('catalog.search.hint', hint.textContent || '');
      const detailEmpty = el('detailEmpty');
      if (detailEmpty) detailEmpty.textContent = t('catalog.detail.empty', 'Select an item.');
    }

    async function fetchTuningTrace(prefix) {
      if (!state.tuningTraceEnabled) return {};
      const pfx = String(prefix || '').trim();
      if (!pfx) return {};
      const res = await fetchJson(api(`/api/v1/tuning/trace?prefix=${encodeURIComponent(pfx)}`));
      const traces = res.traces || {};
      for (const k in traces) {
        if (!Object.prototype.hasOwnProperty.call(traces, k)) continue;
        state.tuningTrace[k] = traces[k];
      }
      return traces;
    }

    function applyLabelModeUI() {
      const sel = el('labelMode');
      if (!sel) return;
      const enabled = Boolean(state.i18n && state.i18n.enabled);
      const optZh = sel.querySelector('option[value="zh"]');
      if (optZh) optZh.disabled = !enabled;
      if (!enabled && state.labelMode === 'zh') {
        state.labelMode = 'en';
        try { localStorage.setItem('ws_label_mode', state.labelMode); } catch (e) {}
      }
      sel.value = state.labelMode || 'en';
    }

    function resolveLabel(iid, enName, zhName) {
      const mode = String(state.labelMode || 'en');
      if (mode === 'id') return iid;
      if (mode === 'zh' && zhName) return zhName;
      return enName || iid;
    }

    async function setLabelMode(mode) {
      state.labelMode = String(mode || 'en');
      try { localStorage.setItem('ws_label_mode', state.labelMode); } catch (e) {}
      applyLabelModeUI();
      await ensureI18nNames(state.labelMode);
      await ensureUiStrings(uiLang());
      applyUiStrings();
      const q = el('q').value;
      renderList(q ? searchKeys(q) : listKeys());
    }

    function iconHtmlFor(id, sizePx) {
      const iid = String(id || '').trim();
      const sz = Number(sizePx || 28);
      const { src, fallback } = _iconUrls(iid);
      if (!src) {
        return `<span class="icon placeholder" style="width:${sz}px;height:${sz}px;"></span>`;
      }
      const fbAttr = fallback ? ` data-fallback="${escHtml(fallback)}"` : '';
      return `<span style="display:inline-flex; align-items:center; justify-content:center;">` +
        `<img class="icon" style="width:${sz}px;height:${sz}px;" src="${escHtml(src)}" loading="lazy" onerror="iconError(this)"${fbAttr} />` +
        `<span class="icon placeholder" style="width:${sz}px;height:${sz}px; display:none;"></span>` +
        `</span>`;
    }

    function renderItem(id) {
      const iid = String(id || '').trim();
      const a = assets[iid] || assets[iid.toLowerCase()] || null;
      const zh = getI18nName(iid);
      const label = resolveLabel(iid, a?.name || iid, zh);
      const iconHtml = iconHtmlFor(iid, 28);
      return `<span class="item">${iconHtml}<span>${escHtml(label)}</span></span>`;
    }

    function listKeys() {
      return allKeys;
    }

    function splitQuery(q) {
      const tokens = String(q || '').trim().toLowerCase().split(/\s+/).filter(Boolean);
      const filters = [];
      const words = [];
      for (const tok of tokens) {
        const idx = tok.indexOf(':');
        if (idx > 0) {
          const key = tok.slice(0, idx).trim();
          const val = tok.slice(idx + 1).trim();
          if (key && val) filters.push([key, val]);
          else words.push(tok);
        } else {
          words.push(tok);
        }
      }
      return { filters, words };
    }

    function searchKeys(q) {
      const query = String(q || '').trim();
      if (!query) return [];
      const { filters, words } = splitQuery(query);
      const keys = listKeys();
      const scored = [];
      for (const k of keys) {
        const a = assets[k] || {};
        const id = String(k).toLowerCase();

        if (filters.length) {
          const kind = String(a.kind || '').toLowerCase();
          const cats = (a.categories || []).map(v => String(v).toLowerCase());
          const behs = (a.behaviors || []).map(v => String(v).toLowerCase());
          const srcs = (a.sources || []).map(v => String(v).toLowerCase());
          const tags = (a.tags || []).map(v => String(v).toLowerCase());
          const comps = (a.components || []).map(v => String(v).toLowerCase());
          const slots = (a.slots || []).map(v => String(v).toLowerCase());

          let ok = true;
          for (const [keyRaw, valRaw] of filters) {
            const key = String(keyRaw || '').toLowerCase();
            const vals = String(valRaw || '').split(',').map(v => v.trim().toLowerCase()).filter(Boolean);
            if (!vals.length) continue;
            const hit = (list) => vals.some(v => list.includes(v));

            if (key === 'kind' || key === 'type') {
              if (!vals.includes(kind)) { ok = false; break; }
            } else if (key === 'cat' || key === 'category') {
              if (!hit(cats)) { ok = false; break; }
            } else if (key === 'beh' || key === 'behavior') {
              if (!hit(behs)) { ok = false; break; }
            } else if (key === 'src' || key === 'source') {
              if (!hit(srcs)) { ok = false; break; }
            } else if (key === 'tag') {
              if (!hit(tags)) { ok = false; break; }
            } else if (key === 'comp' || key === 'component') {
              if (!hit(comps)) { ok = false; break; }
            } else if (key === 'slot') {
              if (!hit(slots)) { ok = false; break; }
            } else {
              // unknown filter: ignore
            }
          }
          if (!ok) continue;
        }

        const name = String(a.name || '').toLowerCase();
        const zh = String(getI18nName(k) || '').toLowerCase();
        let score = 0;
        if (!words.length) {
          score = 1;
        } else {
          for (const w of words) {
            if (!w) continue;
            if (id === w) score += 1000;
            if (id.startsWith(w)) score += 200;
            if (id.includes(w)) score += 80;
            if (name.includes(w)) score += 40;
            if (zh.includes(w)) score += 60;
          }
        }
        if (score > 0) scored.push([score, k]);
      }
      scored.sort((x,y) => (y[0]-x[0]) || x[1].localeCompare(y[1]));
      return scored.map(x => x[1]).slice(0, 800);
    }

    function appendListChunk() {
      const box = el('list');
      if (renderPos >= viewKeys.length) return;

      const end = Math.min(renderPos + CHUNK, viewKeys.length);
      const frag = document.createDocumentFragment();

      for (let i = renderPos; i < end; i++) {
        const k = viewKeys[i];
        const a = assets[k] || {};
        const zh = getI18nName(k);
        const label = resolveLabel(k, a.name || k, zh);
        const div = document.createElement('div');
        div.className = 'li' + (k === activeId ? ' active' : '');
        div.dataset.id = k;

        const iconHtml = iconHtmlFor(k, 28);
        const metaBits = [];
        if (a.kind) metaBits.push(a.kind);
        if (a.categories && a.categories.length) metaBits.push(a.categories.slice(0, 2).join(','));
        if (a.sources && a.sources.length) metaBits.push(a.sources.slice(0, 2).join(','));
        const metaLine = metaBits.length ? `<div class="small muted">${escHtml(metaBits.join(' · '))}</div>` : '';
        div.innerHTML = `${iconHtml}<div><div>${escHtml(label)}</div><div class="small mono">${escHtml(k)}</div>${metaLine}</div>`;
        div.onclick = () => openItem(k).catch(e => setError(String(e)));
        frag.appendChild(div);
      }

      box.appendChild(frag);
      renderPos = end;

      // stats line
      const shown = Math.min(renderPos, viewKeys.length);
      el('stats').textContent = `${allKeys.length} items. Showing ${shown}/${viewKeys.length}.`;
    }

    function renderList(keys) {
      viewKeys = (keys || []).slice();
      renderPos = 0;
      const box = el('list');
      box.innerHTML = '';
      if (!viewKeys.length) {
        box.innerHTML = '<div class="pbody muted">No results.</div>';
        el('stats').textContent = `${allKeys.length} items. Showing 0/0.`;
        return;
      }
      appendListChunk();
    }

    function installInfiniteScroll() {
      const box = el('list');
      box.addEventListener('scroll', () => {
        if (box.scrollTop + box.clientHeight >= box.scrollHeight - 200) {
          appendListChunk();
        }
      });
    }

    function setActiveInList(id) {
      activeId = String(id || '').trim();
      for (const node of el('list').querySelectorAll('.li')) {
        if (node.dataset.id === activeId) node.classList.add('active');
        else node.classList.remove('active');
      }
    }


    function recipeLinkCraft(name) {

      return `${APP_ROOT}/?recipe=${encodeURIComponent(name)}`;
    }
    function recipeLinkCooking(name) {
      return `${APP_ROOT}/cooking?recipe=${encodeURIComponent(name)}`;
    }

    function renderRecipeList(names, hrefFn) {
      const arr = names || [];
      if (!arr.length) return '<span class="muted">-</span>';
      return arr.slice(0, 80).map(n => `<div>• <a class="mono" href="${hrefFn(n)}">${escHtml(n)}</a></div>`).join('') +
        (arr.length > 80 ? `<div class="muted">… +${arr.length-80} more</div>` : '');
    }

    function renderChips(list, extraClass) {
      const arr = (list || []).filter(Boolean);
      if (!arr.length) return '<span class="muted">-</span>';
      const cls = extraClass ? ` ${extraClass}` : '';
      return arr.slice(0, 80).map(v => `<span class="chip${cls}">${escHtml(v)}</span>`).join('');
    }

    function renderMonoLines(list, limit) {
      const arr = (list || []).filter(Boolean);
      if (!arr.length) return '<span class="muted">-</span>';
      const cap = Math.max(1, Number(limit || 8));
      const lines = arr.slice(0, cap).map(v => `<div class="mono">${escHtml(v)}</div>`).join('');
      const more = arr.length > cap ? `<div class="muted small">… +${arr.length - cap} more</div>` : '';
      return lines + more;
    }

    function renderAnalysis(rep) {
      if (!rep) return '<span class="muted">-</span>';
      const brain = rep.brain ? `<span class="chip mono">${escHtml(rep.brain)}</span>` : '<span class="muted">-</span>';
      const sg = rep.stategraph ? `<span class="chip mono">${escHtml(rep.stategraph)}</span>` : '<span class="muted">-</span>';
      const tags = (rep.tags || []).slice(0, 60).map(t => `<span class="chip mono">${escHtml(t)}</span>`).join('') || '<span class="muted">-</span>';
      const comps = (rep.components || []).slice(0, 80).map(c => `<span class="chip mono">${escHtml(c)}</span>`).join('') || '<span class="muted">-</span>';
      const evs = (rep.events || []).slice(0, 80).map(e => `<span class="chip mono">${escHtml(e)}</span>`).join('') || '<span class="muted">-</span>';

      return `
        <div class="section">
          <div class="small muted">${escHtml(t('catalog.analysis.brain', 'Brain'))}</div>
          <div class="chips">${brain}</div>
        </div>
        <div class="section">
          <div class="small muted">${escHtml(t('catalog.analysis.stategraph', 'Stategraph'))}</div>
          <div class="chips">${sg}</div>
        </div>
        <div class="section">
          <div class="small muted">${escHtml(t('catalog.analysis.components', 'Components'))}</div>
          <div class="chips">${comps}</div>
        </div>
        <div class="section">
          <div class="small muted">${escHtml(t('catalog.analysis.tags', 'Tags'))}</div>
          <div class="chips">${tags}</div>
        </div>
        <div class="section">
          <div class="small muted">${escHtml(t('catalog.analysis.events', 'Events'))}</div>
          <div class="chips">${evs}</div>
        </div>
        <div class="section">
          <details>
            <summary>${escHtml(t('catalog.analysis.raw_report', 'Raw report (JSON)'))}</summary>
            <pre>${escHtml(JSON.stringify(rep, null, 2))}</pre>
          </details>
        </div>
      `;
    }

    async function openItem(id) {
      setError('');
      const q = String(id || '').trim();
      if (!q) return;
      setActiveInList(q);

      const data = await fetchJson(api(`/api/v1/items/${encodeURIComponent(q)}`));
      const item = data.item || {};
      const asset = data.asset || {};
      const craft = data.craft || {};
      const cooking = data.cooking || {};
      const iconHtml = iconHtmlFor(q, 54);

      const zh = getI18nName(q);
      const label = resolveLabel(q, item?.name || asset?.name || q, zh);
      const atlas = asset?.atlas || '';
      const image = asset?.image || '';
      const iconPath = asset?.icon || '';

      const kind = item?.kind || '';
      const categories = item?.categories || [];
      const behaviors = item?.behaviors || [];
      const sources = item?.sources || [];
      const slots = item?.slots || [];
      const components = item?.components || [];
      const tags = item?.tags || [];
      const prefabFiles = item?.prefab_files || [];
      const brains = item?.brains || [];
      const stategraphs = item?.stategraphs || [];
      const helpers = item?.helpers || [];
      const prefabAssets = item?.prefab_assets || [];
      const stats = item?.stats || {};

      const kindRow = [];
      if (kind) kindRow.push(kind);
      (sources || []).forEach((s) => kindRow.push(`src:${s}`));
      (slots || []).forEach((s) => kindRow.push(`slot:${s}`));

      const cookRec = cooking.as_recipe;

      function cookTraceForField(field) {
        if (!cookRec) return null;
        const v = cookRec[field];
        if (v && typeof v === 'object' && (v.trace || v.expr || v.value !== undefined)) return v;
        if (cookRec._tuning && cookRec._tuning[field]) return cookRec._tuning[field];
        const key = `cooking:${cookRec.name || q}:${field}`;
        return state.tuningTrace[key] || null;
      }

      function cookStat(field) {
        if (!cookRec) return '';
        const tr = cookTraceForField(field);
        if (tr && tr.value !== null && tr.value !== undefined) return tr.value;
        const val = cookRec[field];
        if (val && typeof val === 'object') {
          if (val.value !== undefined && val.value !== null) return val.value;
          if (val.expr !== undefined) return val.expr;
        }
        return val ?? '';
      }

      function renderCookStatRow(field) {
        if (!cookRec) return '<span class="muted">-</span>';
        const tr = cookTraceForField(field);
        const val = cookStat(field);
        const expr = tr ? (tr.expr ?? '') : '';
        const showExpr = expr && String(expr) !== String(val);
        const key = `cooking:${cookRec.name || q}:${field}`;
        const canTrace = Boolean(key);
        const enabled = Boolean(state.tuningTraceEnabled);
        const btn = canTrace
          ? `<button class="btn" data-cook-trace="${escHtml(field)}" ${enabled ? '' : 'disabled'} style="margin-left:6px; padding:2px 6px; font-size:11px;">${escHtml(t('btn.trace', 'Trace'))}</button>`
          : '';
        const details = tr
          ? `<details style="margin-top:4px;"><summary class="small muted">${escHtml(t('label.trace', 'Trace'))}</summary><pre>${escHtml(JSON.stringify(tr, null, 2))}</pre></details>`
          : '';
        return `<div><span class="mono">${escHtml(val ?? '')}</span>${showExpr ? ` <span class="small muted mono">${escHtml(expr)}</span>` : ''}${btn}${details}</div>`;
      }

      const STAT_LABELS = {
        weapon_damage: 'Weapon Damage',
        weapon_range: 'Weapon Range',
        weapon_range_min: 'Weapon Range (min)',
        weapon_range_max: 'Weapon Range (max)',
        combat_damage: 'Combat Damage',
        attack_period: 'Attack Period',
        attack_range: 'Attack Range',
        attack_range_max: 'Attack Range (max)',
        area_damage: 'Area Damage',
        uses_max: 'Max Uses',
        uses: 'Uses',
        armor_condition: 'Armor Condition',
        armor_absorption: 'Armor Absorption',
        edible_health: 'Edible Health',
        edible_hunger: 'Edible Hunger',
        edible_sanity: 'Edible Sanity',
        perish_time: 'Perish Time',
        fuel_level: 'Fuel Level',
        fuel_max: 'Max Fuel',
        dapperness: 'Dapperness',
        insulation: 'Insulation',
        insulation_winter: 'Insulation (Winter)',
        insulation_summer: 'Insulation (Summer)',
        waterproof: 'Waterproof',
        light_radius: 'Light Radius',
        light_intensity: 'Light Intensity',
        light_falloff: 'Light Falloff',
        stack_size: 'Stack Size',
        health_max: 'Max Health',
        sanity_max: 'Max Sanity',
        sanity_rate: 'Sanity Rate',
        sanity_aura: 'Sanity Aura',
        hunger_max: 'Max Hunger',
        hunger_rate: 'Hunger Rate',
        walk_speed: 'Walk Speed',
        run_speed: 'Run Speed',
        speed_multiplier: 'Speed Multiplier',
        recharge_time: 'Recharge Time',
        heat: 'Heat',
        heat_radius: 'Heat Radius',
        planar_damage_base: 'Planar Damage (base)',
        planar_damage_bonus: 'Planar Damage (bonus)',
        planar_damage: 'Planar Damage',
        planar_absorption: 'Planar Absorption',
        planar_absorption_base: 'Planar Absorption (base)',
        work_left: 'Work Left',
      };

      function renderStatRow(statKey, entry) {
        const key = String(statKey || '');
        const label = t(`stat.${key}`, STAT_LABELS[key] || key);
        const val = entry?.value ?? entry?.expr ?? '';
        const expr = entry?.expr ?? '';
        const showExpr = expr && String(expr) !== String(val);
        const traceKey = entry?.trace_key || `item:${q}:stat:${key}`;
        const trace = entry?.trace || state.tuningTrace[traceKey];
        const enabled = Boolean(state.tuningTraceEnabled);
        const btn = traceKey
          ? `<button class="btn" data-item-trace="${escHtml(traceKey)}" ${enabled ? '' : 'disabled'} style="margin-left:6px; padding:2px 6px; font-size:11px;">${escHtml(t('btn.trace', 'Trace'))}</button>`
          : '';
        const details = trace
          ? `<details style="margin-top:4px;"><summary class="small muted">${escHtml(t('label.trace', 'Trace'))}</summary><pre>${escHtml(JSON.stringify(trace, null, 2))}</pre></details>`
          : '';
        return `<div class="row" style="justify-content:space-between; align-items:flex-start;"><div class="small muted">${escHtml(label)}</div><div><span class="mono">${escHtml(val ?? '')}</span>${showExpr ? ` <span class="small muted mono">${escHtml(expr)}</span>` : ''}${btn}${details}</div></div>`;
      }

      function renderStats(statsObj) {
        const entries = Object.entries(statsObj || {});
        if (!entries.length) return '<span class="muted">-</span>';
        return entries.map(([k, v]) => renderStatRow(k, v)).join('');
      }

      const cookBrief = cookRec ? `
        <div class="section">
          <div class="small muted">${escHtml(t('catalog.section.cooking_recipe', 'Cooking recipe'))}</div>
          <div>• <a class="mono" href="${recipeLinkCooking(cookRec.name || q)}">${escHtml(cookRec.name || q)}</a></div>
          <div class="kv" style="margin-top:6px;">
            <div class="k">${escHtml(t('label.hunger', 'Hunger'))}</div><div>${renderCookStatRow('hunger')}</div>
            <div class="k">${escHtml(t('label.health', 'Health'))}</div><div>${renderCookStatRow('health')}</div>
            <div class="k">${escHtml(t('label.sanity', 'Sanity'))}</div><div>${renderCookStatRow('sanity')}</div>
            <div class="k">${escHtml(t('label.perish', 'Perish'))}</div><div>${renderCookStatRow('perishtime')}</div>
            <div class="k">${escHtml(t('label.cooktime', 'Cooktime'))}</div><div>${renderCookStatRow('cooktime')}</div>
          </div>
        </div>
      ` : `
        <div class="section">
          <div class="small muted">${escHtml(t('catalog.section.cooking_recipe', 'Cooking recipe'))}</div>
          <div class="muted">-</div>
        </div>
      `;

      const analyzerEnabled = Boolean(meta.analyzer_enabled);
      const analyzerBox = analyzerEnabled ? `
        <div class="section">
          <div class="row" style="justify-content:space-between;">
            <div class="small muted">${escHtml(t('catalog.section.prefab_analysis', 'Prefab analysis'))}</div>
            <button class="btn" id="btnAnalyze">${escHtml(t('btn.analyze', 'Analyze'))}</button>
          </div>
          <div class="muted small">${escHtml(t('catalog.prefab_analysis_help', 'Uses server-side LuaAnalyzer (prefab parser). Availability depends on how the server was started.'))}</div>
          <div id="analysis"></div>
        </div>
      ` : `
        <div class="section">
          <div class="small muted">${escHtml(t('catalog.section.prefab_analysis', 'Prefab analysis'))}</div>
          <div class="muted">${escHtml(t('catalog.prefab_analysis_disabled', 'Analyzer disabled. Start server with enable_analyzer=true and provide scripts_dir / scripts_zip (or dst_root).'))}</div>
        </div>
      `;

      el('detail').innerHTML = `
        <div class="row" style="align-items:flex-start; gap:12px;">
          ${iconHtml}
          <div style="flex:1;">
            <div style="font-size:18px; font-weight:700;">${escHtml(label)}</div>
            <div class="small mono">${escHtml(q)}</div>
          </div>
        </div>

        <div class="section">
          <div class="small muted">${escHtml(t('catalog.section.kind_sources', 'Kind / Sources / Slots'))}</div>
          <div class="chips">${renderChips(kindRow, 'mono')}</div>
        </div>

        <div class="section">
          <div class="small muted">${escHtml(t('catalog.section.categories', 'Categories'))}</div>
          <div class="chips">${renderChips(categories, '')}</div>
        </div>

        <div class="section">
          <div class="small muted">${escHtml(t('catalog.section.behaviors', 'Behaviors'))}</div>
          <div class="chips">${renderChips(behaviors, '')}</div>
        </div>

        <div class="section">
          <div class="small muted">${escHtml(t('catalog.section.components', 'Components'))}</div>
          <div class="chips">${renderChips(components, 'mono')}</div>
        </div>

        <div class="section">
          <div class="small muted">${escHtml(t('catalog.section.tags', 'Tags'))}</div>
          <div class="chips">${renderChips(tags, 'mono')}</div>
        </div>

        <div class="section">
          <div class="small muted">${escHtml(t('catalog.section.stats', 'Stats'))}</div>
          <div>${renderStats(stats)}</div>
        </div>

        <div class="section">
          <div class="small muted">${escHtml(t('catalog.section.brains', 'Brains'))}</div>
          <div class="chips">${renderChips(brains, 'mono')}</div>
        </div>

        <div class="section">
          <div class="small muted">${escHtml(t('catalog.section.stategraphs', 'Stategraphs'))}</div>
          <div class="chips">${renderChips(stategraphs, 'mono')}</div>
        </div>

        <div class="section">
          <div class="small muted">${escHtml(t('catalog.section.helpers', 'Helpers'))}</div>
          <div class="chips">${renderChips(helpers, 'mono')}</div>
        </div>

        <div class="section">
          <div class="small muted">${escHtml(t('catalog.section.prefab_files', 'Prefab files'))}</div>
          ${renderMonoLines(prefabFiles, 6)}
        </div>

        <div class="section">
          <div class="small muted">${escHtml(t('catalog.section.assets', 'Assets'))}</div>
          <div class="mono">${escHtml(t('label.icon', 'icon'))}: ${escHtml(iconPath || '-')}</div>
          <div class="mono">${escHtml(t('label.atlas', 'atlas'))}: ${escHtml(atlas || '-')}</div>
          <div class="mono">${escHtml(t('label.image', 'image'))}: ${escHtml(image || '-')}</div>
        </div>

        ${prefabAssets && prefabAssets.length ? `<div class="section"><details><summary>${escHtml(t('catalog.section.prefab_assets', 'Prefab assets (raw)'))}</summary><pre>${escHtml(JSON.stringify(prefabAssets, null, 2))}</pre></details></div>` : ''}

        <div class="section">
          <div class="small muted">${escHtml(t('catalog.section.craft_produced', 'Craft: produced by'))}</div>
          ${renderRecipeList(craft.produced_by, recipeLinkCraft)}
        </div>

        <div class="section">
          <div class="small muted">${escHtml(t('catalog.section.craft_used', 'Craft: used as ingredient'))}</div>
          ${renderRecipeList(craft.used_in, recipeLinkCraft)}
        </div>

        ${cookBrief}

        <div class="section">
          <div class="small muted">${escHtml(t('catalog.section.cooking_used', 'Cooking: used as card ingredient'))}</div>
          ${renderRecipeList(cooking.used_in, recipeLinkCooking)}
        </div>

        ${analyzerBox}
      `;

      if (analyzerEnabled) {
        el('btnAnalyze').onclick = async () => {
          try {
            setError('');
            el('analysis').innerHTML = `<div class="muted">${escHtml(t('label.loading', 'Loading...'))}</div>`;
            const res = await fetchJson(api(`/api/v1/analyze/prefab/${encodeURIComponent(q)}`));
            const rep = res.report || {};
            el('analysis').innerHTML = renderAnalysis(rep);
          } catch (e) {
            el('analysis').innerHTML = '';
            setError(String(e));
          }
        };
      }
      if (cookRec) {
        for (const btn of el('detail').querySelectorAll('button[data-cook-trace]')) {
          const field = btn.getAttribute('data-cook-trace');
          if (!field) continue;
          btn.onclick = async () => {
            try {
              setError('');
              await fetchTuningTrace(`cooking:${cookRec.name || q}:${field}`);
              await openItem(q);
            } catch (e) {
              setError(String(e));
            }
          };
        }
      }

      for (const btn of el('detail').querySelectorAll('button[data-item-trace]')) {
        const key = btn.getAttribute('data-item-trace');
        if (!key) continue;
        btn.onclick = async () => {
          try {
            setError('');
            await fetchTuningTrace(key);
            await openItem(q);
          } catch (e) {
            setError(String(e));
          }
        };
      }
    }

    async function loadMeta() {
      meta = await fetchJson(api('/api/v1/meta'));
      state.i18n = (meta && meta.i18n) ? meta.i18n : { enabled: false };
      state.tuningTraceEnabled = Boolean(meta && meta.tuning_trace_enabled);
      applyLabelModeUI();
      await ensureUiStrings(uiLang());
      applyUiStrings();
      const sha = meta.scripts_sha256_12 ? `sha:${meta.scripts_sha256_12}` : '';
      const ver = meta.schema_version ? `v${meta.schema_version}` : '';
      const ae = meta.analyzer_enabled ? 'analyzer:on' : 'analyzer:off';
      const te = meta.tuning_enabled ? 'tuning:on' : 'tuning:off';
      el('meta').textContent = [ver, sha, ae, te].filter(Boolean).join(' · ');

      el('navCraft').href = APP_ROOT + '/';
      el('navCooking').href = APP_ROOT + '/cooking';
      el('navCatalog').href = APP_ROOT + '/catalog';
    }

    async function loadAssets() {
      const res = await fetchJson(api('/api/v1/catalog/index'));
      assets = {};
      allKeys = [];
      icon = res.icon || null;
      (res.items || []).forEach((it) => {
        const iid = String(it.id || '').trim();
        if (!iid) return;
        assets[iid] = {
          name: it.name || iid,
          image: it.image || null,
          icon: it.icon || it.image || null,
          kind: it.kind || '',
          categories: Array.isArray(it.categories) ? it.categories : [],
          behaviors: Array.isArray(it.behaviors) ? it.behaviors : [],
          sources: Array.isArray(it.sources) ? it.sources : [],
          tags: Array.isArray(it.tags) ? it.tags : [],
          components: Array.isArray(it.components) ? it.components : [],
          slots: Array.isArray(it.slots) ? it.slots : [],
        };
        allKeys.push(iid);
      });
      allKeys.sort();
      el('stats').textContent = `${allKeys.length} items. Showing 0/0.`;
    }

    function initFromUrl() {
      const params = new URLSearchParams(window.location.search || '');
      const item = params.get('item');
      const q = params.get('q');
      if (q) {
        el('q').value = q;
        renderList(searchKeys(q));
        return;
      }
      if (item) {
        el('q').value = item;
        renderList(searchKeys(item));
        openItem(item).catch(e => setError(String(e)));
      }
    }

    el('btnSearch').onclick = () => {
      try {
        setError('');
        const q = el('q').value;
        renderList(searchKeys(q));
      } catch (e) { setError(String(e)); }
    };

    el('btnAll').onclick = () => {
      try {
        setError('');
        el('q').value = '';
        renderList(listKeys());
      } catch (e) { setError(String(e)); }
    };

    el('q').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') el('btnSearch').click();
    });

    const labelSel = el('labelMode');
    if (labelSel) {
      try { labelSel.value = state.labelMode || 'en'; } catch (e) {}
      labelSel.onchange = () => setLabelMode(labelSel.value).catch(e => setError(String(e)));
    }

    (async () => {
      try {
        await loadMeta();
        await loadAssets();
        await ensureI18nNames(state.labelMode);
        installInfiniteScroll();
        renderList(listKeys());
        initFromUrl();
      } catch (e) {
        setError(String(e));
      }
    })();
  </script>
</body>
</html>
"""


def render_catalog_html(app_root: str = "") -> str:
    """Render the Catalog UI page."""
    from html import escape as _esc

    return _CATALOG_TEMPLATE.replace("__WAGSTAFF_APP_ROOT__", _esc(app_root or ""))



def render_index_html(app_root: str = "") -> str:
    """Render the UI page.

    app_root:
      - ""       normal direct serving
      - "/xxx"   reverse proxy mount path
    """
    return _INDEX_TEMPLATE.replace("__WAGSTAFF_APP_ROOT__", escape(app_root or ""))


_COOKING_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="app-root" content="__WAGSTAFF_APP_ROOT__" />
  <title>Wagstaff WebCraft - Cooking</title>
  <style>
    :root {
      --bg: #0b0f14;
      --panel: #0f1722;
      --panel2: #111b29;
      --text: #e6edf3;
      --muted: #9fb0c0;
      --border: #233042;
      --accent: #79c0ff;
      --accent2: #a5d6ff;
      --bad: #ff7b72;
      --ok: #7ee787;
    }
    html, body {
      margin: 0; padding: 0;
      background: var(--bg);
      color: var(--text);
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
    }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }

    .topbar {
      position: sticky;
      top: 0;
      z-index: 10;
      display: flex;
      gap: 12px;
      align-items: center;
      padding: 10px 12px;
      border-bottom: 1px solid var(--border);
      background: rgba(11, 15, 20, 0.92);
      backdrop-filter: blur(8px);
    }
    .topbar h1 {
      font-size: 14px;
      margin: 0;
      font-weight: 650;
      letter-spacing: .3px;
      color: var(--accent2);
    }

    .nav {
      font-size: 12px;
      color: var(--muted);
      padding: 4px 10px;
      border: 1px solid var(--border);
      border-radius: 999px;
      background: rgba(17,27,41,0.6);
    }
    .nav:hover {
      text-decoration: none;
      border-color: #3b4b63;
      color: var(--text);
    }
    .nav.active {
      color: var(--text);
      border-color: rgba(121, 192, 255, 0.45);
      background: rgba(121, 192, 255, 0.10);
    }

    .search {
      flex: 1;
      display: flex;
      gap: 8px;
      align-items: center;
    }
    input[type="text"], textarea {
      width: 100%;
      background: var(--panel);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 10px;
      outline: none;
    }
    textarea {
      min-height: 60px;
      resize: vertical;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    }
    select {
      background: var(--panel2);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 6px 8px;
      font-size: 12px;
      outline: none;
    }
    button {
      background: var(--panel2);
      border: 1px solid var(--border);
      color: var(--text);
      border-radius: 8px;
      padding: 8px 10px;
      cursor: pointer;
    }
    button:hover { border-color: #3b4b63; }
    button.primary {
      background: rgba(121, 192, 255, 0.12);
      border-color: rgba(121, 192, 255, 0.25);
    }
    button.primary:hover {
      border-color: rgba(121, 192, 255, 0.45);
    }

    .layout {
      display: grid;
      grid-template-columns: 260px 1fr 420px;
      gap: 10px;
      padding: 10px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 10px;
      overflow: hidden;
      min-height: calc(100vh - 62px);
    }
    .panel h2 {
      margin: 0;
      padding: 10px 12px;
      font-size: 13px;
      border-bottom: 1px solid var(--border);
      color: var(--muted);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .list {
      max-height: calc(100vh - 62px - 44px);
      overflow: auto;
    }
    .item {
      padding: 8px 12px;
      border-bottom: 1px solid rgba(35, 48, 66, 0.65);
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      gap: 10px;
    }
    .item:hover { background: rgba(255,255,255,0.03); }
    .item.active { background: rgba(121,192,255,0.08); }
    .item .name { font-weight: 560; }
    .item .meta { color: var(--muted); font-size: 12px; }

    .detail {
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .kv {
      display: grid;
      grid-template-columns: 120px 1fr;
      gap: 6px 10px;
      font-size: 13px;
    }
    .kv .k { color: var(--muted); }

    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .chip {
      font-size: 12px;
      color: var(--muted);
      padding: 3px 8px;
      border: 1px solid rgba(35,48,66,0.9);
      border-radius: 999px;
      background: rgba(17,27,41,0.8);
    }

    .grid2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }

    .err {
      color: var(--bad);
      font-size: 12px;
      white-space: pre-wrap;
    }
    .ok {
      color: var(--ok);
      font-size: 12px;
    }

    .muted { color: var(--muted); }
    .small { font-size: 12px; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
    .itemRef {
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .itemIcon {
      width: 18px;
      height: 18px;
      border-radius: 4px;
      border: 1px solid rgba(35,48,66,0.9);
      background: rgba(17,27,41,0.8);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex: 0 0 auto;
      overflow: hidden;
    }
    .itemIconImg {
      width: 100%;
      height: 100%;
      display: block;
      object-fit: contain;
      image-rendering: pixelated;
    }
    .itemIconFallback {
      width: 100%;
      height: 100%;
      display: none;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      color: var(--muted);
    }
    .itemLabel {
      color: var(--text);
    }
  </style>
</head>
<body>
  <div class="topbar">
    <div style="display:flex; gap:10px; align-items:center;">
      <h1>Wagstaff WebCraft</h1>
      <a id="navCraft" class="nav" href="#">Craft</a>
      <a id="navCooking" class="nav active" href="#">Cooking</a>
      <a id="navCatalog" class="nav" href="#">Catalog</a>
      <div class="small" style="display:flex; align-items:center; gap:6px;">
        <span class="muted" id="labelModeLabel">Label</span>
        <select id="labelMode">
          <option value="en">EN</option>
          <option value="zh">中文</option>
          <option value="id">ID</option>
        </select>
      </div>
    </div>
    <div class="search">
      <input id="q" type="text" placeholder="Search: meatballs | ing:berries | tag:honeyed | type:FOODTYPE.MEAT" />
      <button id="btnSearch" class="primary">Search</button>
    </div>
    <div class="small muted" id="meta"></div>
  </div>

  <div class="layout">
    <div class="panel">
      <h2>
        <span id="groupTitle">FoodTypes</span>
        <button id="btnToggle">Toggle</button>
      </h2>
      <div class="list" id="groupList"></div>
    </div>

    <div class="panel">
      <h2>
        <span id="listTitle">Recipes</span>
        <span class="small muted" id="listCount"></span>
      </h2>
      <div class="list" id="recipeList"></div>
    </div>

    <div class="panel">
      <h2 id="detailTitle">Details / Tools</h2>
      <div class="detail">
        <div id="detail"></div>

        <div>
          <div class="small muted" id="inventoryHelp">Available ingredients (for search)</div>
          <textarea id="inv" placeholder="berries=2\ncarrot=3\nmeat=1"></textarea>
          <div style="display:flex; gap:8px; margin-top:8px;">
            <button id="btnFind" class="primary" style="flex:1;">Find cookable</button>
            <button id="btnShowAll" style="flex:1;">Show all</button>
          </div>
        </div>

        <div>
          <div class="small muted" id="slotsHelp">Cookpot slots (requires total = 4)</div>
          <textarea id="slots" placeholder="carrot=2\nberries=1\nbutterflywings=1"></textarea>
          <button id="btnSim" class="primary" style="width:100%; margin-top:8px;">Simulate</button>
        </div>

        <div id="out" class="small"></div>
        <div class="err" id="err"></div>
      </div>
    </div>
  </div>

  <script>
    const APP_ROOT = (document.querySelector('meta[name="app-root"]')?.content || '').replace(/\/+$/,'');
    const api = (path) => APP_ROOT + path;

    const el = (id) => document.getElementById(id);

    function setError(msg) {
      el('err').textContent = msg || '';
    }

    function parseInventory(text) {
      const out = {};
      const raw = (text || '').trim();
      if (!raw) return out;

      const parts = raw
        .split(/[,\n]/g)
        .map(s => s.trim())
        .filter(Boolean);

      for (const p of parts) {
        const m = p.match(/^([^=\s]+)\s*(?:=|\s)\s*([0-9]+(?:\.[0-9]+)?)$/);
        if (!m) continue;
        const k = m[1].trim();
        const v = parseFloat(m[2]);
        if (!k || !Number.isFinite(v) || v <= 0) continue;
        out[k] = v;
      }
      return out;
    }

    function parseSlots(text) {
      const raw = (text || '').trim();
      if (!raw) return {};

      // prefer explicit counts
      const asInv = parseInventory(raw);
      if (Object.keys(asInv).length) return asInv;

      // fallback: "a, b, c" means each counts as 1
      const out = {};
      const parts = raw
        .split(/[,\n]/g)
        .map(s => s.trim())
        .filter(Boolean);

      for (const p of parts) {
        out[p] = (out[p] || 0) + 1;
      }
      return out;
    }

    async function fetchJson(url, opts) {
      const r = await fetch(url, opts || {});
      if (!r.ok) {
        const t = await r.text();
        throw new Error(`HTTP ${r.status} ${r.statusText}\n${t}`);
      }
      return await r.json();
    }

    function escHtml(s) {
      return String(s ?? '').replace(/[&<>"']/g, (c) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      }[c]));
    }

    async function loadAssets() {
      try {
        const res = await fetchJson(api('/api/v1/assets'));
        state.assets = res.assets || {};
        state.icon = res.icon || null;
      } catch (e) {
        state.assets = {};
        state.icon = null;
      }
    }

    function _iconUrls(iid) {
      const cfg = state.icon || {};
      const mode = String(cfg.mode || 'off');
      const enc = encodeURIComponent(iid);
      const staticBaseRaw = String(cfg.static_base || '/static/icons');
      const staticBase = (APP_ROOT && staticBaseRaw.startsWith('/') && !staticBaseRaw.startsWith(APP_ROOT + '/'))
        ? (APP_ROOT + staticBaseRaw)
        : staticBaseRaw;
      const apiBase = String(cfg.api_base || '/api/v1/icon');
      const staticUrl = api(`${staticBase}/${enc}.png`);
      const apiUrl = api(`${apiBase}/${enc}.png`);

      if (mode === 'dynamic') return { src: apiUrl, fallback: '' };
      if (mode === 'static') return { src: staticUrl, fallback: apiUrl };
      if (mode === 'auto') return { src: staticUrl, fallback: apiUrl };
      return { src: '', fallback: '' };
    }

    function iconError(img) {
      try {
        const fb = img?.dataset?.fallback || '';
        const tried = img?.dataset?.fallbackTried || '';
        if (fb && !tried) {
          img.dataset.fallbackTried = '1';
          img.src = fb;
          return;
        }
        img.style.display = 'none';
        const nxt = img.nextElementSibling;
        if (nxt) nxt.style.display = 'flex';
      } catch (e) {
        // ignore
      }
    }

    function _altId(iid) {
      if (!iid) return '';
      const s = String(iid);
      if (s.includes('_')) return s.replace(/_/g,'');
      return '';
    }

    function getI18nName(iid) {
      const mp = (state.i18nNames && state.i18nNames.zh) ? state.i18nNames.zh : null;
      if (!mp) return '';
      const k = String(iid || '').trim();
      if (!k) return '';
      const lo = k.toLowerCase();
      const a1 = _altId(k);
      const a2 = _altId(lo);
      return mp[k] || mp[lo] || (a1 ? mp[a1] : '') || (a2 ? mp[a2] : '') || '';
    }

    async function ensureI18nNames(mode) {
      if (String(mode || '') !== 'zh') return;
      if (state.i18nLoaded && state.i18nLoaded.zh) return;
      const enabled = Boolean(state.i18n && state.i18n.enabled);
      if (!enabled) return;
      try {
        const res = await fetchJson(api('/api/v1/i18n/names/zh'));
        state.i18nNames.zh = res.names || {};
        state.i18nLoaded.zh = true;
      } catch (e) {
        state.i18nLoaded.zh = false;
      }
    }

    // ui i18n (cooking)
    function uiLang() {
      return (state.labelMode === 'zh') ? 'zh' : 'en';
    }

    async function ensureUiStrings(lang) {
      const l = String(lang || '').trim();
      if (!l) return;
      if (state.uiLoaded && state.uiLoaded[l]) return;
      try {
        const res = await fetchJson(api(`/api/v1/i18n/ui/${encodeURIComponent(l)}`));
        state.uiStrings[l] = res.strings || {};
        state.uiLoaded[l] = true;
      } catch (e) {
        state.uiStrings[l] = {};
        state.uiLoaded[l] = false;
      }
    }

    function t(key, fallback) {
      const l = uiLang();
      const mp = (state.uiStrings && state.uiStrings[l]) ? state.uiStrings[l] : {};
      return (mp && mp[key]) ? mp[key] : (fallback || key || '');
    }

    function applyUiStrings() {
      const navCraft = el('navCraft');
      if (navCraft) navCraft.textContent = t('nav.craft', 'Craft');
      const navCooking = el('navCooking');
      if (navCooking) navCooking.textContent = t('nav.cooking', 'Cooking');
      const navCatalog = el('navCatalog');
      if (navCatalog) navCatalog.textContent = t('nav.catalog', 'Catalog');
      const label = el('labelModeLabel');
      if (label) label.textContent = t('label.mode', 'Label');
      const btnSearch = el('btnSearch');
      if (btnSearch) btnSearch.textContent = t('btn.search', 'Search');
      const btnToggle = el('btnToggle');
      if (btnToggle) btnToggle.textContent = t('btn.toggle', 'Toggle');
      const listTitle = el('listTitle');
      if (listTitle) {
        const txt = listTitle.textContent || '';
        if (!txt.includes(':') && !txt.includes('(')) {
          listTitle.textContent = t('cooking.list.recipes', txt || 'Recipes');
        }
      }
      const groupTitle = el('groupTitle');
      if (groupTitle) {
        if (state.mode === 'foodtypes') groupTitle.textContent = t('cooking.group.foodtypes', 'FoodTypes');
        else if (state.mode === 'tags') groupTitle.textContent = t('cooking.group.tags', 'Tags');
        else groupTitle.textContent = t('cooking.group.all', 'All');
      }
      const detailTitle = el('detailTitle');
      if (detailTitle) detailTitle.textContent = t('cooking.detail.title', 'Details / Tools');
      const invHelp = el('inventoryHelp');
      if (invHelp) invHelp.textContent = t('cooking.inventory.help', 'Available ingredients (for search)');
      const slotsHelp = el('slotsHelp');
      if (slotsHelp) slotsHelp.textContent = t('cooking.slots.help', 'Cookpot slots (requires total = 4)');
      const input = el('q');
      if (input) input.placeholder = t('cooking.search.placeholder', input.placeholder || '');
      const inv = el('inv');
      if (inv) inv.placeholder = t('cooking.inventory.placeholder', inv.placeholder || '');
      const slots = el('slots');
      if (slots) slots.placeholder = t('cooking.slots.placeholder', slots.placeholder || '');
      const btnFind = el('btnFind');
      if (btnFind) btnFind.textContent = t('btn.find_cookable', 'Find cookable');
      const btnShowAll = el('btnShowAll');
      if (btnShowAll) btnShowAll.textContent = t('btn.show_all', 'Show all');
      const btnSim = el('btnSim');
      if (btnSim) btnSim.textContent = t('btn.simulate', 'Simulate');
    }

    async function fetchTuningTrace(prefix) {
      if (!state.tuningTraceEnabled) return {};
      const pfx = String(prefix || '').trim();
      if (!pfx) return {};
      const res = await fetchJson(api(`/api/v1/tuning/trace?prefix=${encodeURIComponent(pfx)}`));
      const traces = res.traces || {};
      for (const k in traces) {
        if (!Object.prototype.hasOwnProperty.call(traces, k)) continue;
        state.tuningTrace[k] = traces[k];
      }
      return traces;
    }

    function applyLabelModeUI() {
      const sel = el('labelMode');
      if (!sel) return;
      const enabled = Boolean(state.i18n && state.i18n.enabled);
      const optZh = sel.querySelector('option[value="zh"]');
      if (optZh) optZh.disabled = !enabled;
      if (!enabled && state.labelMode === 'zh') {
        state.labelMode = 'en';
        try { localStorage.setItem('ws_label_mode', state.labelMode); } catch (e) {}
      }
      sel.value = state.labelMode || 'en';
    }

    function resolveLabel(iid, enName, zhName) {
      const mode = String(state.labelMode || 'en');
      if (mode === 'id') return iid;
      if (mode === 'zh' && zhName) return zhName;
      return enName || iid;
    }

    async function setLabelMode(mode) {
      state.labelMode = String(mode || 'en');
      try { localStorage.setItem('ws_label_mode', state.labelMode); } catch (e) {}
      applyLabelModeUI();
      await ensureI18nNames(state.labelMode);
      await ensureUiStrings(uiLang());
      applyUiStrings();
      renderRecipeList();
      renderRecipeDetail(state.activeRecipeData);
    }

    function renderItem(id) {
      const iid = String(id || '').trim();
      if (!iid) return '';
      const m = (state.assets && state.assets[iid]) ? state.assets[iid] : null;
      const enName = (m && m.name) ? m.name : iid;
      const zhName = getI18nName(iid);
      const name = resolveLabel(iid, enName, zhName);

      const tipParts = [`id:${iid}`];
      if (enName && enName !== iid) tipParts.push(`en:${enName}`);
      if (zhName && zhName !== enName && zhName !== iid) tipParts.push(`zh:${zhName}`);
      if (m && m.image) tipParts.push(`img:${m.image}`);
      if (m && m.atlas) tipParts.push(`atlas:${m.atlas}`);
      const tip = escHtml(tipParts.join(' | '));

      const { src, fallback } = _iconUrls(iid);
      const iconChar = (m && (m.image || m.atlas)) ? '🖼️' : '📦';

      if (!src) {
        return `<span class="itemRef" title="${tip}">` +
          `<span class="itemIcon"><span class="itemIconFallback" style="display:flex;">${iconChar}</span></span>` +
          `<span class="itemLabel">${escHtml(name)}</span></span>`;
      }

      const fbAttr = fallback ? ` data-fallback="${escHtml(fallback)}"` : '';
      return `<span class="itemRef" title="${tip}">` +
        `<span class="itemIcon">` +
          `<img class="itemIconImg" src="${escHtml(src)}"${fbAttr} onerror="iconError(this)" alt="" />` +
          `<span class="itemIconFallback">${iconChar}</span>` +
        `</span>` +
        `<span class="itemLabel">${escHtml(name)}</span>` +
      `</span>`;
    }


    const state = {
      mode: 'foodtypes', // foodtypes | tags | all
      groups: [],
      activeGroup: null,
      recipes: [],
      activeRecipe: null,
      activeRecipeData: null,
      assets: {},
      icon: null, // {mode, static_base, api_base}

      // label mode: en | zh | id (persisted in localStorage)
      labelMode: localStorage.getItem('ws_label_mode') || 'en',
      i18n: null,         // meta from /api/v1/meta (set in loadMeta)
      i18nNames: {},      // {lang: {id: name}}
      i18nLoaded: {},     // {lang: true}
      tuningTrace: {},    // {trace_key: trace}
      tuningTraceEnabled: false,
      uiStrings: {},      // {lang: {key: text}}
      uiLoaded: {},       // {lang: true}
    };

    function renderGroupList() {
      const box = el('groupList');
      box.innerHTML = '';
      for (const g of state.groups) {
        const div = document.createElement('div');
        div.className = 'item' + (state.activeGroup === g.name ? ' active' : '');
        div.innerHTML = `<span class="name">${g.name}</span><span class="meta">${g.count ?? ''}</span>`;
        div.onclick = () => selectGroup(g.name);
        box.appendChild(div);
      }
    }

    function renderRecipeList() {
      const box = el('recipeList');
      box.innerHTML = '';
      el('listCount').textContent = state.recipes.length ? `${state.recipes.length}` : '';
      for (const nm of state.recipes) {
        const div = document.createElement('div');
        div.className = 'item' + (state.activeRecipe === nm ? ' active' : '');
        div.innerHTML = `<span class="name">${renderItem(nm)}</span><span class="meta"></span>`;
        div.onclick = () => selectRecipe(nm);
        box.appendChild(div);
      }
    }

    function renderRecipeDetail(rec) {
      if (!rec) {
        el('detail').innerHTML = `<div class="muted">${escHtml(t('cooking.detail.empty', 'Select a recipe.'))}</div>`;
        return;
      }

      const tags = (rec.tags || []).map(x => `<span class="chip">${x}</span>`).join('');
      const card = (rec.card_ingredients || []).map(row => {
        const item = row[0];
        const cnt = row[1];
        return `<div>• ${renderItem(item)} <span class="mono">x${escHtml(cnt)}</span></div>`;
      }).join('');


      const rule = rec.rule || null;

      function renderRule(rule, includeTitle = true) {
        if (!rule) return '';
        const kind = escHtml(rule.kind || '');
        const expr = escHtml(rule.expr || '');
        const cons = rule.constraints || null;
        const title = includeTitle
          ? `<div class="small muted">${escHtml(t('cooking.rule.title', 'Rule'))}${kind ? ` (${kind})` : ''}</div>`
          : '';

        let consHtml = '';
        if (cons) {
          const tags = (cons.tags || []).map(c => `<div>• <span class="mono">${escHtml(c.text || '')}</span></div>`).join('');
          const names = (cons.names || []).map(c => `<div>• <span class="mono">${escHtml(c.text || '')}</span></div>`).join('');
          const unp = (cons.unparsed || []).map(x => `<div>• <span class="mono">${escHtml(x)}</span></div>`).join('');
          const any = Boolean(tags || names || unp);
          consHtml = `
            <div style="margin-top:8px;">
              <div class="small muted">${escHtml(t('cooking.rule.constraints', 'Constraints (best-effort)'))}</div>
              ${tags ? `<div><div class="small muted">${escHtml(t('cooking.rule.constraints.tags', 'tags'))}</div>${tags}</div>` : ''}
              ${names ? `<div style="margin-top:6px;"><div class="small muted">${escHtml(t('cooking.rule.constraints.names', 'names'))}</div>${names}</div>` : ''}
              ${unp ? `<div style="margin-top:6px;"><div class="small muted">${escHtml(t('cooking.rule.constraints.unparsed', 'unparsed'))}</div>${unp}</div>` : ''}
              ${any ? '' : '<span class="muted">-</span>'}
            </div>
          `;
        }

        return `
          ${title}
          <div class="mono" style="white-space:pre-wrap; line-height:1.35;">${expr || '<span class="muted">-</span>'}</div>
          ${consHtml}
        `;
      }

      const cardBody = card
        ? card
        : (rule ? renderRule(rule, false) : '<span class="muted">-</span>');
      const tuning = rec._tuning || {};
      const traceKey = (field) => rec?.name ? `cooking:${rec.name}:${field}` : '';
      const traceCache = state.tuningTrace || {};
      const fields = ['hunger', 'health', 'sanity', 'perishtime', 'cooktime'];

      function traceForField(field) {
        const raw = rec ? rec[field] : null;
        if (raw && typeof raw === 'object' && (raw.trace || raw.expr || raw.value !== undefined)) return raw;
        if (tuning && tuning[field]) return tuning[field];
        const key = traceKey(field);
        return key ? traceCache[key] : null;
      }

      function renderStat(field) {
        const raw = rec ? rec[field] : null;
        const tr = traceForField(field);
        const expr = tr ? (tr.expr ?? raw ?? '') : (raw ?? '');
        const val = tr && (tr.value !== null && tr.value !== undefined) ? tr.value : raw;
        const hasVal = (val !== null && val !== undefined);

        const main = hasVal
          ? `<span class="mono">${escHtml(val)}</span> <span class="small muted mono">${escHtml(expr ?? '')}</span>`
          : `<span class="mono">${escHtml(expr ?? '')}</span>`;

        const enabled = Boolean(state.tuningTraceEnabled);
        const key = traceKey(field);
        const btn = key
          ? `<button class="btn" data-cook-trace="${escHtml(field)}" ${enabled ? '' : 'disabled'} style="margin-left:6px; padding:2px 6px; font-size:11px;">${escHtml(t('btn.trace', 'Trace'))}</button>`
          : '';

        const details = tr
          ? `<details style="margin-top:4px;">
              <summary class="small muted">${escHtml(t('label.trace', 'Trace'))}</summary>
              <div class="mono small" style="white-space:pre-wrap; line-height:1.35; border:1px solid rgba(35,48,66,0.9); border-radius:8px; padding:8px; background: rgba(17,27,41,0.35);">${escHtml(JSON.stringify(tr, null, 2))}</div>
            </details>`
          : '';

        return `<div>${main}${btn}${details}</div>`;
      }

      const extraRule = (card && rule)
        ? `<div style="margin-top:10px;">${renderRule(rule, true)}</div>`
        : '';

      el('detail').innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:baseline; gap:10px;">
          <div style="font-size:16px; font-weight:650;">${renderItem(rec.name || '')}</div>
          <div class="small muted">${String(rec.foodtype || '').replace('FOODTYPE.','')}</div>
        </div>
        <div class="kv">
          <div class="k">${escHtml(t('label.priority', 'Priority'))}</div><div class="mono">${rec.priority ?? ''}</div>
          <div class="k">${escHtml(t('label.hunger', 'Hunger'))}</div><div>${renderStat('hunger')}</div>
          <div class="k">${escHtml(t('label.health', 'Health'))}</div><div>${renderStat('health')}</div>
          <div class="k">${escHtml(t('label.sanity', 'Sanity'))}</div><div>${renderStat('sanity')}</div>
          <div class="k">${escHtml(t('label.perish', 'Perish'))}</div><div>${renderStat('perishtime')}</div>
          <div class="k">${escHtml(t('label.cooktime', 'Cooktime'))}</div><div>${renderStat('cooktime')}</div>
        </div>
        <div>
          <div class="small muted">${escHtml(t('label.tags', 'Tags'))}</div>
          <div class="chips">${tags || '<span class="muted">-</span>'}</div>
        </div>
        <div>
          <div class="small muted">${escHtml(card ? t('cooking.card.ingredients', 'Card ingredients') : (rule ? t('cooking.rule.conditional', 'Recipe rule (conditional)') : t('cooking.card.ingredients', 'Card ingredients')))}</div>
          ${cardBody}
          ${extraRule}
        </div>
      `;

      for (const btn of el('detail').querySelectorAll('button[data-cook-trace]')) {
        const field = btn.getAttribute('data-cook-trace');
        if (!field || !rec.name) continue;
        btn.onclick = async () => {
          try {
            setError('');
            await fetchTuningTrace(`cooking:${rec.name}:${field}`);
            renderRecipeDetail(rec);
          } catch (e) {
            setError(String(e));
          }
        };
      }
    }

    async function loadMeta() {
      const m = await fetchJson(api('/api/v1/meta'));
      state.i18n = (m && m.i18n) ? m.i18n : { enabled: false };
      state.tuningTraceEnabled = Boolean(m && m.tuning_trace_enabled);
      applyLabelModeUI();
      await ensureUiStrings(uiLang());
      applyUiStrings();
      const sha = m.scripts_sha256_12 ? `sha:${m.scripts_sha256_12}` : '';
      const ae = m.analyzer_enabled ? 'analyzer:on' : 'analyzer:off';
      const te = m.tuning_enabled ? 'tuning:on' : 'tuning:off';
      el('meta').textContent = `${sha} | mode:${m.engine_mode || ''} | files:${m.scripts_file_count || ''} | ${ae} | ${te}`;
    }

    async function loadGroups() {
      setError('');

      if (state.mode === 'foodtypes') {
        el('groupTitle').textContent = t('cooking.group.foodtypes', 'FoodTypes');
        const res = await fetchJson(api('/api/v1/cooking/foodtypes'));
        state.groups = (res.foodtypes || []).map(t => ({ name: t.name, count: t.count }));
      } else if (state.mode === 'tags') {
        el('groupTitle').textContent = t('cooking.group.tags', 'Tags');
        const res = await fetchJson(api('/api/v1/cooking/tags'));
        state.groups = (res.tags || []).map(t => ({ name: t.name, count: t.count }));
      } else {
        el('groupTitle').textContent = t('cooking.group.all', 'All');
        const res = await fetchJson(api('/api/v1/cooking/recipes'));
        state.groups = [{ name: 'ALL', count: res.count || '' }];
      }

      state.activeGroup = null;
      state.recipes = [];
      state.activeRecipe = null;
      state.activeRecipeData = null;
      renderGroupList();
      renderRecipeList();
      renderRecipeDetail(null);
    }

    async function selectGroup(name) {
      setError('');
      state.activeGroup = name;
      renderGroupList();

      let url = '';
      if (state.mode === 'foodtypes') url = api(`/api/v1/cooking/foodtypes/${encodeURIComponent(name)}/recipes`);
      else if (state.mode === 'tags') url = api(`/api/v1/cooking/tags/${encodeURIComponent(name)}/recipes`);
      else url = api('/api/v1/cooking/recipes');

      const res = await fetchJson(url);
      state.recipes = (res.recipes || []);
      state.activeRecipe = null;
      state.activeRecipeData = null;

      el('listTitle').textContent = (state.mode === 'all')
        ? t('cooking.list.all_recipes', 'All recipes')
        : t('cooking.list.recipes', 'Recipes');
      renderRecipeList();
      renderRecipeDetail(null);
    }

    async function selectRecipe(name) {
      setError('');
      state.activeRecipe = name;
      renderRecipeList();
      const res = await fetchJson(api(`/api/v1/cooking/recipes/${encodeURIComponent(name)}`));
      state.activeRecipeData = res.recipe || null;
      // ensure name always present
      if (state.activeRecipeData && !state.activeRecipeData.name) state.activeRecipeData.name = name;
      renderRecipeDetail(state.activeRecipeData);
    }

    async function doSearch() {
      setError('');
      const q = el('q').value.trim();
      if (!q) return;
      const res = await fetchJson(api(`/api/v1/cooking/recipes/search?q=${encodeURIComponent(q)}&limit=200`));
      const results = (res.results || []).map(r => r.name).filter(Boolean);
      state.recipes = results;
      state.activeGroup = null;
      state.activeRecipe = null;
      state.activeRecipeData = null;
      renderGroupList();
      renderRecipeList();
      renderRecipeDetail(null);
      el('listTitle').textContent = `${t('label.search', 'Search')}: ${q}`;
    }

    async function showAll() {
      setError('');
      const res = await fetchJson(api('/api/v1/cooking/recipes'));
      state.recipes = (res.recipes || []);
      state.activeGroup = null;
      state.activeRecipe = null;
      state.activeRecipeData = null;
      renderGroupList();
      renderRecipeList();
      renderRecipeDetail(null);
      el('listTitle').textContent = t('cooking.list.all_recipes', 'All recipes');
    }

    async function doFind() {
      setError('');
      const inv = parseInventory(el('inv').value);
      const res = await fetchJson(api('/api/v1/cooking/find'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ inventory: inv, limit: 200 }),
      });

      const cookable = res.cookable || [];
      state.recipes = cookable;
      state.activeGroup = null;
      state.activeRecipe = null;
      state.activeRecipeData = null;
      renderGroupList();
      renderRecipeList();
      renderRecipeDetail(null);

      el('listTitle').textContent = `${t('cooking.list.cookable', 'Cookable')} (${cookable.length})`;
      el('out').innerHTML = res.note ? `<div class="muted">${res.note}</div>` : '';
    }

    async function doSimulate() {
      setError('');
      const slots = parseSlots(el('slots').value);
      const res = await fetchJson(api('/api/v1/cooking/simulate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slots: slots, return_top: 20 }),
      });

      if (!res.ok) {
        el('out').innerHTML = `<div class="err">${res.error || 'simulation_failed'} (total=${res.total ?? ''})</div>`;
        return;
      }

      const result = res.result || '(none)';
      const reason = res.reason || '';
      const cand = res.candidates || [];
      const lines = cand.length
        ? cand.map(c => `• ${renderItem(c.name)} (p=${escHtml(c.priority)}, w=${escHtml(c.weight)})`).join('<br/>')
        : '<span class="muted">No candidates (fallback).</span>';

      el('out').innerHTML = `
        <div class="ok">Result: ${renderItem(result)} <span class="muted">${reason ? '('+reason+')' : ''}</span></div>
        <div class="small muted" style="margin-top:6px;">Top matches</div>
        <div class="mono">${lines}</div>
      `;

      // auto-select result if exists
      if (res.recipe) {
        state.activeRecipe = result;
        state.activeRecipeData = res.recipe;
        if (state.activeRecipeData && !state.activeRecipeData.name) state.activeRecipeData.name = result;
        renderRecipeList();
        renderRecipeDetail(state.activeRecipeData);
      }
    }

    function toggleMode() {
      if (state.mode === 'foodtypes') state.mode = 'tags';
      else if (state.mode === 'tags') state.mode = 'all';
      else state.mode = 'foodtypes';
      loadGroups().catch(e => setError(String(e)));
    }

    // wire
    const navCraft = document.getElementById('navCraft');
    if (navCraft) navCraft.href = APP_ROOT + '/';

    const navCooking = document.getElementById('navCooking');
    if (navCooking) navCooking.href = APP_ROOT + '/cooking';

    const navCatalog = document.getElementById('navCatalog');
    if (navCatalog) navCatalog.href = APP_ROOT + '/catalog';


    const labelSel = el('labelMode');
    if (labelSel) {
      try { labelSel.value = state.labelMode || 'en'; } catch (e) {}
      labelSel.onchange = () => setLabelMode(labelSel.value).catch(e => setError(String(e)));
    }

    el('btnToggle').onclick = toggleMode;
    el('btnSearch').onclick = () => doSearch().catch(e => setError(String(e)));
    el('q').addEventListener('keydown', (e) => { if (e.key === 'Enter') doSearch().catch(err => setError(String(err))); });
    el('btnFind').onclick = () => doFind().catch(e => setError(String(e)));
    el('btnSim').onclick = () => doSimulate().catch(e => setError(String(e)));
    el('btnShowAll').onclick = () => showAll().catch(e => setError(String(e)));

    function initFromUrl() {
      const params = new URLSearchParams(window.location.search || '');
      const recipe = params.get('recipe');
      const q = params.get('q');
      if (recipe) {
        selectRecipe(recipe).catch(e => setError(String(e)));
        return;
      }
      if (q) {
        el('q').value = q;
        doSearch().catch(e => setError(String(e)));
      }
    }

    // init
    (async () => {
      try {
        await loadMeta();
        await ensureI18nNames(state.labelMode);
        await loadAssets();
        await loadGroups();
        await showAll();
        initFromUrl();
      } catch (e) {
        setError(String(e));
      }
    })();
  </script>
</body>
</html>
"""


def render_cooking_html(app_root: str = "") -> str:
    """Render the Cooking UI page."""
    from html import escape as _esc

    return _COOKING_TEMPLATE.replace("__WAGSTAFF_APP_ROOT__", _esc(app_root or ""))
