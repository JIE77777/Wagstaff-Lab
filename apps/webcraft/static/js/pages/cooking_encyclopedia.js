const isNarrow = () => window.matchMedia && window.matchMedia('(max-width: 860px)').matches;
const focusPanel = (id) => {
  if (!isNarrow()) return;
  const node = el(id);
  if (node) node.scrollIntoView({ behavior: 'smooth', block: 'start' });
};
const focusDetail = () => focusPanel('detailPanel');
const focusList = () => focusPanel('listPanel');
const backBtn = el('btnBackList');
if (backBtn) backBtn.onclick = () => focusList();

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
    if (typeof renderResultList === 'function') renderResultList();
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
  const listCount = el('listCount');
  if (listCount) listCount.textContent = state.recipes.length ? `${state.recipes.length}` : '';
  for (const nm of state.recipes) {
    const div = document.createElement('div');
    div.className = 'item' + (state.activeRecipe === nm ? ' active' : '');
    div.innerHTML = `<span class="name">${renderItem(nm)}</span><span class="meta"></span>`;
    div.onclick = () => selectRecipe(nm);
    box.appendChild(div);
  }
}

function renderRecipeDetail(rec) {
  const detail = el('detail');
  if (!detail) return;
  if (!rec) {
    detail.innerHTML = `<div class="muted">${escHtml(t('cooking.detail.empty', 'Select a recipe.'))}</div>`;
    return;
  }

  const tags = (rec.tags || []).map(x => `<span class="chip">${renderTagLabel(x) || escHtml(x)}</span>`).join('');
  const card = (rec.card_ingredients || []).map(row => {
    const item = row[0];
    const cnt = row[1];
    return `<div class="line"><span>&bull;</span><span>${renderItem(item)} <span class="mono">x${escHtml(cnt)}</span></span></div>`;
  }).join('');

  const rule = rec.rule || null;

  function renderRule(ruleObj, includeTitle = true) {
    if (!ruleObj) return '';
    const kind = escHtml(ruleObj.kind || '');
    const expr = escHtml(ruleObj.expr || '');
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
  const foodType = String(rec.foodtype || '').replace('FOODTYPE.', '');
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

  detail.innerHTML = `
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

  for (const btn of detail.querySelectorAll('button[data-cook-trace]')) {
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

async function loadGroups() {
  setError('');

  if (state.mode === 'foodtypes') {
    const title = el('groupTitle');
    if (title) title.textContent = t('cooking.group.foodtypes', 'FoodTypes');
    const res = await fetchJson(api('/api/v1/cooking/foodtypes'));
    state.groups = (res.foodtypes || []).map(tpe => ({ name: tpe.name, count: tpe.count }));
  } else if (state.mode === 'tags') {
    const title = el('groupTitle');
    if (title) title.textContent = t('cooking.group.tags', 'Tags');
    const res = await fetchJson(api('/api/v1/cooking/tags'));
    state.groups = (res.tags || []).map(tag => ({
      name: tag.name,
      label: tagLabel(tag.name),
      count: tag.count,
    }));
  } else {
    const title = el('groupTitle');
    if (title) title.textContent = t('cooking.group.all', 'All');
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

  const listTitle = el('listTitle');
  if (listTitle) {
    listTitle.textContent = (state.mode === 'all')
      ? t('cooking.list.all_recipes', 'All recipes')
      : t('cooking.list.recipes', 'Recipes');
  }
  renderRecipeList();
  renderRecipeDetail(null);
}

async function selectRecipe(name) {
  setError('');
  state.activeRecipe = name;
  renderRecipeList();
  const res = await fetchJson(api(`/api/v1/cooking/recipes/${encodeURIComponent(name)}`));
  state.activeRecipeData = res.recipe || null;
  if (state.activeRecipeData && !state.activeRecipeData.name) state.activeRecipeData.name = name;
  renderRecipeDetail(state.activeRecipeData);
  focusDetail();
}

async function doSearch() {
  setError('');
  const q = el('q') ? el('q').value.trim() : '';
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
  const listTitle = el('listTitle');
  if (listTitle) listTitle.textContent = `${t('label.search', 'Search')}: ${q}`;
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
  const listTitle = el('listTitle');
  if (listTitle) listTitle.textContent = t('cooking.list.all_recipes', 'All recipes');
}

function toggleMode() {
  if (state.mode === 'foodtypes') state.mode = 'tags';
  else if (state.mode === 'tags') state.mode = 'all';
  else state.mode = 'foodtypes';
  loadGroups().catch(e => setError(String(e)));
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

const boot = window.COOKING_BOOT || Promise.resolve();
boot.then(async () => {
  if (PAGE_ROLE !== 'encyclopedia') return;
  if (el('groupList')) {
    await loadGroups();
  }
  setView(state.view);
  await showAll();
  initFromUrl();
}).catch(e => setError(String(e)));
