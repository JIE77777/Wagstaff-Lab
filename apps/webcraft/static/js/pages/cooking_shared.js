function setError(msg) {
  const box = el('err');
  if (!box) return;
  box.textContent = msg || '';
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

const ICON_ALIAS_IDS = new Set(['onion', 'onion_cooked', 'tomato', 'tomato_cooked']);

function _iconUrls(iid) {
  if (isVirtualIngredient(iid)) return { src: '', fallback: '' };
  const cfg = state.icon || {};
  const mode = String(cfg.mode || 'off');
  const key = String(iid || '');
  const enc = encodeURIComponent(key);
  const staticBaseRaw = String(cfg.static_base || '/static/data/icons');
  const staticBase = (APP_ROOT && staticBaseRaw.startsWith('/') && !staticBaseRaw.startsWith(APP_ROOT + '/'))
    ? (APP_ROOT + staticBaseRaw)
    : staticBaseRaw;
  const apiBase = String(cfg.api_base || '/api/v1/icon');
  const staticUrl = api(`${staticBase}/${enc}.png`);
  const apiUrl = api(`${apiBase}/${enc}.png`);

  if (ICON_ALIAS_IDS.has(key) && (mode === 'auto' || mode === 'dynamic')) {
    return { src: apiUrl, fallback: '' };
  }
  if (mode === 'dynamic') return { src: apiUrl, fallback: '' };
  if (mode === 'static') return { src: staticUrl, fallback: apiUrl };
  if (mode === 'auto') return { src: staticUrl, fallback: apiUrl };
  return { src: '', fallback: '' };
}

function isVirtualIngredient(iid) {
  if (!iid) return false;
  const set = state.virtualIngredientIds;
  if (!set || typeof set.has !== 'function') return false;
  return set.has(String(iid));
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
  if (s.includes('_')) return s.replace(/_/g, '');
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
  const btnAtlas = el('btnAtlas');
  if (btnAtlas) btnAtlas.textContent = t('cooking.title.encyclopedia', 'Cooking Atlas');
  const appNavCraft = el('appNavCraft');
  if (appNavCraft) {
    const label = appNavCraft.querySelector('.app-nav__label');
    if (label) label.textContent = t('nav.craft', 'Craft');
  }
  const appNavCooking = el('appNavCooking');
  if (appNavCooking) {
    const label = appNavCooking.querySelector('.app-nav__label');
    if (label) label.textContent = t('nav.cooking', 'Cooking');
  }
  const appNavCatalog = el('appNavCatalog');
  if (appNavCatalog) {
    const label = appNavCatalog.querySelector('.app-nav__label');
    if (label) label.textContent = t('nav.catalog', 'Catalog');
  }
  const label = el('labelModeLabel');
  if (label) label.textContent = t('label.mode', 'Label');
  const btnSearch = el('btnSearch');
  if (btnSearch) btnSearch.textContent = t('btn.search', 'Search');
  const btnToggle = el('btnToggle');
  if (btnToggle) btnToggle.textContent = t('btn.toggle', 'Toggle');
  const ingredientVirtualToggle = el('ingredientVirtualToggle');
  if (ingredientVirtualToggle) ingredientVirtualToggle.textContent = t('cooking.ingredients.virtual', 'Virtual ingredients');
  const ingredientVirtualTitle = el('ingredientVirtualTitle');
  if (ingredientVirtualTitle) ingredientVirtualTitle.textContent = t('cooking.ingredients.virtual', 'Virtual ingredients');
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
  const resultTitle = el('resultTitle');
  if (resultTitle) resultTitle.textContent = t('cooking.results.title', 'Results');
  const ingredientTitle = el('ingredientTitle');
  if (ingredientTitle) ingredientTitle.textContent = t('cooking.ingredients.title', 'Ingredient picker');
  const consoleTitle = el('consoleTitle');
  if (consoleTitle) consoleTitle.textContent = t('cooking.tools.console', 'Slot Console');
  const slotInputLabel = el('slotInputLabel');
  if (slotInputLabel) slotInputLabel.textContent = t('cooking.slots.manual', 'Manual input');
  const ingredientSearch = el('ingredientSearch');
  if (ingredientSearch) ingredientSearch.placeholder = t('cooking.ingredients.search', ingredientSearch.placeholder || 'Filter ingredients...');
  const resultSearch = el('resultSearch');
  if (resultSearch) resultSearch.placeholder = t('cooking.results.search', resultSearch.placeholder || 'Filter results...');
  const filterPrev = el('ingredientFilterPrev');
  const filterNext = el('ingredientFilterNext');
  if (filterPrev) {
    const label = t('cooking.ingredients.filter_prev', 'Prev tags');
    filterPrev.setAttribute('aria-label', label);
    filterPrev.title = label;
  }
  if (filterNext) {
    const label = t('cooking.ingredients.filter_next', 'Next tags');
    filterNext.setAttribute('aria-label', label);
    filterNext.title = label;
  }
  if (typeof updateSlotUi === 'function') updateSlotUi();
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
  if (typeof renderGroupList === 'function') renderGroupList();
  if (typeof renderIngredientFilters === 'function') renderIngredientFilters();
  if (typeof renderIngredientGrid === 'function') renderIngredientGrid();
  if (typeof updateSlotUi === 'function') updateSlotUi();
  if (typeof renderRecipeList === 'function') renderRecipeList();
  if (typeof renderResultList === 'function' && PAGE_ROLE === 'tool') renderResultList();
  if (typeof renderRecipeDetail === 'function') renderRecipeDetail(state.activeRecipeData);
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

const PAGE = (document.body && document.body.dataset && document.body.dataset.page)
  ? document.body.dataset.page
  : '';
const PAGE_ROLE = (document.body && document.body.dataset && document.body.dataset.role)
  ? document.body.dataset.role
  : 'encyclopedia';
const PATHNAME = window.location && window.location.pathname ? window.location.pathname : '';
const PATH_VIEW = PATHNAME.endsWith('/cooking/simulate')
  ? 'simulate'
  : '';

const state = {
  mode: 'foodtypes',
  view: 'encyclopedia',
  results: null,
  groups: [],
  activeGroup: null,
  recipes: [],
  activeRecipe: null,
  activeRecipeData: null,
  assets: {},
  icon: null,
  ingredients: [],
  ingredientIndex: {},
  ingredientFilter: 'all',
  ingredientQuery: '',
  ingredientSource: '',
  virtualIngredientIds: new Set(),
  showVirtualIngredients: false,
  resultQuery: '',

  labelMode: localStorage.getItem('ws_label_mode') || 'en',
  i18n: null,
  i18nNames: {},
  i18nLoaded: {},
  i18nTags: {},
  i18nTagsMeta: {},
  i18nTagsLoaded: {},
  tuningTrace: {},
  tuningTraceEnabled: false,
  uiStrings: {},
  uiLoaded: {},
};

if (PAGE_ROLE === 'tool') {
  state.view = PATH_VIEW || (document.body && document.body.dataset ? (document.body.dataset.view || 'simulate') : 'simulate');
  if (state.view !== 'simulate') state.view = 'simulate';
} else {
  state.view = 'encyclopedia';
}

function setView(view) {
  state.view = String(view || 'encyclopedia');
  document.body.dataset.view = state.view;
  const btnSearch = el('btnSearch');
  if (btnSearch) btnSearch.style.display = (state.view === 'encyclopedia') ? '' : 'none';
  const searchWrap = el('q') ? el('q').closest('.search') : null;
  if (searchWrap) searchWrap.style.display = (state.view === 'encyclopedia') ? '' : 'none';
  const picker = el('ingredientPicker');
  if (picker) picker.style.display = (state.view === 'encyclopedia') ? 'none' : '';

  const title = el('pageTitle');
  const sub = el('pageSub');
  if (title) {
    title.textContent = (state.view === 'simulate')
      ? t('cooking.title.simulate', 'Cooking Simulate')
      : t('cooking.title.encyclopedia', 'Cooking Lab');
  }
  if (sub) {
    sub.textContent = (state.view === 'simulate')
      ? t('cooking.sub.simulate', 'Simulate results with full slots')
      : t('cooking.sub.encyclopedia', 'Recipe rules and cookpot tools');
  }

  if (state.view !== 'encyclopedia') {
    const listTitle = el('listTitle');
    if (listTitle) listTitle.textContent = t('cooking.list.simulate', 'Simulate');
    const listCount = el('listCount');
    if (listCount) listCount.textContent = '';
  }

  if (typeof updateSlotUi === 'function') updateSlotUi();
  if (PAGE_ROLE === 'tool') {
    if (state.results && typeof renderResultList === 'function') renderResultList();
  } else if (typeof renderRecipeList === 'function') {
    renderRecipeList();
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

const navCraft = document.getElementById('navCraft');
if (navCraft) navCraft.href = APP_ROOT + '/craft';

const navCooking = document.getElementById('navCooking');
if (navCooking) navCooking.href = APP_ROOT + '/cooking';

const navCatalog = document.getElementById('navCatalog');
if (navCatalog) navCatalog.href = APP_ROOT + '/catalog';

const appNavCraft = el('appNavCraft');
if (appNavCraft) appNavCraft.href = APP_ROOT + '/craft';
const appNavCooking = el('appNavCooking');
if (appNavCooking) appNavCooking.href = APP_ROOT + '/';
const appNavCatalog = el('appNavCatalog');
if (appNavCatalog) appNavCatalog.href = APP_ROOT + '/catalog';
if (appNavCraft) appNavCraft.classList.toggle('active', PAGE === 'craft');
if (appNavCooking) appNavCooking.classList.toggle('active', PAGE === 'cooking');
if (appNavCatalog) appNavCatalog.classList.toggle('active', PAGE === 'catalog');

const btnAtlas = el('btnAtlas');
if (btnAtlas) btnAtlas.href = APP_ROOT + '/cooking';

const labelSel = el('labelMode');
if (labelSel) {
  try { labelSel.value = state.labelMode || 'en'; } catch (e) {}
  labelSel.onchange = () => setLabelMode(labelSel.value).catch(e => setError(String(e)));
}

const COOKING_BOOT = (async () => {
  await loadMeta();
  await ensureI18nNames(state.labelMode);
  if (typeof ensureI18nTags === 'function') {
    await ensureI18nTags(state.labelMode);
  }
  await loadAssets();
})();
window.COOKING_BOOT = COOKING_BOOT;
