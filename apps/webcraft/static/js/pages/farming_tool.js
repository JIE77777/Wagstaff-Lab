const PAGE = (document.body && document.body.dataset && document.body.dataset.page)
  ? document.body.dataset.page
  : '';
const PAGE_ROLE = (document.body && document.body.dataset && document.body.dataset.role)
  ? document.body.dataset.role
  : '';

const COLOR_BANK = [
  'var(--seed-1)',
  'var(--seed-2)',
  'var(--seed-3)',
  'var(--seed-4)',
  'var(--seed-5)',
  'var(--seed-6)',
];
const MAX_SELECTED_CHIPS = 4;
const RATIO_MIX_KEY = '__mix__';
const FIXED_TILE_KEYS = ['1x1', '1x2'];
const FIXED_PIT_MODES = ['8', '9', '10'];

const state = {
  labelMode: localStorage.getItem('ws_label_mode') || 'en',
  mode: localStorage.getItem('ws_farming_mode') || 'fixed',
  i18n: null,
  i18nNames: {},
  i18nLoaded: {},
  uiStrings: {},
  uiLoaded: {},
  assets: {},
  icon: null,
  defs: null,
  fixed: null,
  plants: [],
  tuning: {},
  seasons: [],
  consumeMax: [0, 0, 0],
  selected: new Set(),
  ratioFilter: '',
  results: [],
  fixedFilter: {
    manual: false,
  },
  plot: {
    tileW: 1,
    tileH: 2,
    pitModes: new Set(['9', '10']),
    activePattern: '9',
  },
  activePlanIndex: null,
};

function setError(msg) {
  const box = el('err');
  if (!box) return;
  if (!msg) {
    box.textContent = '';
    return;
  }
  box.textContent = String(msg);
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

function applyModeUI() {
  const mode = ['fixed', 'explore', 'single'].includes(state.mode) ? state.mode : 'fixed';
  if (mode !== state.mode) state.mode = mode;
  if (document.body) {
    document.body.dataset.farmingMode = mode;
  }
  const buttons = document.querySelectorAll('.mode-btn');
  buttons.forEach((btn) => {
    const mode = btn.getAttribute('data-mode');
    btn.classList.toggle('active', mode === state.mode);
  });
  const note = el('modeNote');
  if (note) {
  if (state.mode === 'fixed') {
    note.textContent = t('farming.mode.note.fixed', 'Nutrient complement: perfect complement layouts only.');
    } else if (state.mode === 'single') {
      note.textContent = t('farming.mode.note.single', 'Single nutrient: group crops by missing fertilizer.');
    } else {
      note.textContent = t('farming.mode.note.explore', 'Explore: search mixed layouts by deficit ranking.');
    }
  }
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
  const appNavFarming = el('appNavFarming');
  if (appNavFarming) {
    const label = appNavFarming.querySelector('.app-nav__label');
    if (label) label.textContent = t('nav.farming', 'Farming');
  }
  const appNavCatalog = el('appNavCatalog');
  if (appNavCatalog) {
    const label = appNavCatalog.querySelector('.app-nav__label');
    if (label) label.textContent = t('nav.catalog', 'Catalog');
  }
  const label = el('labelModeLabel');
  if (label) label.textContent = t('label.mode', 'Label');
  const pageTitle = el('pageTitle');
  if (pageTitle) pageTitle.textContent = t('farming.title', 'Farming Matrix');
  const pageSub = el('pageSub');
  if (pageSub) pageSub.textContent = t('farming.sub', 'Mix crops to balance nutrients, water, and family clusters.');
  const seedTitle = el('seedTitle');
  if (seedTitle) seedTitle.textContent = t('farming.seeds.title', 'Seed Ledger');
  const controlTitle = el('controlTitle');
  if (controlTitle) controlTitle.textContent = t('farming.controls.title', 'Planner Console');
  const modeButtons = document.querySelectorAll('.mode-btn');
  modeButtons.forEach((btn) => {
    const mode = btn.getAttribute('data-mode');
    if (mode === 'fixed') btn.textContent = t('farming.mode.fixed', 'Nutrient Complement');
    if (mode === 'explore') btn.textContent = t('farming.mode.explore', 'Explore');
    if (mode === 'single') btn.textContent = t('farming.mode.single', 'Single Nutrient');
  });
  const resultTitle = el('resultTitle');
  if (resultTitle) resultTitle.textContent = t('farming.results.title', 'Plan Results');
  const legend = el('nutrientLegend');
  if (legend) legend.textContent = t('farming.legend.nutrients', 'N1 / N2 / N3 are the three soil nutrient channels.');
  const plantClear = el('plantClear');
  if (plantClear) plantClear.textContent = t('farming.plants.clear', 'Clear');
  const plotLabel = el('plotLabel');
  if (plotLabel) plotLabel.textContent = t('farming.plot.label', 'Plot tiles');
  const pitLabel = el('pitLabel');
  if (pitLabel) pitLabel.textContent = t('farming.pit.label', 'Pit pattern');
  const seasonLabel = el('seasonLabel');
  if (seasonLabel) seasonLabel.textContent = t('farming.season.label', 'Season filter');
  const maxKindsLabel = el('maxKindsLabel');
  if (maxKindsLabel) maxKindsLabel.textContent = t('farming.max_kinds.label', 'Max plant kinds');
  const topNLabel = el('topNLabel');
  if (topNLabel) topNLabel.textContent = t('farming.top_n.label', 'Top results');
  const plotPreviewLabel = el('plotPreviewLabel');
  if (plotPreviewLabel) plotPreviewLabel.textContent = t('farming.plot.preview', 'Plot preview');
  const selectedLabel = el('selectedLabel');
  if (selectedLabel) selectedLabel.textContent = t('farming.selected.label', 'Selected plants');
  const btnGenerate = el('btnGenerate');
  if (btnGenerate) btnGenerate.textContent = t('farming.btn.generate', 'Generate plans');
  const btnReset = el('btnReset');
  if (btnReset) btnReset.textContent = t('farming.btn.reset', 'Reset');
}

function setToolViewportVars() {
  if (PAGE_ROLE !== 'tool') return;
  const viewport = window.visualViewport;
  const h = (viewport && viewport.height) || window.innerHeight || document.documentElement.clientHeight || 0;
  const w = (viewport && viewport.width) || window.innerWidth || document.documentElement.clientWidth || 0;
  if (h && document.body) {
    document.body.style.setProperty('--tool-height', `${Math.round(h)}px`);
  }
  if (w && document.body) {
    document.body.style.setProperty('--tool-width', `${Math.round(w)}px`);
  }
  if (document.body) {
    if ((h && h <= 740) || (w && w <= 420)) {
      document.body.dataset.viewport = 'tight';
    } else {
      document.body.removeAttribute('data-viewport');
    }
  }
  const header = document.querySelector('.header');
  if (header && document.body) {
    document.body.style.setProperty('--tool-header', `${header.offsetHeight}px`);
  }
  const nav = document.querySelector('.app-nav');
  if (nav && document.body) {
    document.body.style.setProperty('--tool-nav', `${nav.offsetHeight}px`);
  }
}

function syncModeSwitchPlacement() {
  const panel = el('controlPanel');
  if (!panel) return;
  const head = panel.querySelector('.panel-head');
  const body = panel.querySelector('.control-body');
  const row = panel.querySelector('.control-row--mode');
  const title = head ? head.querySelector('.panel-title') : null;
  if (!head || !body || !row) return;
  const narrow = window.matchMedia ? window.matchMedia('(max-width: 720px)').matches : false;
  const tight = narrow || (document.body && document.body.dataset.viewport === 'tight');
  if (tight) {
    row.classList.add('inline');
    if (!head.contains(row)) {
      if (title && title.nextSibling) {
        head.insertBefore(row, title.nextSibling);
      } else {
        head.appendChild(row);
      }
    }
  } else {
    row.classList.remove('inline');
    if (!body.contains(row)) body.insertBefore(row, body.firstChild);
  }
}

function syncToolLayout() {
  setToolViewportVars();
  syncModeSwitchPlacement();
  if (document.body && document.body.dataset.viewport === 'tight' && state.mode === 'explore') {
    setMode('fixed');
  }
}

function _altId(iid) {
  if (!iid) return '';
  const s = String(iid);
  if (s.includes('_')) return s.replace(/_/g, '');
  return '';
}

function getI18nName(iid, lang) {
  const l = String(lang || '').trim().toLowerCase();
  const mp = (state.i18nNames && state.i18nNames[l]) ? state.i18nNames[l] : null;
  if (!mp) return '';
  const k = String(iid || '').trim();
  if (!k) return '';
  const lo = k.toLowerCase();
  const a1 = _altId(k);
  const a2 = _altId(lo);
  return mp[k] || mp[lo] || (a1 ? mp[a1] : '') || (a2 ? mp[a2] : '') || '';
}

async function ensureI18nNames(mode) {
  const lang = String(mode || '').trim().toLowerCase();
  if (!lang || lang === 'id') return;
  if (state.i18nLoaded && state.i18nLoaded[lang]) return;
  const enabled = Boolean(state.i18n && state.i18n.enabled);
  if (!enabled) return;
  try {
    const res = await fetchJson(api(`/api/v1/i18n/names/${encodeURIComponent(lang)}`));
    state.i18nNames[lang] = res.names || {};
    state.i18nLoaded[lang] = true;
  } catch (e) {
    state.i18nLoaded[lang] = false;
  }
}

function resolveLabel(iid, enName, zhName) {
  const mode = String(state.labelMode || 'en');
  if (mode === 'id') return iid;
  if (mode === 'zh' && zhName) return zhName;
  return enName || iid;
}

function itemLabel(iid) {
  const id = String(iid || '');
  if (!id) return '';
  const meta = (state.assets && state.assets[id]) ? state.assets[id] : null;
  const fallbackEn = (meta && meta.name) ? meta.name : id;
  const enName = getI18nName(id, 'en') || fallbackEn;
  const zhName = getI18nName(id, 'zh');
  return resolveLabel(id, enName, zhName);
}

function plantLabel(plant) {
  return itemLabel(plant?.id || '');
}

function shortId(iid) {
  return String(iid || '').replace(/[^a-z0-9]/gi, '').slice(0, 2).toUpperCase();
}

function iconUrls(iid) {
  const cfg = state.icon || {};
  const mode = String(cfg.mode || 'off');
  const enc = encodeURIComponent(String(iid || ''));
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

function iconHtml(iid, cls) {
  const label = shortId(iid);
  const { src, fallback } = iconUrls(iid);
  if (!src) {
    return (
      `<span class="item-icon ${cls}">` +
        `<span class="item-icon-fallback">${escHtml(label || '--')}</span>` +
      `</span>`
    );
  }
  const fbAttr = fallback ? ` data-fallback="${escHtml(fallback)}"` : '';
  return (
    `<span class="item-icon ${cls}">` +
      `<img class="item-icon-img" src="${escHtml(src)}" loading="lazy"${fbAttr} onerror="iconError(this)" alt="" />` +
      `<span class="item-icon-fallback">${escHtml(label || '--')}</span>` +
    `</span>`
  );
}

function iconStackHtml(seedId, fruitId, sizeClass) {
  const cls = sizeClass ? ` icon-stack--${sizeClass}` : '';
  const seedHtml = seedId ? iconHtml(seedId, 'seed') : '';
  const fruitHtml = fruitId ? iconHtml(fruitId, 'fruit') : '';
  return `<div class="icon-stack${cls}">${seedHtml}${fruitHtml}</div>`;
}

function plantSeedId(plant, fallbackId) {
  if (plant && plant.seed) return String(plant.seed);
  if (plant && plant.is_randomseed) return 'seeds';
  if (fallbackId) return `${fallbackId}_seeds`;
  return '';
}

function plantFruitId(pid, seedId) {
  const seed = String(seedId || '');
  if (seed && seed.endsWith('_seeds')) {
    return seed.slice(0, -6);
  }
  return String(pid || seed || '');
}

function plantSeedIdForId(pid) {
  const plant = state.plants.find(p => p.id === pid);
  return plantSeedId(plant, pid);
}

function formatDelta(value) {
  const v = Number(value);
  if (!Number.isFinite(v)) return '--';
  const abs = Math.abs(v);
  const digits = (abs % 1 === 0) ? 0 : 1;
  const base = abs.toFixed(digits);
  if (v > 0) return `+${base}`;
  if (v < 0) return `-${base}`;
  return '0';
}

function formatNeed(value) {
  const v = Number(value);
  if (!Number.isFinite(v)) return '--';
  const abs = Math.abs(v);
  const digits = (abs % 1 === 0) ? 0 : 1;
  return abs.toFixed(digits);
}

const WATER_UNIT = 0.0035;
const WATER_UNITS_MAX = 10;

function waterUnitsFromRate(value) {
  const v = Number(value);
  if (!Number.isFinite(v)) return null;
  return Math.abs(v) / WATER_UNIT;
}

function formatWaterUnits(units) {
  const val = Number(units);
  if (!Number.isFinite(val)) return '';
  let digits = 0;
  if (val > 0 && val < 1) digits = 2;
  else if (val < 10) digits = 1;
  let out = val.toFixed(digits);
  if (out.includes('.')) {
    out = out.replace(/0+$/, '').replace(/\.$/, '');
  }
  return out || '0';
}

function formatWaterRate(value) {
  const units = waterUnitsFromRate(value);
  if (units === null) return '';
  return formatWaterUnits(units);
}

function pitModeLabel(mode) {
  const key = String(mode || '').trim();
  if (key === '8') return t('farming.pit.mode.8', '8 (9-1)');
  if (key === '10') return t('farming.pit.mode.10', '10');
  return t('farming.pit.mode.9', '9');
}

function holesPerTile(mode) {
  const key = String(mode || '').trim();
  if (key === '8') return 8;
  if (key === '10') return 10;
  return 9;
}

function pitGridPositions(count) {
  const total = Number(count);
  if (!Number.isFinite(total) || total <= 0) return [];
  const step = 1 / (total + 1);
  const out = [];
  for (let i = 0; i < total; i++) out.push(step * (i + 1));
  return out;
}

function pitPattern(mode) {
  const key = String(mode || '').trim();
  if (key === '8' || key === '9') {
    const pts = pitGridPositions(3);
    const coords = [];
    for (let r = 0; r < pts.length; r++) {
      for (let c = 0; c < pts.length; c++) {
        if (key === '8' && r === 1 && c === 1) continue;
        coords.push([pts[c], pts[r]]);
      }
    }
    return coords;
  }
  const rowLens = [2, 3, 2, 3];
  const ys = pitGridPositions(rowLens.length);
  const coords = [];
  rowLens.forEach((len, idx) => {
    const xs = pitGridPositions(len);
    xs.forEach((x) => coords.push([x, ys[idx]]));
  });
  return coords;
}

function buildPlotPits(tileW, tileH, mode) {
  const w = Math.max(1, Number(tileW) || 1);
  const h = Math.max(1, Number(tileH) || 1);
  const local = pitPattern(mode);
  const pits = [];
  let idx = 0;
  for (let ty = 0; ty < h; ty++) {
    for (let tx = 0; tx < w; tx++) {
      for (const [x, y] of local) {
        pits.push({ x: x + tx, y: y + ty, tile_x: tx, tile_y: ty, index: idx });
        idx += 1;
      }
    }
  }
  return pits;
}

function waterLabelForRate(rate) {
  const val = Number(rate);
  if (!Number.isFinite(val)) return '';
  const low = Math.abs(Number(state.tuning.FARM_PLANT_DRINK_LOW));
  const med = Math.abs(Number(state.tuning.FARM_PLANT_DRINK_MED));
  const high = Math.abs(Number(state.tuning.FARM_PLANT_DRINK_HIGH));
  if (!Number.isFinite(low) || !Number.isFinite(med) || !Number.isFinite(high)) return '';
  const avg = Math.abs(val);
  if (avg <= (low + med) / 2) return 'low';
  if (avg <= (med + high) / 2) return 'med';
  return 'high';
}

function waterLabelText(level) {
  if (level === 'low') return t('farming.water.low', 'Low water');
  if (level === 'med') return t('farming.water.med', 'Medium water');
  if (level === 'high') return t('farming.water.high', 'High water');
  return t('farming.water.unknown', 'Water n/a');
}

function seasonLabelText(season) {
  const key = String(season || '').trim().toLowerCase();
  if (!key) return t('farming.season.all', 'All seasons');
  if (key === 'autumn') return t('farming.season.autumn', 'Autumn');
  if (key === 'winter') return t('farming.season.winter', 'Winter');
  if (key === 'spring') return t('farming.season.spring', 'Spring');
  if (key === 'summer') return t('farming.season.summer', 'Summer');
  return key;
}

function orderSeasonTags(tags) {
  const order = ['spring', 'summer', 'autumn', 'winter'];
  const rank = new Map(order.map((k, i) => [k, i]));
  return (tags || []).slice().sort((a, b) => {
    const ra = rank.has(a) ? rank.get(a) : 99;
    const rb = rank.has(b) ? rank.get(b) : 99;
    if (ra !== rb) return ra - rb;
    return String(a || '').localeCompare(String(b || ''));
  });
}

function seasonSymbol(season) {
  const key = String(season || '').trim().toLowerCase();
  if (key === 'autumn') return t('farming.season.sym.autumn', '🍂');
  if (key === 'winter') return t('farming.season.sym.winter', '❄');
  if (key === 'spring') return t('farming.season.sym.spring', '🌱');
  if (key === 'summer') return t('farming.season.sym.summer', '☀');
  return '';
}

function seasonPack(seasonTags) {
  let tags = orderSeasonTags(seasonTags || []);
  if (!tags.length) {
    tags = ['spring', 'summer', 'autumn', 'winter'];
  }
  const icons = tags.map((key) => {
    const symbol = seasonSymbol(key) || seasonLabelText(key).charAt(0).toUpperCase();
    return `<span class="season-icon season-${escHtml(key)}" title="${escHtml(seasonLabelText(key))}">${escHtml(symbol)}</span>`;
  }).join('');
  return `<span class="season-pack">${icons}</span>`;
}

async function loadMeta() {
  const m = await fetchJson(api('/api/v1/meta'));
  state.i18n = (m && m.i18n) ? m.i18n : { enabled: false };
  applyLabelModeUI();
  await ensureUiStrings(uiLang());
  applyUiStrings();
  applyModeUI();
  const defs = m.farming_defs_enabled ? 'farming:on' : 'farming:off';
  const sha = m.scripts_sha256_12 ? `sha:${m.scripts_sha256_12}` : '';
  const meta = [sha, defs].filter(Boolean).join(' | ');
  const metaNode = el('meta');
  if (metaNode) metaNode.textContent = meta;
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

async function loadFarmingDefs() {
  const res = await fetchJson(api('/api/v1/farming/defs'));
  state.defs = res;
  state.plants = res.plants || [];
  state.tuning = res.tuning || {};
  state.seasons = res.seasons || [];
  computeConsumeMax();
  buildSeasonOptions();
  updateDefsMeta();
}

async function loadFixedSolutions() {
  try {
    const res = await fetchJson(api('/api/v1/farming/fixed'));
    const solutions = Array.isArray(res.solutions) ? res.solutions : [];
    solutions.forEach((plan, idx) => {
      plan._index = idx;
    });
    state.fixed = { ...res, solutions };
  } catch (e) {
    state.fixed = { enabled: false, solutions: [] };
  }
}

function updateDefsMeta() {
  const meta = el('defsMeta');
  if (!meta) return;
  const v = state.defs ? state.defs.schema_version : null;
  const fixed = state.fixed ? state.fixed.schema_version : null;
  const parts = [`defs: v${v || 1}`];
  if (state.fixed && state.fixed.enabled) {
    parts.push(`fixed: v${fixed || 1}`);
  }
  meta.textContent = parts.join(' | ');
}

function computeConsumeMax() {
  const max = [0, 0, 0];
  for (const plant of state.plants) {
    const consume = Array.isArray(plant.consume) ? plant.consume : [0, 0, 0];
    for (let i = 0; i < 3; i++) {
      const v = Number(consume[i] || 0);
      if (Number.isFinite(v) && v > max[i]) max[i] = v;
    }
  }
  state.consumeMax = max;
}

function buildSeasonOptions() {
  const sel = el('season');
  if (!sel) return;
  const cur = sel.value || '';
  const seasons = [''];
  for (const s of state.seasons || []) seasons.push(String(s));
  const uniq = Array.from(new Set(seasons.filter(Boolean).map(s => s.toLowerCase())));
  uniq.sort();
  sel.innerHTML = '';
  const allOpt = document.createElement('option');
  allOpt.value = '';
  allOpt.textContent = t('farming.season.all', 'All seasons');
  sel.appendChild(allOpt);
  for (const s of uniq) {
    const opt = document.createElement('option');
    opt.value = s;
    opt.textContent = seasonLabelText(s);
    sel.appendChild(opt);
  }
  if (cur) {
    try { sel.value = cur; } catch (e) {}
  }
}

function filterPlants() {
  const season = String(el('season')?.value || '').trim().toLowerCase();
  return state.plants.filter((plant) => {
    if (season) {
      const seasons = plant.good_seasons || {};
      if (!seasons[season]) return false;
    }
    return true;
  });
}

function renderPlantGrid() {
  const grid = el('plantGrid');
  if (!grid) return;
  const plants = filterPlants();
  const max = state.consumeMax || [0, 0, 0];
  grid.innerHTML = plants.map((plant, idx) => {
    const consume = Array.isArray(plant.consume) ? plant.consume : [0, 0, 0];
    const water = waterLabelForRate(plant.drink_rate);
    const waterText = waterLabelText(water);
    const waterClass = water ? `water-${water}` : '';
    const waterVal = formatWaterRate(plant.drink_rate);
    const waterLevel = (() => {
      const abs = Math.abs(Number(plant.drink_rate || 0));
      const max = Math.abs(Number(state.tuning.FARM_PLANT_DRINK_HIGH || 0)) || 0.035;
      if (!Number.isFinite(abs) || !Number.isFinite(max) || max <= 0) return 0;
      return Math.max(0, Math.min(1, abs / max));
    })();
    const seasons = plant.good_seasons || {};
    const seasonTags = Object.keys(seasons).filter(k => seasons[k]);
    const selected = state.selected.has(plant.id);
    const seedId = plantSeedId(plant, plant.id);
    const fruitId = plantFruitId(plant.id, seedId);
    const seedLabel = itemLabel(seedId) || plantLabel(plant);
    const fruitLabel = itemLabel(fruitId) || fruitId;
    const id = escHtml(plant.id);
    const title = escHtml(`${seedLabel} | ${fruitLabel}`);
    const bar = (v, i) => {
      const maxVal = max[i] || 1;
      const val = Math.max(0, Number(v) || 0);
      const pct = Math.min(100, Math.round((val / maxVal) * 100));
      return `<div class="nutrient-bar n${i + 1}"><span style="--value:${pct}%"></span></div>`;
    };
    const seasonPackHtml = seasonPack(seasonTags);
    return (
      `<div class="plant-card${selected ? ' selected' : ''}" data-id="${id}" style="--delay:${idx * 0.02}s" title="${title}">` +
        `<div class="plant-head">` +
          `<div class="plant-icon">` +
            `${iconStackHtml(seedId, fruitId, 'lg')}` +
          `</div>` +
          `<div class="plant-text">` +
            `<div class="plant-title">${escHtml(seedLabel)}</div>` +
            `<div class="plant-sub">${escHtml(fruitLabel)}</div>` +
          `</div>` +
        `</div>` +
        `<div class="nutrient-bars">${bar(consume[0], 0)}${bar(consume[1], 1)}${bar(consume[2], 2)}</div>` +
        `<div class="plant-row plant-season">` +
          `${seasonPackHtml}` +
          `<span class="season-divider" aria-hidden="true"></span>` +
          `<span class="water-pill ${waterClass}" style="--water-level:${waterLevel.toFixed(3)}" title="${escHtml(waterText)}">` +
            `<span class="water-icon">💧</span>` +
            `<span class="water-val">${escHtml(waterVal || '')}</span>` +
          `</span>` +
        `</div>` +
      `</div>`
    );
  }).join('');
}

function renderSelectedList() {
  const list = el('selectionList');
  if (!list) return;
  const items = Array.from(state.selected);
  if (!items.length) {
    list.innerHTML = `<span class="muted">${escHtml(t('farming.selected.all', 'All plants'))}</span>`;
    return;
  }
  const shown = items.slice(0, MAX_SELECTED_CHIPS);
  const extra = items.length - shown.length;
  const chips = shown.map((id) => {
    const plant = state.plants.find(p => p.id === id);
    const label = plant ? plantLabel(plant) : id;
    return `<span class="selected-chip" data-id="${escHtml(id)}">${escHtml(label)}</span>`;
  });
  if (extra > 0) {
    chips.push(`<span class="selected-chip extra" title="${escHtml(t('farming.selected.more', 'More selected'))}">+${extra}</span>`);
  }
  list.innerHTML = chips.join('');
}

function renderPlanPlants(plants, counts, opts) {
  const options = opts || {};
  const showCounts = options.showCounts !== false;
  return (plants || []).map((pid) => {
    const seedId = plantSeedIdForId(pid);
    const fruitId = plantFruitId(pid, seedId);
    const seedLabel = itemLabel(seedId) || seedId;
    const fruitLabel = itemLabel(fruitId) || fruitId;
    const count = showCounts ? Number(counts?.[pid] || 0) : null;
    const selected = state.selected.has(pid) ? ' selected' : '';
    const countHtml = (count !== null && count > 0) ? `<div class="plan-plant-count">x${count}</div>` : '';
    return (
      `<div class="plan-plant${selected}">` +
        `${iconStackHtml(seedId, fruitId, 'sm')}` +
        `<div class="plan-plant-text">` +
          `<div class="plan-plant-name">${escHtml(fruitLabel)}</div>` +
          `<div class="plan-plant-sub">${escHtml(seedLabel)}</div>` +
        `</div>` +
        countHtml +
      `</div>`
    );
  }).join('');
}

function planSelectionScore(plan) {
  if (!state.selected.size) return 0;
  const plants = plan.plants || [];
  let score = 0;
  for (const pid of plants) {
    if (state.selected.has(pid)) score += 1;
  }
  return score;
}

function planIndexValue(plan, fallback) {
  const idx = Number(plan?._index);
  return Number.isFinite(idx) ? idx : (fallback || 0);
}

function sortPlansBySelection(plans) {
  if (!state.selected.size) return plans;
  return plans.sort((a, b) => {
    const scoreDiff = planSelectionScore(b) - planSelectionScore(a);
    if (scoreDiff !== 0) return scoreDiff;
    return planIndexValue(a, 0) - planIndexValue(b, 0);
  });
}

function planRatioKey(plan) {
  const raw = String(plan?.ratio || '').trim();
  return raw || RATIO_MIX_KEY;
}

function ratioLabel(key) {
  if (key === RATIO_MIX_KEY) return t('farming.ratio.mix', 'Mix');
  return key;
}

function ratioSort(a, b) {
  const la = ratioLabel(a);
  const lb = ratioLabel(b);
  return la.localeCompare(lb, 'en', { numeric: true });
}

function renderRatioFilters(ratioKeys, counts) {
  const wrap = el('ratioFilters');
  if (!wrap) return;
  if (!ratioKeys || !ratioKeys.length || state.mode === 'single') {
    wrap.innerHTML = '';
    return;
  }
  const active = state.ratioFilter || '';
  const tags = [];
  const allLabel = t('farming.ratio.all', 'All');
  tags.push(
    `<button class="ratio-tag${active ? '' : ' active'}" data-ratio="">${escHtml(allLabel)}</button>`
  );
  ratioKeys.forEach((key) => {
    const label = ratioLabel(key);
    const count = counts.get(key) || 0;
    const isActive = active === key;
    tags.push(
      `<button class="ratio-tag${isActive ? ' active' : ''}" data-ratio="${escHtml(key)}">` +
        `${escHtml(label)}` +
        `<span class="ratio-count">${count}</span>` +
      `</button>`
    );
  });
  wrap.innerHTML = tags.join('');
}

function planMatchesSeason(plan, season) {
  const s = String(season || '').trim().toLowerCase();
  if (!s) return true;
  const plants = plan.plants || [];
  return plants.every((pid) => {
    const plant = state.plants.find(p => p.id === pid);
    if (!plant) return false;
    const seasons = plant.good_seasons || {};
    return Boolean(seasons[s]);
  });
}

function fixedPlansForPlot() {
  const solutions = (state.fixed && Array.isArray(state.fixed.solutions)) ? state.fixed.solutions : [];
  const manual = Boolean(state.fixedFilter && state.fixedFilter.manual);
  const tileKey = `${state.plot.tileW}x${state.plot.tileH}`;
  const tileSet = manual ? new Set([tileKey]) : new Set(FIXED_TILE_KEYS);
  const modes = manual ? (state.plot.pitModes || new Set()) : new Set(FIXED_PIT_MODES);
  return solutions.filter((plan) => {
    const tile = plan.tile || {};
    const w = Number(tile.width || 0);
    const h = Number(tile.height || 0);
    if (!tileSet.has(`${w}x${h}`)) return false;
    const mode = String(plan.pit_mode || '');
    if (modes.size && !modes.has(mode)) return false;
    return true;
  });
}

function renderSingleNutrient() {
  const wrap = el('results');
  if (!wrap) return;
  const season = String(el('season')?.value || '').trim().toLowerCase();
  const plants = state.plants.filter((plant) => {
    if (season) {
      const seasons = plant.good_seasons || {};
      if (!seasons[season]) return false;
    }
    return true;
  });

  const groups = { 1: [], 2: [], 3: [] };
  plants.forEach((plant) => {
    const consume = Array.isArray(plant.consume) ? plant.consume : [0, 0, 0];
    const nonzero = consume.map((v, i) => (Number(v) > 0 ? i + 1 : 0)).filter(Boolean);
    if (nonzero.length === 1) {
      groups[nonzero[0]].push(plant);
    }
  });
  [1, 2, 3].forEach((idx) => {
    groups[idx].sort((a, b) => {
      const sa = state.selected.has(a.id) ? 1 : 0;
      const sb = state.selected.has(b.id) ? 1 : 0;
      if (sa !== sb) return sb - sa;
      return plantLabel(a).localeCompare(plantLabel(b));
    });
  });

  const total = groups[1].length + groups[2].length + groups[3].length;
  const meta = el('resultMeta');
  if (meta) meta.textContent = `${total} ${t('farming.results.plants', 'plants')}`;
  const summary = el('planSummary');
  if (summary) summary.textContent = t('farming.single.hint', 'Plant any 4 from one group.');

  if (!total) {
    wrap.innerHTML = `<div class="muted">${escHtml(t('farming.single.empty', 'No single-nutrient crops match filters.'))}</div>`;
    return;
  }

  const cards = [1, 2, 3].map((idx) => {
    const list = groups[idx];
    if (!list.length) return '';
    const plants = list.map(p => p.id);
    const plantRows = renderPlanPlants(plants, null, { showCounts: false });
    const title = t('farming.single.need', 'Need N{n}').replace('{n}', String(idx));
    return (
      `<div class="plan-card">` +
        `<div class="plan-plants">${plantRows}</div>` +
        `<div class="plan-meta">` +
          `<div class="plan-ratio">${escHtml(title)}</div>` +
          `<div class="plan-score">${escHtml(t('farming.single.plan', 'Plant x4'))}</div>` +
        `</div>` +
      `</div>`
    );
  }).join('');

  wrap.innerHTML = cards;
}

function selectedPitModes() {
  const modes = new Set();
  const wrap = el('pitModes');
  if (!wrap) return modes;
  const inputs = wrap.querySelectorAll('input[type="checkbox"]');
  inputs.forEach((input) => {
    if (input.checked) modes.add(String(input.value || '').trim());
  });
  return modes;
}

function updatePlotMeta() {
  const meta = el('plotMeta');
  if (!meta) return;
  if (state.mode === 'fixed' && !(state.fixedFilter && state.fixedFilter.manual)) {
    const tiles = `${FIXED_TILE_KEYS[0]} + ${FIXED_TILE_KEYS[1]}`;
    const pits = FIXED_PIT_MODES.join('/');
    const parts = [
      `${t('farming.plot.meta.tiles', 'Tiles')} ${tiles}`,
      `${t('farming.plot.meta.pits', 'Pits')} ${pits}`,
    ];
    meta.textContent = parts.join(' | ');
    return;
  }
  const w = state.plot.tileW;
  const h = state.plot.tileH;
  const modes = Array.from(state.plot.pitModes).filter(Boolean);
  const parts = [`${t('farming.plot.meta.tiles', 'Tiles')} ${w}x${h}`];
  modes.sort((a, b) => Number(a) - Number(b)).forEach((mode) => {
    const total = w * h * holesPerTile(mode);
    parts.push(`${pitModeLabel(mode)} ${total}`);
  });
  meta.textContent = parts.join(' | ');
}

function renderPlotPreview(plan) {
  const canvas = el('plotPreview');
  if (!canvas) return;
  const patternLabel = el('plotPattern');
  const plotHint = el('plotHint');
  if (plotHint) plotHint.textContent = '';

  if (!plan && state.activePlanIndex !== null) {
    const idx = Number(state.activePlanIndex);
    if (state.mode === 'fixed') {
      const fixed = (state.fixed && Array.isArray(state.fixed.solutions)) ? state.fixed.solutions : [];
      plan = fixed.find(p => Number(p._index) === idx) || null;
    } else {
      plan = state.results.find(p => Number(p._index) === idx) || null;
    }
  }

  let pits = [];
  let tileW = state.plot.tileW;
  let tileH = state.plot.tileH;
  let pattern = state.plot.activePattern || '9';
  let colorMap = {};

  if (plan && plan.layout && plan.layout.mode === 'pits') {
    const layout = plan.layout;
    pits = Array.isArray(layout.pits) ? layout.pits : [];
    tileW = layout.tile ? layout.tile.width : tileW;
    tileH = layout.tile ? layout.tile.height : tileH;
    pattern = layout.pattern || pattern;
    if (layout.pattern) state.plot.activePattern = layout.pattern;
    const plants = plan.plants || [];
    plants.forEach((pid, idx) => {
      colorMap[pid] = COLOR_BANK[idx % COLOR_BANK.length];
    });
  } else {
    pits = buildPlotPits(tileW, tileH, pattern);
  }

  if (patternLabel) {
    const label = pattern ? pitModeLabel(pattern) : '';
    patternLabel.textContent = label;
  }

  const maxW = Math.max(1, Number(tileW) || 1);
  const maxH = Math.max(1, Number(tileH) || 1);
  const viewW = maxH;
  const viewH = maxW;
  const displayW = Math.max(viewW, 2);
  const displayH = Math.max(viewH, 2);
  const offsetX = (displayW - viewW) / 2;
  const offsetY = (displayH - viewH) / 2;
  const radius = 0.06;
  const tiles = [];
  for (let ty = 0; ty < maxH; ty++) {
    for (let tx = 0; tx < maxW; tx++) {
      const rx = ty + offsetX;
      const ry = maxW - tx - 1 + offsetY;
      tiles.push(`<rect class="plot-tile" x="${rx}" y="${ry}" width="1" height="1"></rect>`);
    }
  }
  const dots = pits.map((pit) => {
    const pid = pit.plant || '';
    const color = pid ? (colorMap[pid] || 'var(--accent)') : null;
    const style = color ? `fill:${color};stroke:${color};` : '';
    const cls = pid ? 'plot-dot assigned' : 'plot-dot';
    const px = Number(pit.x) || 0;
    const py = Number(pit.y) || 0;
    const rx = py + offsetX;
    const ry = maxW - px + offsetY;
    return `<circle class="${cls}" cx="${rx}" cy="${ry}" r="${radius}" style="${style}"></circle>`;
  }).join('');

  const aspect = (document.body && document.body.dataset.viewport === 'tight') ? 'none' : 'xMidYMid meet';
  const svg = (
    `<svg viewBox="0 0 ${displayW} ${displayH}" preserveAspectRatio="${aspect}" role="img" aria-label="${escHtml(t('farming.plot.preview', 'Plot preview'))}">` +
      `<g>${tiles.join('')}</g>` +
      `<g>${dots}</g>` +
    `</svg>`
  );
  canvas.innerHTML = svg;
}

function syncPlotState() {
  let plotW = Math.max(1, Number(el('plotW')?.value || 1));
  let plotH = Math.max(1, Number(el('plotH')?.value || 1));
  if (state.mode === 'fixed') {
    if (!((plotW === 1 && plotH === 1) || (plotW === 1 && plotH === 2))) {
      plotW = 1;
      plotH = 2;
      if (el('plotW')) el('plotW').value = plotW;
      if (el('plotH')) el('plotH').value = plotH;
    }
  }
  state.plot.tileW = plotW;
  state.plot.tileH = plotH;
  state.plot.pitModes = selectedPitModes();
  if (!state.plot.pitModes.has(state.plot.activePattern)) {
    const next = Array.from(state.plot.pitModes)[0];
    if (next) state.plot.activePattern = next;
  }
  updatePlotMeta();
}

function renderPlanCard(plan, idx) {
  const planIndex = Number.isFinite(Number(plan._index)) ? Number(plan._index) : idx;
  const ratio = ratioLabel(planRatioKey(plan));
  const nutrientOverall = (plan.nutrients && plan.nutrients.overall) ? plan.nutrients.overall : plan.nutrients;
  const nutrientBase = (plan.nutrients && plan.nutrients.tile) ? plan.nutrients.tile : plan.nutrients;
  const deficit = (nutrientBase && nutrientBase.deficit) ? nutrientBase.deficit : { count: 0, total: 0, max: 0 };
  const overallDeficit = (nutrientOverall && nutrientOverall.deficit) ? nutrientOverall.deficit : { count: 0 };
  const tileDeficit = (plan.nutrients && plan.nutrients.tile && plan.nutrients.tile.deficit)
    ? plan.nutrients.tile.deficit
    : null;
  const deficitTotal = formatNeed(deficit.total);
  const plants = plan.plants || [];
  const counts = plan.counts || {};
  const netCycle = nutrientBase && nutrientBase.net_cycle ? nutrientBase.net_cycle : [0, 0, 0];
  const water = plan.water || {};
  const waterLevel = water.label || '';
  const waterText = waterLabelText(waterLevel);
  const waterClass = waterLevel ? `water-${waterLevel}` : '';
  const layoutInfo = plan.layout || null;
  const tile = (layoutInfo && layoutInfo.tile) ? layoutInfo.tile : null;
  const tileW = tile ? Number(tile.width || 0) : 0;
  const tileH = tile ? Number(tile.height || 0) : 0;
  const holesPerTile = (layoutInfo && layoutInfo.holes_per_tile) ? Number(layoutInfo.holes_per_tile || 0) : 0;
  let slotCount = Number(plan.slots || 0);
  if (layoutInfo && layoutInfo.mode === 'pits' && tileW > 0 && tileH > 0 && holesPerTile > 0) {
    slotCount = tileW * tileH * holesPerTile;
  } else if (layoutInfo && layoutInfo.mode === 'grid' && layoutInfo.width && layoutInfo.height) {
    slotCount = Number(layoutInfo.width || 0) * Number(layoutInfo.height || 0);
  }
  const waterAvg = (water && Number.isFinite(Number(water.avg))) ? Math.abs(Number(water.avg)) : null;
  let totalWater = (water && Number.isFinite(Number(water.total))) ? Math.abs(Number(water.total)) : null;
  if (totalWater === null && waterAvg !== null && slotCount > 0) {
    totalWater = waterAvg * slotCount;
  }
  const tileCount = (tileW > 0 && tileH > 0) ? (tileW * tileH) : 1;
  const perTileWater = (totalWater !== null && tileCount > 0) ? (totalWater / tileCount) : null;
  const waterUnitsValue = (perTileWater !== null) ? (Math.abs(perTileWater) / WATER_UNIT) : null;
  const waterUnits = (waterUnitsValue !== null) ? formatWaterUnits(waterUnitsValue) : '';
  const waterLevelPct = (() => {
    if (waterUnitsValue === null) return 0;
    const high = Math.abs(Number(state.tuning.FARM_PLANT_DRINK_HIGH || 0));
    const perPlantUnits = (Number.isFinite(high) && high > 0) ? (high / WATER_UNIT) : WATER_UNITS_MAX;
    const unitsMax = perPlantUnits * 10;
    return Math.max(0, Math.min(1, waterUnitsValue / unitsMax));
  })();
  const midStageRisk = Boolean(nutrientBase && nutrientBase.mid_stage_risk);
  const perfect = (Number(overallDeficit.count || 0) === 0) && (!tileDeficit || Number(tileDeficit.count || 0) === 0);
  const deficitCells = netCycle
    .map((v, i) => ({ v, i }))
    .filter(row => row.v < -1e-9);
  const netGrid = deficitCells.map((row) => {
    return (
      `<div class="net-cell net-neg">` +
        `<span class="net-label">N${row.i + 1}</span>` +
        `<span class="net-value">${escHtml(formatDelta(row.v))}</span>` +
      `</div>`
    );
  }).join('');

  const plantRows = renderPlanPlants(plants, counts, { showCounts: true });

  const familyOk = plan.family && plan.family.counts_ok;
  const crowdOk = plan.overcrowding_ok;
  const badges = [
    (familyOk === false) ? { text: t('farming.family.bad', 'Family short'), cls: 'badge-warn' } : null,
    (crowdOk === false) ? { text: t('farming.crowding.bad', 'Overcrowded'), cls: 'badge-warn' } : null,
    (perfect && state.mode !== 'fixed') ? { text: t('farming.deficit.perfect', 'Perfect complement'), cls: 'badge-ok' } : null,
    midStageRisk ? { text: t('farming.deficit.risk', 'Mid-stage deficit risk'), cls: 'badge-warn' } : null,
  ].filter(Boolean).map(b => `<span class="chip ${b.cls}">${escHtml(b.text)}</span>`).join('');

  const layout = plan.layout || null;
  let holesChip = '';
  if (layout && layout.mode === 'pits') {
    const key = String(layout.pattern || '').trim();
    const holesLabel = t('farming.plot.meta.holes', 'holes');
    if (key === '10') {
      holesChip = `<span class="chip">10 ${escHtml(holesLabel)}</span>`;
    }
  }

  return (
    `<div class="plan-card${state.activePlanIndex === planIndex ? ' active' : ''}" data-plan-idx="${planIndex}" style="--delay:${idx * 0.02}s">` +
      `<div class="plan-plants">${plantRows}</div>` +
      `<div class="plan-meta">` +
        `<div class="plan-ratio">${escHtml(ratio)}</div>` +
        `${(deficit && deficit.count > 0) ? `<div class="plan-score">${t('farming.deficit.count', 'Deficit')} ${escHtml(String(deficit.count))}</div>` : ''}` +
        `<div class="plan-meta-badges">` +
          `<span class="water-pill ${waterClass}" style="--water-level:${waterLevelPct.toFixed(3)}" title="${escHtml(waterText)}">` +
            `<span class="water-icon">💧</span>` +
            `<span class="water-val">${escHtml(waterUnits || '')}</span>` +
          `</span>` +
          `${holesChip}` +
          `${badges}` +
        `</div>` +
      `</div>` +
      `${netGrid ? (
        `<div class="plan-net">` +
          `<div class="net-title">${t('farming.net.label', 'Net x4')}</div>` +
          `<div class="net-grid">${netGrid}</div>` +
        `</div>`
      ) : ''}` +
    `</div>`
  );
}

function renderResults() {
  const wrap = el('results');
  if (!wrap) return;
  if (state.mode === 'single') {
    renderRatioFilters([], new Map());
    renderSingleNutrient();
    return;
  }
  const season = String(el('season')?.value || '').trim();
  let plans = [];
  if (state.mode === 'fixed') {
    if (!(state.fixed && state.fixed.enabled)) {
      wrap.innerHTML = `<div class="muted">${escHtml(t('farming.fixed.empty', 'Complement solutions not available.'))}</div>`;
      const meta = el('resultMeta');
      if (meta) meta.textContent = '0';
      const summary = el('planSummary');
      if (summary) summary.textContent = t('farming.results.none', 'No plans yet.');
      renderRatioFilters([], new Map());
      return;
    }
    plans = fixedPlansForPlot();
  } else {
    plans = Array.isArray(state.results) ? state.results.slice() : [];
  }

  if (season) {
    plans = plans.filter(plan => planMatchesSeason(plan, season));
  }
  plans = plans.filter(plan => plan.family && plan.family.layout_ok === true);
  const baseCount = plans.length;

  const ratioCounts = new Map();
  plans.forEach((plan) => {
    const key = planRatioKey(plan);
    ratioCounts.set(key, (ratioCounts.get(key) || 0) + 1);
  });
  const ratioKeys = Array.from(ratioCounts.keys()).sort(ratioSort);
  if (state.ratioFilter && !ratioCounts.has(state.ratioFilter)) {
    state.ratioFilter = '';
  }
  renderRatioFilters(ratioKeys, ratioCounts);
  if (state.ratioFilter) {
    plans = plans.filter(plan => planRatioKey(plan) === state.ratioFilter);
  }

  plans = sortPlansBySelection(plans);

  const meta = el('resultMeta');
  if (meta) meta.textContent = `${plans.length} / ${baseCount}`;
  const summary = el('planSummary');
  if (summary) summary.textContent = `${plans.length} ${t('farming.results.plans', 'plans')}`;

  let activeValid = true;
  if (state.activePlanIndex !== null) {
    const activeIdx = Number(state.activePlanIndex);
    activeValid = plans.some(plan => Number(plan._index) === activeIdx);
    if (!activeValid) state.activePlanIndex = null;
  }

  if (!plans.length) {
    const msg = baseCount
      ? t('farming.results.empty', 'No plans match filters.')
      : t('farming.results.none', 'No plans yet.');
    wrap.innerHTML = `<div class="muted">${escHtml(msg)}</div>`;
    renderRatioFilters([], new Map());
    if (!activeValid) renderPlotPreview();
    return;
  }

  const grouped = new Map();
  plans.forEach((plan) => {
    const key = planRatioKey(plan);
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(plan);
  });
  const order = (state.ratioFilter ? [state.ratioFilter] : ratioKeys)
    .filter(key => grouped.has(key));
  let cardIndex = 0;
  wrap.innerHTML = order.map((key) => {
    const list = grouped.get(key) || [];
    const label = ratioLabel(key);
    const cards = list.map((plan) => renderPlanCard(plan, cardIndex++)).join('');
    return (
      `<section class="ratio-column" data-ratio="${escHtml(key)}">` +
        `<div class="ratio-head">` +
          `<span class="ratio-label">${escHtml(label)}</span>` +
          `<span class="ratio-count">${list.length}</span>` +
        `</div>` +
        `<div class="ratio-stack">${cards}</div>` +
      `</section>`
    );
  }).join('');
  if (!activeValid) renderPlotPreview();
}

async function generatePlans() {
  setError('');
  if (state.mode !== 'explore') {
    renderResults();
    renderPlotPreview();
    return;
  }
  const tileW = Math.max(1, Number(el('plotW')?.value || 1));
  const tileH = Math.max(1, Number(el('plotH')?.value || 1));
  state.plot.tileW = tileW;
  state.plot.tileH = tileH;
  const modes = Array.from(state.plot.pitModes).sort((a, b) => Number(a) - Number(b));
  const plotHint = el('plotHint');
  if (!modes.length) {
    if (plotHint) plotHint.textContent = t('farming.plot.hint', 'Select at least one pit pattern.');
    return;
  }
  if (plotHint) plotHint.textContent = '';

  const maxKinds = Number(el('maxKinds')?.value || 3);
  const topN = Number(el('topN')?.value || 12);
  const season = String(el('season')?.value || '').trim() || null;

  try {
    const payloadBase = {
      season: season,
      max_kinds: Math.max(2, Math.round(maxKinds)),
      top_n: Math.max(1, Math.round(topN)),
      tile: [Math.round(tileW), Math.round(tileH)],
    };
    const results = [];
    const tasks = modes.map((mode) => {
      const slots = tileW * tileH * holesPerTile(mode);
      const payload = { ...payloadBase, slots: Math.max(1, Math.round(slots)), pit_mode: mode };
      return fetchJson(api('/api/v1/farming/plan'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }).then(res => ({ mode, res }));
    });
    const responses = await Promise.all(tasks);
    for (const { res } of responses) {
      const plans = res.plans || [];
      for (const plan of plans) {
        plan._index = results.length;
        results.push(plan);
      }
    }
    state.results = results;
    state.activePlanIndex = null;
    renderResults();
    renderPlotPreview();
  } catch (e) {
    setError(String(e));
  }
}

function bindEvents() {
  const navCraft = el('navCraft');
  if (navCraft) navCraft.href = APP_ROOT + '/craft';
  const navCooking = el('navCooking');
  if (navCooking) navCooking.href = APP_ROOT + '/cooking';
  const navFarming = el('navFarming');
  if (navFarming) navFarming.href = APP_ROOT + '/farming';
  const navCatalog = el('navCatalog');
  if (navCatalog) navCatalog.href = APP_ROOT + '/catalog';

  const appNavCraft = el('appNavCraft');
  if (appNavCraft) appNavCraft.href = APP_ROOT + '/craft';
  const appNavCooking = el('appNavCooking');
  if (appNavCooking) appNavCooking.href = APP_ROOT + '/';
  const appNavFarming = el('appNavFarming');
  if (appNavFarming) appNavFarming.href = APP_ROOT + '/farming';
  const appNavCatalog = el('appNavCatalog');
  if (appNavCatalog) appNavCatalog.href = APP_ROOT + '/catalog';
  if (appNavCraft) appNavCraft.classList.toggle('active', PAGE === 'craft');
  if (appNavCooking) appNavCooking.classList.toggle('active', PAGE === 'cooking');
  if (appNavFarming) appNavFarming.classList.toggle('active', PAGE === 'farming');
  if (appNavCatalog) appNavCatalog.classList.toggle('active', PAGE === 'catalog');

  const plantClear = el('plantClear');
  if (plantClear) plantClear.onclick = () => {
    state.selected.clear();
    renderPlantGrid();
    renderSelectedList();
    renderResults();
  };
  const plantGrid = el('plantGrid');
  if (plantGrid) {
    plantGrid.addEventListener('click', (e) => {
      const card = e.target.closest('.plant-card');
      if (!card) return;
      const id = card.getAttribute('data-id');
      if (!id) return;
      if (state.selected.has(id)) state.selected.delete(id);
      else state.selected.add(id);
      renderPlantGrid();
      renderSelectedList();
      renderResults();
    });
  }
  const selectionList = el('selectionList');
  if (selectionList) {
    selectionList.addEventListener('click', (e) => {
      const chip = e.target.closest('.selected-chip');
      if (!chip) return;
      const id = chip.getAttribute('data-id');
      if (!id) return;
      state.selected.delete(id);
      renderPlantGrid();
      renderSelectedList();
      renderResults();
    });
  }
  const seasonSel = el('season');
  if (seasonSel) seasonSel.addEventListener('change', () => {
    renderPlantGrid();
    if (state.mode !== 'explore') renderResults();
  });
  const modeSwitch = el('modeSwitch');
  if (modeSwitch) {
    modeSwitch.addEventListener('click', (e) => {
      const btn = e.target.closest('.mode-btn');
      if (!btn) return;
      const mode = btn.getAttribute('data-mode');
      if (!mode) return;
      setMode(mode);
      if (state.mode === 'explore') {
        generatePlans();
      } else {
        renderResults();
      }
    });
  }
  const plotW = el('plotW');
  const plotH = el('plotH');
  const plotPresets = el('plotPresets');
  const pitModes = el('pitModes');
  const refreshPlot = () => {
    state.activePlanIndex = null;
    syncPlotState();
    renderPlotPreview();
    if (state.mode === 'fixed') renderResults();
  };
  if (plotW) plotW.addEventListener('input', () => {
    if (state.mode === 'fixed') state.fixedFilter.manual = true;
    refreshPlot();
  });
  if (plotH) plotH.addEventListener('input', () => {
    if (state.mode === 'fixed') state.fixedFilter.manual = true;
    refreshPlot();
  });
  if (plotPresets) {
    plotPresets.addEventListener('click', (e) => {
      const btn = e.target.closest('.preset-btn');
      if (!btn) return;
      const w = Number(btn.getAttribute('data-w') || 0);
      const h = Number(btn.getAttribute('data-h') || 0);
      if (w && h) {
        if (plotW) plotW.value = w;
        if (plotH) plotH.value = h;
        if (state.mode === 'fixed') state.fixedFilter.manual = true;
        refreshPlot();
      }
    });
  }
  if (pitModes) {
    pitModes.addEventListener('change', () => {
      state.plot.pitModes = selectedPitModes();
      if (!state.plot.pitModes.has(state.plot.activePattern)) {
        const next = Array.from(state.plot.pitModes)[0];
        if (next) state.plot.activePattern = next;
      }
      if (state.mode === 'fixed') state.fixedFilter.manual = true;
      refreshPlot();
    });
  }
  const btnGenerate = el('btnGenerate');
  if (btnGenerate) btnGenerate.onclick = () => generatePlans();
  const btnReset = el('btnReset');
  if (btnReset) btnReset.onclick = () => {
    state.selected.clear();
    state.fixedFilter.manual = false;
    state.ratioFilter = '';
    if (el('season')) el('season').value = '';
    if (plotW) plotW.value = 1;
    if (plotH) plotH.value = 2;
    if (el('maxKinds')) el('maxKinds').value = 3;
    if (el('topN')) el('topN').value = 12;
    if (pitModes) {
      pitModes.querySelectorAll('input[type="checkbox"]').forEach((input) => {
        const val = String(input.value || '');
        if (state.mode === 'fixed') {
          input.checked = (val === '8' || val === '9' || val === '10');
        } else {
          input.checked = (val === '9' || val === '10');
        }
      });
    }
    syncPlotState();
    renderPlantGrid();
    renderSelectedList();
    generatePlans();
  };
  const ratioFilters = el('ratioFilters');
  if (ratioFilters) {
    ratioFilters.addEventListener('click', (e) => {
      const tag = e.target.closest('.ratio-tag');
      if (!tag) return;
      const ratio = tag.getAttribute('data-ratio') || '';
      state.ratioFilter = ratio;
      renderResults();
    });
  }
  const results = el('results');
  if (results) {
    results.addEventListener('click', (e) => {
      const card = e.target.closest('.plan-card');
      if (!card) return;
      const idx = Number(card.getAttribute('data-plan-idx'));
      if (!Number.isFinite(idx)) return;
      state.activePlanIndex = idx;
      renderResults();
      renderPlotPreview();
    });
  }
  const labelSel = el('labelMode');
  if (labelSel) {
    try { labelSel.value = state.labelMode || 'en'; } catch (e) {}
    labelSel.onchange = () => setLabelMode(labelSel.value).catch(e => setError(String(e)));
  }
  syncToolLayout();
  window.addEventListener('resize', syncToolLayout);
  window.addEventListener('orientationchange', syncToolLayout);
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', syncToolLayout);
  }
}

async function setLabelMode(mode) {
  state.labelMode = String(mode || 'en');
  try { localStorage.setItem('ws_label_mode', state.labelMode); } catch (e) {}
  applyLabelModeUI();
  await ensureI18nNames(state.labelMode);
  await ensureUiStrings(uiLang());
  applyUiStrings();
  applyModeUI();
  buildSeasonOptions();
  updatePlotMeta();
  renderPlantGrid();
  renderSelectedList();
  renderResults();
  renderPlotPreview();
}

function setMode(mode) {
  const next = String(mode || 'fixed');
  if (!['fixed', 'explore', 'single'].includes(next)) {
    state.mode = 'fixed';
  } else {
    state.mode = next;
  }
  try { localStorage.setItem('ws_farming_mode', state.mode); } catch (e) {}
  const plotW = el('plotW');
  const plotH = el('plotH');
  const pitModes = el('pitModes');
  if (state.mode === 'fixed') {
    const w = Number(plotW?.value || 1);
    const h = Number(plotH?.value || 1);
    if (!((w === 1 && h === 1) || (w === 1 && h === 2))) {
      if (plotW) plotW.value = 1;
      if (plotH) plotH.value = 2;
    }
    state.fixedFilter.manual = false;
    if (pitModes) {
      pitModes.querySelectorAll('input[type="checkbox"]').forEach((input) => {
        input.checked = true;
      });
    }
  }
  if (state.mode === 'single') {
    state.activePlanIndex = null;
  }
  state.ratioFilter = '';
  applyModeUI();
  syncPlotState();
  renderPlotPreview();
  renderResults();
}

const FARMING_BOOT = (async () => {
  await loadMeta();
  await ensureI18nNames(state.labelMode);
  await loadAssets();
  await loadFarmingDefs();
  await loadFixedSolutions();
  updateDefsMeta();
  renderPlantGrid();
  renderSelectedList();
  bindEvents();
  if (state.mode === 'fixed') {
    const pitModes = el('pitModes');
    if (pitModes) {
      pitModes.querySelectorAll('input[type="checkbox"]').forEach((input) => {
        input.checked = true;
      });
    }
  }
  syncPlotState();
  renderPlotPreview();
  generatePlans();
})();
window.FARMING_BOOT = FARMING_BOOT;
