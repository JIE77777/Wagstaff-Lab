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
  if (!box) return;
  box.textContent = msg || '';
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
  const modeEncy = el('modeEncy');
  if (modeEncy) modeEncy.textContent = t('cooking.mode.encyclopedia', 'Encyclopedia');
  const modeExplore = el('modeExplore');
  if (modeExplore) modeExplore.textContent = t('cooking.mode.explore', 'Explore');
  const modeSim = el('modeSim');
  if (modeSim) modeSim.textContent = t('cooking.mode.simulate', 'Simulate');
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
  const input = el('q');
  if (input) input.placeholder = t('cooking.search.placeholder', input.placeholder || '');
  const btnShowAll = el('btnShowAll');
  if (btnShowAll) btnShowAll.textContent = t('btn.show_all', 'Show all');
  const btnExplore = el('btnExplore');
  if (btnExplore) btnExplore.textContent = t('btn.explore', 'Explore');
  const btnSim = el('btnSim');
  if (btnSim) btnSim.textContent = t('btn.simulate', 'Simulate');
  const toolModeLabel = el('toolModeLabel');
  if (toolModeLabel) toolModeLabel.textContent = t('cooking.tools.mode', 'Mode');
  const toolExplore = el('toolExplore');
  if (toolExplore) toolExplore.textContent = t('cooking.mode.explore', 'Explore');
  const toolSim = el('toolSim');
  if (toolSim) toolSim.textContent = t('cooking.mode.simulate', 'Simulate');
  const btnViewCards = el('btnViewCards');
  if (btnViewCards) btnViewCards.textContent = t('btn.view_cards', 'Cards');
  const btnViewDense = el('btnViewDense');
  if (btnViewDense) btnViewDense.textContent = t('btn.view_dense', 'Dense');
  const resultTitle = el('resultTitle');
  if (resultTitle) resultTitle.textContent = t('cooking.results.title', 'Results');
  const ingredientTitle = el('ingredientTitle');
  if (ingredientTitle) ingredientTitle.textContent = t('cooking.ingredients.title', 'Ingredient picker');
  const slotInputLabel = el('slotInputLabel');
  if (slotInputLabel) slotInputLabel.textContent = t('cooking.slots.manual', 'Manual input');
  const ingredientSearch = el('ingredientSearch');
  if (ingredientSearch) ingredientSearch.placeholder = t('cooking.ingredients.search', ingredientSearch.placeholder || 'Filter ingredients...');
  updateSlotUi();
}

function updateSlotUi() {
  const slotsHelp = el('slotsHelp');
  const slots = el('slots');
  const ingredientHint = el('ingredientHint');
  const ingredientClear = el('ingredientClear');
  if (state.view === 'explore') {
    if (slotsHelp) slotsHelp.textContent = t('cooking.slots.help_explore', 'Available ingredients (types only)');
    if (slots) slots.placeholder = t('cooking.slots.placeholder.explore', 'berries\ncarrot\nmonstermeat');
    if (ingredientHint) ingredientHint.textContent = t('cooking.ingredients.hint_explore', 'Click to toggle availability');
    if (ingredientClear) ingredientClear.textContent = t('cooking.ingredients.clear_explore', 'Clear selection');
  } else if (state.view === 'simulate') {
    if (slotsHelp) slotsHelp.textContent = t('cooking.slots.help_simulate', 'Cookpot slots (=4 items)');
    if (slots) slots.placeholder = t('cooking.slots.placeholder.simulate', 'carrot=2\nberries=1\nbutterflywings=1');
    if (ingredientHint) ingredientHint.textContent = t('cooking.ingredients.hint', 'Click to add, Shift/Alt to remove');
    if (ingredientClear) ingredientClear.textContent = t('cooking.ingredients.clear', 'Clear slots');
  } else {
    if (slotsHelp) slotsHelp.textContent = t('cooking.slots.help', 'Cookpot slots (<=4 for explore, =4 for simulate)');
    if (slots) slots.placeholder = t('cooking.slots.placeholder', slots.placeholder || '');
    if (ingredientHint) ingredientHint.textContent = t('cooking.ingredients.hint', 'Click to add, Shift/Alt to remove');
    if (ingredientClear) ingredientClear.textContent = t('cooking.ingredients.clear', 'Clear slots');
  }
  updateIngredientSourceHint();
  renderSlotPreview();
  updateIngredientSelection();
}

function updateIngredientSourceHint() {
  const hint = el('ingredientHint');
  if (!hint || !state.ingredientSource) return;
  const base = (state.view === 'explore')
    ? t('cooking.ingredients.hint_explore', 'Click to toggle availability')
    : t('cooking.ingredients.hint', 'Click to add, Shift/Alt to remove');
  const srcLabel = (state.ingredientSource === 'cooking_ingredients')
    ? t('cooking.ingredients.source.tags', 'ingredient tags')
    : (state.ingredientSource === 'items_fallback'
      ? t('cooking.ingredients.source.fallback', 'fallback tags')
      : t('cooking.ingredients.source.card', 'card ingredients'));
  hint.textContent = `${base} · ${srcLabel}`;
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
  if (typeof ensureI18nTags === 'function') {
    await ensureI18nTags(state.labelMode);
  }
  await ensureUiStrings(uiLang());
  applyUiStrings();
  renderGroupList();
  renderIngredientFilters();
  renderIngredientGrid();
  updateSlotUi();
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

function tagLabelPlain(tag) {
  const label = tagLabel(tag);
  if (!label) return '';
  if (state.labelMode !== 'id') return label;
  const src = tagSource(tag);
  return src ? `${label} [${src}]` : label;
}

function renderTagLabel(tag) {
  const label = tagLabel(tag);
  if (!label) return '';
  const src = (state.labelMode === 'id') ? tagSource(tag) : '';
  if (!src) return escHtml(label);
  return `${escHtml(label)} <span class="tag-source">${escHtml(src)}</span>`;
}


const PAGE_ROLE = (document.body && document.body.dataset && document.body.dataset.role)
  ? document.body.dataset.role
  : 'encyclopedia';
const PATHNAME = window.location && window.location.pathname ? window.location.pathname : '';
const PATH_VIEW = PATHNAME.endsWith('/cooking/simulate')
  ? 'simulate'
  : (PATHNAME.endsWith('/cooking/explore') ? 'explore' : '');

const state = {
  mode: 'foodtypes', // foodtypes | tags | all
  view: 'encyclopedia', // encyclopedia | explore | simulate
  listView: localStorage.getItem('ws_cooking_list') || 'card',
  results: null,
  groups: [],
  activeGroup: null,
  recipes: [],
  activeRecipe: null,
  activeRecipeData: null,
  assets: {},
  icon: null, // {mode, static_base, api_base}
  ingredients: [],
  ingredientFilter: 'all',
  ingredientQuery: '',
  ingredientSource: '',

  // label mode: en | zh | id (persisted in localStorage)
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

if (PAGE_ROLE === 'tool') {
  state.view = PATH_VIEW || (document.body && document.body.dataset ? (document.body.dataset.view || 'explore') : 'explore');
} else {
  state.view = 'encyclopedia';
}

const ING_CATEGORIES = [
  { key: 'all', label: () => t('cooking.ingredients.all', 'All'), tags: [] },
  { key: 'meat', label: () => t('cooking.ingredients.meat', 'Meat'), tags: ['meat'] },
  { key: 'veggie', label: () => t('cooking.ingredients.veggie', 'Veggie'), tags: ['veggie', 'vegetable'] },
  { key: 'fruit', label: () => t('cooking.ingredients.fruit', 'Fruit'), tags: ['fruit'] },
  { key: 'fish', label: () => t('cooking.ingredients.fish', 'Fish'), tags: ['fish'] },
  { key: 'egg', label: () => t('cooking.ingredients.egg', 'Egg'), tags: ['egg'] },
  { key: 'dairy', label: () => t('cooking.ingredients.dairy', 'Dairy'), tags: ['dairy'] },
  { key: 'sweetener', label: () => t('cooking.ingredients.sweetener', 'Sweetener'), tags: ['sweetener'] },
  { key: 'fungus', label: () => t('cooking.ingredients.fungus', 'Fungus'), tags: ['fungus', 'mushroom'] },
  { key: 'monster', label: () => t('cooking.ingredients.monster', 'Monster'), tags: ['monster'] },
  { key: 'inedible', label: () => t('cooking.ingredients.filler', 'Filler'), tags: ['inedible', 'filler'] },
  { key: 'other', label: () => t('cooking.ingredients.other', 'Other'), tags: [] },
];

const ING_GUESS = {
  meat: ['meat', 'morsel', 'drumstick', 'froglegs', 'batwing', 'smallmeat', 'monstermeat', 'leafymeat'],
  fish: ['fish', 'eel', 'salmon', 'tuna', 'perch', 'trout', 'barnacle'],
  egg: ['egg'],
  dairy: ['milk', 'butter', 'cheese'],
  sweetener: ['honey', 'sugar', 'nectar', 'syrup'],
  fruit: ['berries', 'berry', 'banana', 'pomegranate', 'watermelon', 'dragonfruit', 'durian', 'fig'],
  veggie: ['carrot', 'corn', 'pumpkin', 'eggplant', 'pepper', 'potato', 'tomato', 'onion', 'garlic', 'asparagus', 'cactus', 'kelp'],
  fungus: ['mushroom', 'cap'],
  monster: ['monster', 'durian'],
  inedible: ['twigs', 'ice'],
};

function setView(view) {
  state.view = String(view || 'encyclopedia');
  document.body.dataset.view = state.view;

  for (const btn of document.querySelectorAll('.mode-btn')) {
    const v = btn.getAttribute('data-mode');
    btn.classList.toggle('active', v === state.view);
  }

  const btnShowAll = el('btnShowAll');
  if (btnShowAll) btnShowAll.style.display = (state.view === 'encyclopedia') ? '' : 'none';
  const btnSearch = el('btnSearch');
  if (btnSearch) btnSearch.style.display = (state.view === 'encyclopedia') ? '' : 'none';
  const searchWrap = el('q') ? el('q').closest('.search') : null;
  if (searchWrap) searchWrap.style.display = (state.view === 'encyclopedia') ? '' : 'none';
  const btnViewCards = el('btnViewCards');
  if (btnViewCards) btnViewCards.style.display = (state.view === 'encyclopedia') ? 'none' : '';
  const btnViewDense = el('btnViewDense');
  if (btnViewDense) btnViewDense.style.display = (state.view === 'encyclopedia') ? 'none' : '';
  const btnExplore = el('btnExplore');
  if (btnExplore) btnExplore.style.display = (state.view === 'simulate') ? 'none' : '';
  const btnSim = el('btnSim');
  if (btnSim) btnSim.style.display = (state.view === 'explore') ? 'none' : '';
  const picker = el('ingredientPicker');
  if (picker) picker.style.display = (state.view === 'encyclopedia') ? 'none' : '';
  const toolExplore = el('toolExplore');
  if (toolExplore) toolExplore.classList.toggle('active', state.view === 'explore');
  const toolSim = el('toolSim');
  if (toolSim) toolSim.classList.toggle('active', state.view === 'simulate');

  const title = el('pageTitle');
  const sub = el('pageSub');
  if (title) {
    title.textContent = (state.view === 'simulate')
      ? t('cooking.title.simulate', 'Cooking Simulate')
      : (state.view === 'explore' ? t('cooking.title.explore', 'Cooking Explore') : t('cooking.title.encyclopedia', 'Cooking Lab'));
  }
  if (sub) {
    sub.textContent = (state.view === 'simulate')
      ? t('cooking.sub.simulate', 'Simulate results with full slots')
      : (state.view === 'explore' ? t('cooking.sub.explore', 'Explore recipes with partial slots') : t('cooking.sub.encyclopedia', 'Recipe rules and cookpot tools'));
  }

  if (state.view !== 'encyclopedia') {
    const listTitle = el('listTitle');
    if (listTitle) listTitle.textContent = (state.view === 'simulate')
      ? t('cooking.list.simulate', 'Simulate')
      : t('cooking.list.explore', 'Explore');
    const listCount = el('listCount');
    if (listCount) listCount.textContent = '';
  }

  updateSlotUi();
  renderRecipeList();
}

function setListView(view) {
  state.listView = String(view || 'card');
  try { localStorage.setItem('ws_cooking_list', state.listView); } catch (e) {}
  const btnViewCards = el('btnViewCards');
  if (btnViewCards) btnViewCards.classList.toggle('active', state.listView === 'card');
  const btnViewDense = el('btnViewDense');
  if (btnViewDense) btnViewDense.classList.toggle('active', state.listView === 'dense');
  renderRecipeList();
}

function formatMissing(missing) {
  const rows = Array.isArray(missing) ? missing : [];
  if (!rows.length) return '';
  const best = {};
  for (const m of rows) {
    const key = String(m.key || '').trim();
    const tpe = String(m.type || '').trim();
    const optKey = key || (Array.isArray(m.options) ? m.options.join('|') : '');
    if (!optKey && tpe !== 'name_any') continue;
    const id = `${tpe}:${optKey}`;
    const delta = Number(m.delta || 0);
    if (!best[id] || delta > Number(best[id].delta || 0)) {
      best[id] = m;
    }
  }
  const picked = Object.values(best);
  const typeRank = { name_any: 0, name: 1, tag: 2 };
  picked.sort((a, b) => {
    const ra = typeRank[String(a.type || '')] ?? 9;
    const rb = typeRank[String(b.type || '')] ?? 9;
    if (ra !== rb) return ra - rb;
    const da = Number(a.delta || 0);
    const db = Number(b.delta || 0);
    if (db !== da) return db - da;
    return String(a.key || '').localeCompare(String(b.key || ''));
  });
  const fmtNum = (num) => {
    const v = Number(num || 0);
    if (!Number.isFinite(v)) return '';
    const out = v.toFixed(1);
    return out.endsWith('.0') ? out.slice(0, -2) : out;
  };
  const parts = picked.slice(0, 4).map((m) => {
    const key = String(m.key || '').trim();
    const delta = Number(m.delta || 0);
    const dir = String(m.direction || '');
    if (m.type === 'name_sum') {
      const opts = Array.isArray(m.options) ? m.options : key.split('|');
      const label = opts.map((v) => itemLabel(v)).filter(Boolean).join(' | ');
      const minVal = (m.min !== undefined && m.min !== null) ? m.min : (m.required ?? 0);
      const tpl = t('cooking.missing.name_sum', 'sum of: {items} >= {min}');
      return label ? String(tpl || '')
        .replace('{items}', label)
        .replace('{min}', fmtNum(minVal))
        : (tpl || 'sum of');
    }
    if (m.type === 'name_any') {
      const opts = Array.isArray(m.options) ? m.options : key.split('|');
      const label = opts.map((v) => itemLabel(v)).filter(Boolean).join(' | ');
      const tpl = t('cooking.missing.name_any', 'any of: {items}');
      return label ? String(tpl || '').replace('{items}', label) : (tpl || 'any of');
    }
    if (!key) return '';
    const isName = m.type === 'name';
    const prefix = isName ? t('cooking.missing.item_prefix', 'item') : t('cooking.missing.tag_prefix', 'tag');
    const label = isName ? itemLabel(key) : tagLabelPlain(key);
    const base = `${prefix}:${label || key}`;
    if (dir === 'under' && delta > 0) return `${base} +${fmtNum(delta)}`;
    if (dir === 'over' && delta > 0) return `${base} -${fmtNum(delta)}`;
    if (dir === 'mismatch') return `${base} ≠ ${fmtNum(m.required || 0)}`;
    return base;
  }).filter(Boolean);
  if (!parts.length) return '';
  const suffix = rows.length > 4 ? ' ...' : '';
  return parts.join(', ') + suffix;
}

function _formatAttrValue(val) {
  if (val === null || val === undefined) return '';
  if (typeof val === 'number' && Number.isFinite(val)) {
    const out = val.toFixed(1);
    return out.endsWith('.0') ? out.slice(0, -2) : out;
  }
  if (typeof val === 'string') return val;
  if (typeof val === 'object' && val.value !== undefined) {
    const num = Number(val.value);
    if (Number.isFinite(num)) {
      const out = num.toFixed(1);
      return out.endsWith('.0') ? out.slice(0, -2) : out;
    }
  }
  return '';
}

function renderAttrPills(row) {
  const attrs = row && row.attrs ? row.attrs : {};
  const specs = [
    { key: 'hunger', label: 'H', title: t('label.hunger', 'Hunger') },
    { key: 'health', label: 'HP', title: t('label.health', 'Health') },
    { key: 'sanity', label: 'SAN', title: t('label.sanity', 'Sanity') },
    { key: 'perishtime', label: 'PER', title: t('label.perish', 'Perish') },
    { key: 'cooktime', label: 'COOK', title: t('label.cooktime', 'Cooktime') },
  ];
  const pills = [];
  for (const spec of specs) {
    const val = _formatAttrValue(attrs[spec.key]);
    if (!val) continue;
    pills.push(`<span class="attr-pill" title="${escHtml(spec.title)}">${escHtml(spec.label)} ${escHtml(val)}</span>`);
  }
  return pills.join('');
}

function renderResultList() {
  const box = el('results');
  if (!box) return;
  box.innerHTML = '';
  const recipeBox = el('recipeList');
  if (recipeBox) recipeBox.innerHTML = '';
  const listCount = el('listCount');
  if (listCount) listCount.textContent = '';
  const res = state.results;
  const formula = res && res.formula ? String(res.formula) : '';
  const formulaEl = el('formula');
  if (formulaEl) {
    formulaEl.textContent = formula ? `${t('label.formula', 'Formula')}: ${formula}` : '';
  }
  const mode = res && res._mode ? res._mode : state.view;
  const resultTitle = el('resultTitle');
  if (resultTitle) {
    const base = t('cooking.results.title', 'Results');
    if (mode === 'simulate') {
      resultTitle.textContent = `${base} - ${t('cooking.list.simulate', 'Simulate')}`;
    } else if (mode === 'explore') {
      resultTitle.textContent = `${base} - ${t('cooking.list.explore', 'Explore')}`;
    } else {
      resultTitle.textContent = base;
    }
  }
  if (!res) {
    box.innerHTML = `<div class="muted">${escHtml(t('cooking.results.empty', 'Run explore or simulate to see results.'))}</div>`;
    return;
  }

  const cookable = Array.isArray(res.cookable) ? res.cookable : [];
  const near = Array.isArray(res.near_miss) ? res.near_miss : [];
  const nearTiers = Array.isArray(res.near_miss_tiers) ? res.near_miss_tiers : [];

  const sections = [
    { title: t('cooking.results.cookable', 'Cookable'), items: cookable },
  ];
  if (nearTiers.length) {
    const label = (key) => {
      if (key === 'primary') return t('cooking.results.near_tier_primary', 'Near miss · current pool');
      if (key === 'filler') return t('cooking.results.near_tier_filler', 'Near miss · filler-heavy');
      return t('cooking.results.near_tier_secondary', 'Near miss · needs extra');
    };
    for (const tier of nearTiers) {
      const items = Array.isArray(tier.items) ? tier.items : [];
      sections.push({ title: label(String(tier.key || 'secondary')), items });
    }
  } else {
    sections.push({ title: t('cooking.results.near', 'Near miss'), items: near });
  }

  let animIdx = 0;
  for (const sec of sections) {
    const wrap = document.createElement('div');
    wrap.className = 'result-section';
    const header = document.createElement('div');
    header.className = 'result-header';
    header.innerHTML = `<div class="panel-title">${escHtml(sec.title)}</div><div class="small muted">${sec.items.length}</div>`;
    wrap.appendChild(header);

    if (!sec.items.length) {
      const empty = document.createElement('div');
      empty.className = 'muted small';
      empty.textContent = t('cooking.results.none', 'None');
      wrap.appendChild(empty);
      box.appendChild(wrap);
      continue;
    }

    if (state.listView === 'dense') {
      for (const row of sec.items) {
        const name = String(row.name || '').trim();
        if (!name) continue;
        const missing = formatMissing(row.missing || []) || t('label.ok', 'OK');
        const score = Number(row.score || 0);
        const rule = row.rule_mode ? String(row.rule_mode).toUpperCase() : '';
        const meta = `
          <span class="meta-pw">p=${escHtml(Number(row.priority || 0))} · w=${escHtml(Number(row.weight || 0))}</span>
          <span class="meta-s">· s=${escHtml(score.toFixed(1))}</span>
          ${rule ? `<span class="meta-rule">· ${escHtml(rule)}</span>` : ''}
        `;
        const div = document.createElement('div');
        const isMiss = Array.isArray(row.missing) && row.missing.length > 0;
        div.className = `result-row ${isMiss ? 'is-miss' : 'is-ok'}`;
        div.style.animationDelay = `${Math.min(animIdx * 0.03, 0.4)}s`;
        animIdx += 1;
        div.innerHTML = `<div>${renderItem(name)}<div class="small muted result-meta">${meta}</div></div>` +
          `<div class="result-missing">${escHtml(missing || '')}</div>`;
        div.onclick = () => selectRecipe(name);
        wrap.appendChild(div);
      }
      box.appendChild(wrap);
      continue;
    }

    const grid = document.createElement('div');
    grid.className = 'result-grid';
    for (const row of sec.items) {
      const name = String(row.name || '').trim();
      if (!name) continue;
      const missing = formatMissing(row.missing || []);
      const score = Number(row.score || 0);
      const rule = row.rule_mode ? String(row.rule_mode).toUpperCase() : '';
      const attrs = renderAttrPills(row);
      const card = document.createElement('div');
      const isMiss = Array.isArray(row.missing) && row.missing.length > 0;
      card.className = `result-card ${isMiss ? 'is-miss' : 'is-ok'}`;
      card.style.animationDelay = `${Math.min(animIdx * 0.03, 0.4)}s`;
      animIdx += 1;
      card.innerHTML = `
        <div>${renderItem(name)}</div>
        ${missing ? `<div class="result-missing">${escHtml(missing)}</div>` : `<div class="result-ok">${escHtml(t('label.ok', 'OK'))}</div>`}
        ${attrs ? `<div class="result-attrs">${attrs}</div>` : ''}
        <div class="result-meta">
          <span class="pill pill-pw">p=${escHtml(Number(row.priority || 0))}</span>
          <span class="pill pill-pw">w=${escHtml(Number(row.weight || 0))}</span>
          <span class="pill pill-s">s=${escHtml(score.toFixed(1))}</span>
          ${rule ? `<span class="pill pill-rule">${escHtml(rule)}</span>` : ''}
        </div>
      `;
      card.onclick = () => selectRecipe(name);
      grid.appendChild(card);
    }
    wrap.appendChild(grid);
    box.appendChild(wrap);
  }
}

function _guessTagsFromId(iid) {
  const out = new Set();
  const name = String(iid || '').toLowerCase();
  for (const key in ING_GUESS) {
    for (const needle of ING_GUESS[key]) {
      if (name.includes(needle)) {
        out.add(key);
        break;
      }
    }
  }
  return Array.from(out);
}

function _normalizeIngredient(raw) {
  if (!raw) return null;
  const id = String(raw.id || raw.item_id || raw.name || '').trim();
  if (!id) return null;
  const tags = new Set();
  const rawTags = raw.tags;
  if (Array.isArray(rawTags)) {
    for (const t of rawTags) tags.add(String(t).toLowerCase());
  } else if (rawTags && typeof rawTags === 'object') {
    for (const t of Object.keys(rawTags)) tags.add(String(t).toLowerCase());
  }
  const foodtype = raw.foodtype ? String(raw.foodtype).toLowerCase().replace('foodtype.', '') : '';
  if (foodtype) tags.add(foodtype);
  if (!tags.size) {
    for (const t of _guessTagsFromId(id)) tags.add(t);
  }
  return {
    id: id,
    tags: Array.from(tags),
    uses: Number(raw.uses || 0),
  };
}

function _ingredientLabel(item) {
  const m = (state.assets && state.assets[item.id]) ? state.assets[item.id] : null;
  const enName = (m && m.name) ? m.name : item.id;
  const zhName = getI18nName(item.id);
  return resolveLabel(item.id, enName, zhName);
}

function _ingredientMatchesCategory(item, key) {
  if (key === 'all') return true;
  if (key === 'other') {
    for (const cat of ING_CATEGORIES) {
      if (cat.key === 'all' || cat.key === 'other') continue;
      if (_ingredientMatchesCategory(item, cat.key)) return false;
    }
    return true;
  }
  const cat = ING_CATEGORIES.find(c => c.key === key);
  if (!cat) return true;
  return (cat.tags || []).some(tag => item.tags.includes(tag));
}

function _ingredientQueryMatch(item) {
  const q = String(state.ingredientQuery || '').trim().toLowerCase();
  if (!q) return true;
  const label = _ingredientLabel(item).toLowerCase();
  return String(item.id).toLowerCase().includes(q) || label.includes(q);
}

function renderIngredientFilters() {
  const box = el('ingredientFilters');
  if (!box) return;
  box.innerHTML = '';
  const items = state.ingredients || [];
  for (const cat of ING_CATEGORIES) {
    const count = items.filter(it => _ingredientMatchesCategory(it, cat.key)).length;
    if (cat.key === 'other' && !count) continue;
    const btn = document.createElement('button');
    btn.className = 'ingredient-filter' + (state.ingredientFilter === cat.key ? ' active' : '');
    btn.textContent = `${cat.label()}${count ? ' (' + count + ')' : ''}`;
    btn.onclick = () => {
      state.ingredientFilter = cat.key;
      renderIngredientFilters();
      renderIngredientGrid();
    };
    box.appendChild(btn);
  }
}

function renderIngredientGrid() {
  const grid = el('ingredientGrid');
  if (!grid) return;
  grid.innerHTML = '';
  if (!state.ingredients.length) {
    grid.innerHTML = `<div class="muted small">${escHtml(t('cooking.ingredients.empty', 'Ingredient index not ready.'))}</div>`;
    return;
  }
  const items = state.ingredients.filter(it => _ingredientMatchesCategory(it, state.ingredientFilter)).filter(_ingredientQueryMatch);
  if (!items.length) {
    grid.innerHTML = `<div class="muted small">${escHtml(t('cooking.ingredients.empty_filter', 'No ingredients match.'))}</div>`;
    return;
  }
  for (const item of items) {
    const btn = document.createElement('button');
    btn.className = 'ingredient-item';
    btn.setAttribute('data-id', item.id);
    const uses = item.uses ? `${item.uses} recipes` : '';
    const tagLabels = item.tags.map(tagLabelPlain).filter(Boolean);
    const tagsPlain = tagLabels.length ? tagLabels.join(', ') : '';
    const tagsHtml = item.tags.map(tag => renderTagLabel(tag)).filter(Boolean).join(', ');
    btn.title = `${item.id}${tagsPlain ? ' | ' + tagsPlain : ''}`;
    btn.innerHTML = `
      <div>${renderItem(item.id)}</div>
      <div class="ingredient-meta"><span>${escHtml(uses)}</span><span>${tagsHtml || ''}</span></div>
    `;
    btn.onclick = (e) => {
      if (state.view === 'explore') {
        toggleAvailable(item.id);
        return;
      }
      const delta = (e.shiftKey || e.altKey) ? -1 : 1;
      updateSlots(item.id, delta);
    };
    btn.oncontextmenu = (e) => {
      e.preventDefault();
      if (state.view === 'explore') {
        toggleAvailable(item.id, true);
        return;
      }
      updateSlots(item.id, -1);
    };
    grid.appendChild(btn);
  }
  updateIngredientSelection();
}

function formatSlots(inv) {
  const keys = Object.keys(inv || {}).filter(Boolean).sort();
  return keys.map(k => `${k}=${inv[k]}`).join('\n');
}

function parseAvailable(text) {
  const inv = parseSlots(text);
  return Object.keys(inv || {}).filter(Boolean);
}

function formatAvailable(items) {
  return (items || []).filter(Boolean).join('\n');
}

function updateIngredientSelection() {
  const grid = el('ingredientGrid');
  if (!grid) return;
  const selected = new Set(parseAvailable(el('slots')?.value || ''));
  for (const btn of grid.querySelectorAll('button.ingredient-item')) {
    const iid = btn.getAttribute('data-id') || '';
    btn.classList.toggle('active', selected.has(iid));
  }
}

function renderSlotPreview() {
  const box = el('slotPreview');
  if (!box) return;
  box.innerHTML = '';
  const inv = parseSlots(el('slots')?.value || '');
  const ids = Object.keys(inv || {}).filter(Boolean);
  if (!ids.length) {
    box.innerHTML = `<span class="muted small">${escHtml(t('cooking.slots.empty', 'No ingredients selected.'))}</span>`;
    return;
  }
  ids.sort();
  for (const iid of ids) {
    const count = Number(inv[iid] || 0);
    const btn = document.createElement('button');
    btn.className = 'slot-chip';
    btn.innerHTML = `
      ${renderItem(iid)}
      ${count > 1 ? `<span class="slot-count">x${escHtml(count)}</span>` : ''}
      <span class="slot-remove">x</span>
    `;
    btn.onclick = () => {
      if (state.view === 'explore') {
        toggleAvailable(iid, true);
      } else {
        updateSlots(iid, -count);
      }
    };
    box.appendChild(btn);
  }
}

function updateSlots(itemId, delta) {
  const slots = el('slots');
  if (!slots) return;
  const inv = parseSlots(slots.value);
  const cur = Number(inv[itemId] || 0);
  const next = cur + Number(delta || 0);
  if (next <= 0) delete inv[itemId];
  else inv[itemId] = Math.max(0, next);
  slots.value = formatSlots(inv);
  slots.dispatchEvent(new Event('input', { bubbles: true }));
}

function toggleAvailable(itemId, forceRemove) {
  const slots = el('slots');
  if (!slots) return;
  const items = parseAvailable(slots.value);
  const set = new Set(items);
  const iid = String(itemId || '').trim();
  if (!iid) return;
  if (forceRemove) set.delete(iid);
  else if (set.has(iid)) set.delete(iid);
  else set.add(iid);
  slots.value = formatAvailable(Array.from(set).sort());
  slots.dispatchEvent(new Event('input', { bubbles: true }));
}

async function loadIngredients() {
  try {
    const res = await fetchJson(api('/api/v1/cooking/ingredients'));
    const raw = Array.isArray(res.ingredients) ? res.ingredients : [];
    const items = raw.map(_normalizeIngredient).filter(Boolean);
    state.ingredients = items;
    state.ingredientSource = String(res.source || '');
  } catch (e) {
    state.ingredients = [];
    state.ingredientSource = '';
  }
  updateIngredientSourceHint();
  renderIngredientFilters();
  renderIngredientGrid();
}

function renderGroupList() {
  const box = el('groupList');
  if (!box) return;
  box.innerHTML = '';
  for (const g of state.groups) {
    const div = document.createElement('div');
    div.className = 'item' + (state.activeGroup === g.name ? ' active' : '');
    const label = g.label || g.name;
    const labelHtml = (state.mode === 'tags') ? renderTagLabel(g.name) : escHtml(label);
    div.innerHTML = `<span class="name">${labelHtml}</span><span class="meta">${g.count ?? ''}</span>`;
    div.onclick = () => selectGroup(g.name);
    box.appendChild(div);
  }
}

function renderRecipeList() {
  if (state.view !== 'encyclopedia') {
    renderResultList();
    return;
  }
  const formulaEl = el('formula');
  if (formulaEl) formulaEl.textContent = '';
  const out = el('out');
  if (out) out.textContent = '';
  const resultsBox = el('results');
  if (resultsBox) resultsBox.innerHTML = '';
  const resultTitle = el('resultTitle');
  if (resultTitle) resultTitle.textContent = t('cooking.results.title', 'Results');
  const box = el('recipeList');
  if (!box) return;
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

  const tags = (rec.tags || []).map(x => `<span class="chip">${renderTagLabel(x) || escHtml(x)}</span>`).join('');
  const card = (rec.card_ingredients || []).map(row => {
    const item = row[0];
    const cnt = row[1];
    return `<div class="line"><span>•</span><span>${renderItem(item)} <span class="mono">x${escHtml(cnt)}</span></span></div>`;
  }).join('');


  const rule = rec.rule || null;

  function renderRule(rule, includeTitle = true) {
    if (!rule) return '';
    const kind = escHtml(rule.kind || '');
    const expr = escHtml(rule.expr || '');
    const title = includeTitle
      ? `<div class="section-title">${escHtml(t('cooking.rule.title', 'Rule'))}${kind ? ` (${kind})` : ''}</div>`
      : '';

    return `
      ${title}
      <div class="mono small" style="white-space:pre-wrap; line-height:1.35;">${expr || '<span class="muted">-</span>'}</div>
    `;
  }

  const cardBody = card
    ? `<div class="list-lines">${card}</div>`
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
    const hasVal = (val !== null && val !== undefined && val !== '');
    const showExpr = expr && String(expr) !== String(val);
    const titleAttr = showExpr ? ` title="${escHtml(expr)}"` : '';

    const main = hasVal
      ? `<span class="mono"${titleAttr}>${escHtml(val)}</span>`
      : `<span class="mono">${escHtml(expr ?? '')}</span>`;

    const enabled = Boolean(state.tuningTraceEnabled);
    const key = traceKey(field);
    const btn = key
      ? `<button class="btn" data-cook-trace="${escHtml(field)}" ${enabled ? '' : 'disabled'} style="margin-left:6px; padding:2px 6px; font-size:11px;">${escHtml(t('btn.trace', 'Trace'))}</button>`
      : '';

    const details = tr
      ? `<details style="margin-top:6px;"><summary class="small muted">${escHtml(t('label.trace', 'Trace'))}</summary><pre>${escHtml(JSON.stringify(tr, null, 2))}</pre></details>`
      : '';

    const actions = btn ? `<span class="stat-actions">${btn}</span>` : '';
    return `<div class="stat-row">${main}${actions}</div>${details}`;
  }

  const extraRule = (card && rule)
    ? `<div style="margin-top:10px;">${renderRule(rule, true)}</div>`
    : '';
  const foodType = String(rec.foodtype || '').replace('FOODTYPE.','');
  const heroMeta = foodType ? `<span class="pill">${escHtml(foodType)}</span>` : '<span class="muted">-</span>';
  const statRows = [
    {
      label: t('label.priority', 'Priority'),
      value: `<span class="mono">${escHtml(rec.priority ?? '')}</span>`,
    },
    { label: t('label.hunger', 'Hunger'), value: renderStat('hunger') },
    { label: t('label.health', 'Health'), value: renderStat('health') },
    { label: t('label.sanity', 'Sanity'), value: renderStat('sanity') },
    { label: t('label.perish', 'Perish'), value: renderStat('perishtime') },
    { label: t('label.cooktime', 'Cooktime'), value: renderStat('cooktime') },
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
        <div class="hero-title">${renderItem(rec.name || '')}</div>
        <div class="hero-sub">${escHtml(foodType || '-')}</div>
      </div>
      <div class="hero-meta">${heroMeta}</div>
    </div>
    <div class="stat-grid">
      ${statCards}
    </div>
    <div class="section">
      <div class="section-title">${escHtml(t('label.tags', 'Tags'))}</div>
      <div class="chips">${tags || '<span class="muted">-</span>'}</div>
    </div>
    <div class="section">
      <div class="section-title">${escHtml(card ? t('cooking.card.ingredients', 'Card ingredients') : (rule ? t('cooking.rule.conditional', 'Recipe rule (conditional)') : t('cooking.card.ingredients', 'Card ingredients')))}</div>
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
    state.groups = (res.tags || []).map(t => ({
      name: t.name,
      label: tagLabel(t.name),
      count: t.count,
    }));
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
  focusDetail();
}

async function doSearch() {
  setError('');
  const q = el('q').value.trim();
  if (!q) {
    if (PAGE_ROLE === 'encyclopedia') {
      await showAll();
    }
    return;
  }
  setView('encyclopedia');
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
  setView('encyclopedia');
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

async function doExplore() {
  setError('');
  const available = parseAvailable(el('slots').value);
  const res = await fetchJson(api('/api/v1/cooking/explore'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ slots: {}, available: available, limit: 200 }),
  });

  if (!res.ok) {
    el('out').innerHTML = `<div class="err">${res.error || 'explore_failed'} (total=${res.total ?? ''})</div>`;
    return;
  }

  state.results = Object.assign({ _mode: 'explore' }, res);
  renderRecipeList();
  el('out').innerHTML = `<div class="small muted">${escHtml(t('cooking.results.summary', 'Explore results updated.'))}</div>`;
}

async function doSimulate() {
  setError('');
  const slots = parseSlots(el('slots').value);
  const total = Object.values(slots).reduce((acc, v) => acc + Number(v || 0), 0);
  if (total < 4) {
    await doExplore();
    return;
  }
  const res = await fetchJson(api('/api/v1/cooking/simulate'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ slots: slots, return_top: 20 }),
  });

  if (!res.ok) {
    el('out').innerHTML = `<div class="err">${res.error || 'simulation_failed'} (total=${res.total ?? ''})</div>`;
    return;
  }

  state.results = {
    _mode: 'simulate',
    formula: res.formula || '',
    cookable: res.cookable || [],
    near_miss: res.near_miss || [],
  };
  renderRecipeList();

  const result = res.result || '(none)';
  const reason = res.reason || '';
  el('out').innerHTML = `
    <div class="ok">Result: ${renderItem(result)} <span class="muted">${reason ? '('+reason+')' : ''}</span></div>
    <div class="small muted" style="margin-top:6px;">${escHtml(t('cooking.results.sim_summary', 'Candidates listed in results.'))}</div>
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

const btnToggle = el('btnToggle');
if (btnToggle) btnToggle.onclick = toggleMode;

const btnSearch = el('btnSearch');
if (btnSearch) btnSearch.onclick = () => doSearch().catch(e => setError(String(e)));
const searchInput = el('q');
if (searchInput) {
  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') doSearch().catch(err => setError(String(err)));
  });
}

const btnExplore = el('btnExplore');
if (btnExplore) btnExplore.onclick = () => {
  setView('explore');
  doExplore().catch(e => setError(String(e)));
};
const btnSim = el('btnSim');
if (btnSim) btnSim.onclick = () => {
  setView('simulate');
  doSimulate().catch(e => setError(String(e)));
};

const btnShowAll = el('btnShowAll');
if (btnShowAll) btnShowAll.onclick = () => showAll().catch(e => setError(String(e)));

const btnViewCards = el('btnViewCards');
if (btnViewCards) btnViewCards.onclick = () => setListView('card');
const btnViewDense = el('btnViewDense');
if (btnViewDense) btnViewDense.onclick = () => setListView('dense');

const toolExplore = el('toolExplore');
if (toolExplore) toolExplore.onclick = () => { window.location.href = APP_ROOT + '/cooking/explore'; };
const toolSim = el('toolSim');
if (toolSim) toolSim.onclick = () => { window.location.href = APP_ROOT + '/cooking/simulate'; };

const modeEncy = el('modeEncy');
if (modeEncy) modeEncy.onclick = () => { setView('encyclopedia'); showAll().catch(e => setError(String(e))); };
const modeExplore = el('modeExplore');
if (modeExplore) modeExplore.onclick = () => { setView('explore'); doExplore().catch(e => setError(String(e))); };
const modeSim = el('modeSim');
if (modeSim) modeSim.onclick = () => { setView('simulate'); doSimulate().catch(e => setError(String(e))); };

const ingSearch = el('ingredientSearch');
if (ingSearch) {
  ingSearch.addEventListener('input', () => {
    state.ingredientQuery = ingSearch.value.trim();
    renderIngredientGrid();
  });
}
const ingClear = el('ingredientClear');
if (ingClear) {
  ingClear.onclick = () => {
    const slots = el('slots');
    if (!slots) return;
    slots.value = '';
    slots.dispatchEvent(new Event('input', { bubbles: true }));
  };
}

let exploreTimer = null;
const slotsInput = el('slots');
if (slotsInput) {
  slotsInput.addEventListener('input', () => {
    renderSlotPreview();
    updateIngredientSelection();
    if (state.view === 'encyclopedia') {
      setView('explore');
    }
    if (exploreTimer) clearTimeout(exploreTimer);
    exploreTimer = setTimeout(() => {
      if (state.view === 'simulate') doSimulate().catch(e => setError(String(e)));
      else doExplore().catch(e => setError(String(e)));
    }, 400);
  });
}

function initFromUrl() {
  const params = new URLSearchParams(window.location.search || '');
  const recipe = params.get('recipe');
  const q = params.get('q');
  if (recipe) {
    selectRecipe(recipe).catch(e => setError(String(e)));
    return;
  }
  if (q && PAGE_ROLE === 'encyclopedia' && el('q')) {
    el('q').value = q;
    doSearch().catch(e => setError(String(e)));
  }
}

// init
(async () => {
  try {
    await loadMeta();
    await ensureI18nNames(state.labelMode);
    if (typeof ensureI18nTags === 'function') {
      await ensureI18nTags(state.labelMode);
    }
    await loadAssets();
    if (el('ingredientPicker') || el('ingredientGrid')) {
      await loadIngredients();
    }
    if (el('groupList')) {
      await loadGroups();
    }
    setView(state.view);
    setListView(state.listView);
    if (PAGE_ROLE === 'encyclopedia') {
      await showAll();
      initFromUrl();
    } else {
      renderRecipeDetail(null);
      renderResultList();
    }
  } catch (e) {
    setError(String(e));
  }
})();
