const navCraft = document.getElementById('navCraft');
if (navCraft) navCraft.href = APP_ROOT + '/craft';

const navCooking = document.getElementById('navCooking');
if (navCooking) navCooking.href = APP_ROOT + '/cooking';

const navFarming = document.getElementById('navFarming');
if (navFarming) navFarming.href = APP_ROOT + '/farming';

const navCatalog = document.getElementById('navCatalog');
if (navCatalog) navCatalog.href = APP_ROOT + '/catalog';

const isNarrow = () => window.matchMedia('(max-width: 860px)').matches;
const focusPanel = (id) => {
  if (!isNarrow()) return;
  const node = el(id);
  if (node) node.scrollIntoView({ behavior: 'smooth', block: 'start' });
};
const focusDetail = () => focusPanel('detailPanel');
const focusList = () => focusPanel('listPanel');
const backBtn = el('btnBackList');
if (backBtn) backBtn.onclick = () => focusList();
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
  const staticBaseRaw = String(cfg.static_base || '/static/data/icons');
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
  const navFarming = el('navFarming');
  if (navFarming) navFarming.textContent = t('nav.farming', 'Farming');
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
  setView(state.view);
  renderRecipeList();
  renderRecipeDetail(state.activeRecipeData);
  renderIngredientFilters();
  renderIngredientGrid();
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

function itemLabel(id) {
  const iid = String(id || '').trim();
  if (!iid) return '';
  const m = (state.assets && state.assets[iid]) ? state.assets[iid] : null;
  const enName = (m && m.name) ? m.name : iid;
  const zhName = getI18nName(iid);
  return resolveLabel(iid, enName, zhName);
}

function tagLabel(tag) {
  const key = String(tag || '').trim().toLowerCase();
  if (!key) return '';
  const en = (state.i18nTags && state.i18nTags.en && state.i18nTags.en[key]) ? state.i18nTags.en[key] : key;
  const zh = (state.i18nTags && state.i18nTags.zh && state.i18nTags.zh[key]) ? state.i18nTags.zh[key] : '';
  return resolveLabel(key, en || key, zh);
}

function tagSource(tag) {
  const key = String(tag || '').trim().toLowerCase();
  if (!key) return '';
  return (state.i18nTagsMeta && state.i18nTagsMeta.en && state.i18nTagsMeta.en[key])
    ? state.i18nTagsMeta.en[key]
    : ((state.i18nTagsMeta && state.i18nTagsMeta.zh && state.i18nTagsMeta.zh[key]) ? state.i18nTagsMeta.zh[key] : '');
}

function renderTagLabel(tag) {
  const label = tagLabel(tag);
  if (!label) return '';
  const src = (state.labelMode === 'id') ? tagSource(tag) : '';
  if (!src) return escHtml(label);
  return `${escHtml(label)} <span class="tag-source">${escHtml(src)}</span>`;
}


function renderGroupList() {
  const box = el('groupList');
  box.innerHTML = '';
  for (const g of state.groups) {
    const div = document.createElement('div');
    div.className = 'item' + (state.activeGroup === g.name ? ' active' : '');
    const labelHtml = (state.mode === 'tags')
      ? renderTagLabel(g.name)
      : escHtml(g.label || g.name);
    div.innerHTML = `<span class="name">${labelHtml}</span><span class="meta">${g.count ?? ''}</span>`;
    div.onclick = () => selectGroup(g.name);
    box.appendChild(div);
  }
}

function renderRecipeList() {
  const formulaEl = el('formula');
  if (formulaEl) formulaEl.textContent = '';
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
    return `<div class="line"><span>•</span><span>${renderItem(item)} <span class="mono">x${escHtml(amt)}</span>${extra}</span></div>`;
  }).join('');
  const tabLabel = String(rec.tab || '').replace('RECIPETABS.','');
  const techLabel = String(rec.tech || '').replace('TECH.','');
  const heroSubParts = [];
  if (tabLabel) heroSubParts.push(`Tab: ${tabLabel}`);
  if (techLabel) heroSubParts.push(`Tech: ${techLabel}`);
  const heroSub = heroSubParts.length ? heroSubParts.join(' | ') : '-';
  const heroMeta = [tabLabel, techLabel].filter(Boolean).map(v => `<span class="pill">${escHtml(v)}</span>`).join('');
  const heroMetaHtml = heroMeta || '<span class="muted">-</span>';
  const statRows = [
    {
      label: t('craft.detail.product', 'Product'),
      value: rec.product ? renderItem(rec.product) : '<span class="muted">-</span>',
    },
    {
      label: t('craft.detail.tech', 'Tech'),
      value: techLabel ? `<span class="mono">${escHtml(techLabel)}</span>` : '<span class="muted">-</span>',
    },
    {
      label: t('craft.detail.station', 'Station'),
      value: rec.station_tag ? `<span class="mono">${escHtml(rec.station_tag)}</span>` : '<span class="muted">-</span>',
    },
    {
      label: t('craft.detail.builder_skill', 'Builder skill'),
      value: rec.builder_skill ? `<span class="mono">${escHtml(rec.builder_skill)}</span>` : '<span class="muted">-</span>',
    },
  ];
  const statCards = statRows.map(row => `
    <div class="stat-card">
      <div class="stat-label">${escHtml(row.label)}</div>
      <div class="stat-value">${row.value}</div>
    </div>
  `).join('');

  el('detail').innerHTML = `
    <div class="detail-hero">
      <div>
        <div class="hero-title">${renderItem(rec.name)}</div>
        <div class="hero-sub">${escHtml(heroSub)}</div>
      </div>
      <div class="hero-meta">${heroMetaHtml}</div>
    </div>
    <div class="stat-grid">
      ${statCards}
    </div>
    <div class="section">
      <div class="section-title">${escHtml(t('craft.detail.filters', 'Filters'))}</div>
      <div class="chips">${filters || '<span class="muted">-</span>'}</div>
    </div>
    <div class="section">
      <div class="section-title">${escHtml(t('craft.detail.builder_tags', 'Builder tags'))}</div>
      <div class="chips">${tags || '<span class="muted">-</span>'}</div>
    </div>
    <div class="section">
      <div class="section-title">${escHtml(t('craft.detail.ingredients', 'Ingredients'))}</div>
      <div class="list-lines">${ings || '<span class="muted">-</span>'}</div>
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
  focusDetail();
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
