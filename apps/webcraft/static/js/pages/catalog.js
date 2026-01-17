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

function setError(msg) {
  const box = el('err');
  if (!msg) { box.style.display = 'none'; box.textContent = ''; return; }
  box.style.display = 'block';
  box.textContent = String(msg);
}

function hasCjk(text) {
  return /[\u4e00-\u9fff]/.test(String(text || ''));
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
  i18nTags: {},       // {lang: {tag: label}}
  i18nTagsMeta: {},   // {lang: {tag: source}}
  i18nTagsLoaded: {}, // {lang: true}
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
const PAGE_SIZE = 400;
let catalogTotal = 0;
let searchTotal = 0;
let listMode = 'all';
let loadingPage = false;
let loadedKeys = new Set();

function _iconUrls(iid) {
  const cfg = icon || {};
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

async function ensureI18nTags(mode) {
  const m = String(mode || 'en');
  if (m === 'id') return;
  const lang = (m === 'zh') ? 'zh' : 'en';
  if (state.i18nTagsLoaded && state.i18nTagsLoaded[lang]) return;
  const enabled = Boolean(state.i18n && state.i18n.enabled);
  if (!enabled) return;
  try {
    const res = await fetchJson(api(`/api/v1/i18n/tags/${encodeURIComponent(lang)}`));
    state.i18nTags[lang] = res.tags || {};
    state.i18nTagsMeta[lang] = res.meta || {};
    state.i18nTagsLoaded[lang] = true;
  } catch (e) {
    state.i18nTags[lang] = {};
    state.i18nTagsMeta[lang] = {};
    state.i18nTagsLoaded[lang] = false;
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
  await runSearch(q);
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
  const iconHtml = iconHtmlFor(iid, 30);
  return `<span class="item">${iconHtml}<span>${escHtml(label)}</span></span>`;
}

function listKeys() {
  return allKeys;
}

async function runSearch(q) {
  const query = String(q || '').trim();
  if (!query) {
    listMode = 'all';
    searchTotal = 0;
    renderList(listKeys());
    return;
  }
  listMode = 'search';
  try {
    const res = await fetchJson(api(`/api/v1/catalog/search?q=${encodeURIComponent(query)}&limit=800`));
    const items = res.items || [];
    searchTotal = Number(res.total || res.count || items.length);
    applyCatalogItems(items, false);
    const keys = [];
    items.forEach((it) => {
      const iid = String(it.id || '').trim();
      if (iid) keys.push(iid);
    });
    renderList(keys);
  } catch (e) {
    setError(String(e));
  }
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

    const iconHtml = iconHtmlFor(k, 34);
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
  const total = (listMode === 'search')
    ? (searchTotal || viewKeys.length)
    : (catalogTotal || allKeys.length);
  el('stats').textContent = `${total} items. Showing ${shown}/${viewKeys.length}.`;
}

function renderList(keys) {
  viewKeys = (keys || []).slice();
  renderPos = 0;
  const box = el('list');
  box.innerHTML = '';
  if (!viewKeys.length) {
    box.innerHTML = '<div class="pbody muted">No results.</div>';
    const total = (listMode === 'search')
      ? (searchTotal || 0)
      : (catalogTotal || allKeys.length);
    el('stats').textContent = `${total} items. Showing 0/0.`;
    return;
  }
  appendListChunk();
}

async function maybeLoadMore() {
  if (listMode !== 'all') return;
  if (loadingPage) return;
  if (catalogTotal && allKeys.length >= catalogTotal) return;
  const before = allKeys.length;
  await loadCatalogPage(allKeys.length);
  if (allKeys.length > before) {
    viewKeys = listKeys();
  }
}

function installInfiniteScroll() {
  const box = el('list');
  box.addEventListener('scroll', () => {
    if (box.scrollTop + box.clientHeight >= box.scrollHeight - 200) {
      appendListChunk();
      maybeLoadMore().then(() => appendListChunk());
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
  const lines = arr.slice(0, 80).map(n => `<div class="line"><span>•</span><span><a class="mono" href="${hrefFn(n)}">${escHtml(n)}</a></span></div>`).join('');
  const more = arr.length > 80 ? `<div class="muted">… +${arr.length-80} more</div>` : '';
  return `<div class="list-lines">${lines}${more}</div>`;
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
  return `<div class="list-lines">${lines}${more}</div>`;
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
  const iconHtml = iconHtmlFor(q, 64);

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
    const titleAttr = showExpr ? ` title="${escHtml(expr)}"` : '';
    const key = `cooking:${cookRec.name || q}:${field}`;
    const canTrace = Boolean(key);
    const enabled = Boolean(state.tuningTraceEnabled);
    const btn = canTrace
      ? `<button class="btn" data-cook-trace="${escHtml(field)}" ${enabled ? '' : 'disabled'} style="margin-left:6px; padding:2px 6px; font-size:11px;">${escHtml(t('btn.trace', 'Trace'))}</button>`
      : '';
    const details = tr
      ? `<details style="margin-top:4px;"><summary class="small muted">${escHtml(t('label.trace', 'Trace'))}</summary><pre>${escHtml(JSON.stringify(tr, null, 2))}</pre></details>`
      : '';
    const main = (val !== null && val !== undefined && val !== '')
      ? `<span class="mono"${titleAttr}>${escHtml(val ?? '')}</span>`
      : `<span class="mono">${escHtml(expr ?? '')}</span>`;
    const actions = btn ? `<span class="stat-actions">${btn}</span>` : '';
    return `<div class="stat-row">${main}${actions}</div>${details}`;
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
    recharge_percent: 'Recharge Percent',
    recharge_charge: 'Recharge Charge',
    equip_slot: 'Equip Slot',
    equip_walk_speed_mult: 'Equip Walk Speed Mult',
    equip_run_speed_mult: 'Equip Run Speed Mult',
    equip_restricted_tag: 'Equip Restricted Tag',
    equip_stack: 'Equip Stack',
    equip_insulated: 'Equip Insulated',
    equip_moisture: 'Equip Moisture',
    equip_moisture_max: 'Equip Moisture Max',
    equip_magic_dapperness: 'Equip Magic Dapperness',
    heat: 'Heat',
    heat_radius: 'Heat Radius',
    heat_radius_cutoff: 'Heat Radius Cutoff',
    heat_falloff: 'Heat Falloff',
    heater_exothermic: 'Heater Exothermic',
    heater_endothermic: 'Heater Endothermic',
    equipped_heat: 'Equipped Heat',
    carried_heat_multiplier: 'Carried Heat Mult',
    heat_rate: 'Heat Rate',
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
    const value = `<span class="mono">${escHtml(val ?? '')}</span>${showExpr ? ` <span class="small muted mono">${escHtml(expr)}</span>` : ''}${btn}${details}`;
    return `
      <div class="stat-card">
        <div class="stat-label">${escHtml(label)}</div>
        <div class="stat-value">${value}</div>
      </div>
    `;
  }

  function renderStats(statsObj) {
    const entries = Object.entries(statsObj || {});
    if (!entries.length) return '<span class="muted">-</span>';
    return `<div class="stat-grid">${entries.map(([k, v]) => renderStatRow(k, v)).join('')}</div>`;
  }

  const cookBrief = cookRec ? `
    <div class="section">
      <div class="section-title">${escHtml(t('catalog.section.cooking_recipe', 'Cooking recipe'))}</div>
      <div class="list-lines">
        <div class="line"><span>•</span><span><a class="mono" href="${recipeLinkCooking(cookRec.name || q)}">${escHtml(cookRec.name || q)}</a></span></div>
      </div>
      <div class="stat-grid" style="margin-top:8px;">
        <div class="stat-card"><div class="stat-label">${escHtml(t('label.hunger', 'Hunger'))}</div><div class="stat-value">${renderCookStatRow('hunger')}</div></div>
        <div class="stat-card"><div class="stat-label">${escHtml(t('label.health', 'Health'))}</div><div class="stat-value">${renderCookStatRow('health')}</div></div>
        <div class="stat-card"><div class="stat-label">${escHtml(t('label.sanity', 'Sanity'))}</div><div class="stat-value">${renderCookStatRow('sanity')}</div></div>
        <div class="stat-card"><div class="stat-label">${escHtml(t('label.perish', 'Perish'))}</div><div class="stat-value">${renderCookStatRow('perishtime')}</div></div>
        <div class="stat-card"><div class="stat-label">${escHtml(t('label.cooktime', 'Cooktime'))}</div><div class="stat-value">${renderCookStatRow('cooktime')}</div></div>
      </div>
    </div>
  ` : `
    <div class="section">
      <div class="section-title">${escHtml(t('catalog.section.cooking_recipe', 'Cooking recipe'))}</div>
      <span class="muted">-</span>
    </div>
  `;

  const analyzerEnabled = Boolean(meta.analyzer_enabled);
  const analyzerBox = analyzerEnabled ? `
    <div class="section">
      <div class="row" style="justify-content:space-between;">
        <div class="section-title">${escHtml(t('catalog.section.prefab_analysis', 'Prefab analysis'))}</div>
        <button class="btn" id="btnAnalyze">${escHtml(t('btn.analyze', 'Analyze'))}</button>
      </div>
      <div class="muted small">${escHtml(t('catalog.prefab_analysis_help', 'Uses server-side LuaAnalyzer (prefab parser). Availability depends on how the server was started.'))}</div>
      <div id="analysis"></div>
    </div>
  ` : `
    <div class="section">
      <div class="section-title">${escHtml(t('catalog.section.prefab_analysis', 'Prefab analysis'))}</div>
      <div class="muted">${escHtml(t('catalog.prefab_analysis_disabled', 'Analyzer disabled. Start server with enable_analyzer=true and provide scripts_dir / scripts_zip (or dst_root).'))}</div>
    </div>
  `;

  el('detail').innerHTML = `
    <div class="detail-hero">
      <div class="row" style="align-items:center; gap:12px;">
        ${iconHtml}
        <div>
          <div class="hero-title">${escHtml(label)}</div>
          <div class="hero-sub mono">${escHtml(q)}</div>
        </div>
      </div>
      <div class="hero-meta">${renderChips(kindRow, 'mono')}</div>
    </div>

    <div class="section">
      <div class="section-title">${escHtml(t('catalog.section.stats', 'Stats'))}</div>
      ${renderStats(stats)}
    </div>

    <div class="section">
      <div class="section-title">${escHtml(t('catalog.section.categories', 'Categories'))}</div>
      <div class="chips">${renderChips(categories, '')}</div>
    </div>

    <div class="section">
      <div class="section-title">${escHtml(t('catalog.section.behaviors', 'Behaviors'))}</div>
      <div class="chips">${renderChips(behaviors, '')}</div>
    </div>

    <div class="section">
      <div class="section-title">${escHtml(t('catalog.section.components', 'Components'))}</div>
      <div class="chips">${renderChips(components, 'mono')}</div>
    </div>

    <div class="section">
      <div class="section-title">${escHtml(t('catalog.section.tags', 'Tags'))}</div>
      <div class="chips">${renderChips(tags, 'mono')}</div>
    </div>

    <div class="section">
      <div class="section-title">${escHtml(t('catalog.section.brains', 'Brains'))}</div>
      <div class="chips">${renderChips(brains, 'mono')}</div>
    </div>

    <div class="section">
      <div class="section-title">${escHtml(t('catalog.section.stategraphs', 'Stategraphs'))}</div>
      <div class="chips">${renderChips(stategraphs, 'mono')}</div>
    </div>

    <div class="section">
      <div class="section-title">${escHtml(t('catalog.section.helpers', 'Helpers'))}</div>
      <div class="chips">${renderChips(helpers, 'mono')}</div>
    </div>

    <div class="section">
      <div class="section-title">${escHtml(t('catalog.section.prefab_files', 'Prefab files'))}</div>
      ${renderMonoLines(prefabFiles, 6)}
    </div>

    <div class="section">
      <div class="section-title">${escHtml(t('catalog.section.assets', 'Assets'))}</div>
      <div class="list-lines">
        <div class="mono">${escHtml(t('label.icon', 'icon'))}: ${escHtml(iconPath || '-')}</div>
        <div class="mono">${escHtml(t('label.atlas', 'atlas'))}: ${escHtml(atlas || '-')}</div>
        <div class="mono">${escHtml(t('label.image', 'image'))}: ${escHtml(image || '-')}</div>
      </div>
    </div>

    ${prefabAssets && prefabAssets.length ? `<div class="section"><details><summary class="section-title">${escHtml(t('catalog.section.prefab_assets', 'Prefab assets (raw)'))}</summary><pre>${escHtml(JSON.stringify(prefabAssets, null, 2))}</pre></details></div>` : ''}

    <div class="section">
      <div class="section-title">${escHtml(t('catalog.section.craft_produced', 'Craft: produced by'))}</div>
      ${renderRecipeList(craft.produced_by, recipeLinkCraft)}
    </div>

    <div class="section">
      <div class="section-title">${escHtml(t('catalog.section.craft_used', 'Craft: used as ingredient'))}</div>
      ${renderRecipeList(craft.used_in, recipeLinkCraft)}
    </div>

    ${cookBrief}

    <div class="section">
      <div class="section-title">${escHtml(t('catalog.section.cooking_used', 'Cooking: used as card ingredient'))}</div>
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
  focusDetail();
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

function applyCatalogItems(items, updateList) {
  const trackList = (updateList !== false);
  (items || []).forEach((it) => {
    const iid = String(it.id || '').trim();
    if (!iid) return;
    if (trackList) {
      if (loadedKeys.has(iid)) return;
      loadedKeys.add(iid);
    }
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
    if (trackList) allKeys.push(iid);
  });
}

async function loadCatalogPage(offset) {
  if (loadingPage) return [];
  loadingPage = true;
  try {
    const res = await fetchJson(api(`/api/v1/catalog/index?offset=${offset}&limit=${PAGE_SIZE}`));
    icon = res.icon || icon;
    catalogTotal = Number(res.total || res.count || 0);
    const items = res.items || [];
    applyCatalogItems(items, true);
    return items;
  } finally {
    loadingPage = false;
  }
}

async function loadAssets() {
  assets = {};
  allKeys = [];
  loadedKeys = new Set();
  listMode = 'all';
  searchTotal = 0;
  await loadCatalogPage(0);
  const total = catalogTotal || allKeys.length;
  el('stats').textContent = `${total} items. Showing 0/0.`;
}

async function initFromUrl() {
  const params = new URLSearchParams(window.location.search || '');
  const item = params.get('item');
  const q = params.get('q');
  if (q) {
    el('q').value = q;
    await runSearch(q);
    return;
  }
  if (item) {
    el('q').value = item;
    await runSearch(item);
    openItem(item).catch(e => setError(String(e)));
  }
}

el('btnSearch').onclick = () => {
  setError('');
  const q = el('q').value;
  runSearch(q).catch(e => setError(String(e)));
};

const btnAll = el('btnAll');
if (btnAll) {
  btnAll.onclick = () => {
    try {
      setError('');
      el('q').value = '';
      listMode = 'all';
      searchTotal = 0;
      renderList(listKeys());
    } catch (e) { setError(String(e)); }
  };
}

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
    await initFromUrl();
  } catch (e) {
    setError(String(e));
  }
})();
