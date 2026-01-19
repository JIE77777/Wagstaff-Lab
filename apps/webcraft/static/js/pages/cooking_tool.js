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

  const asInv = parseInventory(raw);
  if (Object.keys(asInv).length) return asInv;

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

const VIRTUAL_PANEL_MAX_WIDTH = 860;

function isToolMobile() {
  const viewport = window.visualViewport;
  const w = (viewport && viewport.width) || window.innerWidth || document.documentElement.clientWidth || 0;
  if (!w) return false;
  return w <= VIRTUAL_PANEL_MAX_WIDTH;
}

function hasVirtualIngredients() {
  return Boolean(state.virtualIngredientIds && state.virtualIngredientIds.size);
}

function syncVirtualToggleState() {
  if (PAGE_ROLE !== 'tool') return;
  const picker = el('ingredientPicker');
  const toggle = el('ingredientVirtualToggle');
  const panel = el('ingredientVirtualPanel');
  const allow = hasVirtualIngredients() && !isToolMobile();
  if (!allow) state.showVirtualIngredients = false;
  const show = allow && state.showVirtualIngredients;
  if (picker) picker.classList.toggle('show-virtual', show);
  if (toggle) {
    toggle.style.display = allow ? '' : 'none';
    toggle.classList.toggle('active', show);
    toggle.setAttribute('aria-pressed', show ? 'true' : 'false');
  }
  if (panel) panel.style.display = show ? '' : 'none';
}

function syncToolLayout() {
  if (PAGE_ROLE !== 'tool') return;
  setToolViewportVars();
  updateFilterPager();
  syncVirtualToggleState();
}

function updateSlotUi() {
  const slotsHelp = el('slotsHelp');
  const slots = el('slots');
  const ingredientHint = el('ingredientHint');
  const ingredientClear = el('ingredientClear');
  const toolModeToggles = document.querySelectorAll('.tool-mode-toggle');
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
  if (toolModeToggles.length) {
    const isSim = state.view === 'simulate';
    const exploreLabel = t('cooking.mode.explore', 'Explore');
    const simulateLabel = t('cooking.mode.simulate', 'Simulate');
    toolModeToggles.forEach((btn) => {
      btn.innerHTML = `
        <span class="tool-mode-option tool-mode-option--explore">${escHtml(exploreLabel)}</span>
        <span class="tool-mode-option tool-mode-option--simulate">${escHtml(simulateLabel)}</span>
      `;
      btn.dataset.mode = isSim ? 'simulate' : 'explore';
      btn.setAttribute('aria-pressed', isSim ? 'true' : 'false');
      btn.setAttribute('aria-label', `${exploreLabel} / ${simulateLabel}`);
    });
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

function formatConditions(row) {
  const rows = row && Array.isArray(row.conditions) ? row.conditions : [];
  const fmtNum = (num) => {
    const v = Number(num);
    if (!Number.isFinite(v)) return '';
    const out = v.toFixed(1);
    return out.endsWith('.0') ? out.slice(0, -2) : out;
  };
  const opLabel = (op, required) => {
    if (!op) return '';
    if (required === null || required === undefined || required === '') return String(op);
    return `${op} ${fmtNum(required)}`;
  };
  const formatRow = (cond) => {
    const tpe = String(cond.type || '').trim();
    if (tpe === 'name_any') {
      const opts = Array.isArray(cond.options) ? cond.options : [];
      const label = opts.map((v) => itemLabel(v)).filter(Boolean).join(' / ');
      const fallback = opts.filter(Boolean).join(' / ');
      const text = label || fallback || '';
      return {
        type: 'item',
        text: text || t('cooking.conditions.empty', 'No conditions'),
        suffix: opLabel('>=', 1),
        ok: !!cond.ok,
      };
    }
    if (tpe === 'name_sum') {
      const opts = Array.isArray(cond.options) ? cond.options : [];
      const label = opts.map((v) => itemLabel(v)).filter(Boolean).join(' + ');
      const fallback = opts.filter(Boolean).join(' + ');
      const text = label || fallback || '';
      return {
        type: 'item',
        text: text || t('cooking.conditions.empty', 'No conditions'),
        suffix: opLabel('>=', cond.required),
        ok: !!cond.ok,
      };
    }
    const key = String(cond.key || '').trim();
    if (!key) return null;
    const isName = tpe === 'name';
    const label = isName ? itemLabel(key) : tagLabelPlain(key);
    const base = `${label || key}`;
    return {
      type: isName ? 'item' : 'tag',
      text: base,
      suffix: opLabel(String(cond.op || '').trim(), cond.required),
      ok: !!cond.ok,
    };
  };

  if (!rows.length) {
    const empty = escHtml(t('cooking.conditions.empty', 'No conditions'));
    return `<div class="condition-empty">${empty}</div>`;
  }

  const parts = rows.map(formatRow).filter(Boolean);
  const title = escHtml(t('cooking.conditions.title', 'Conditions'));
  const chips = parts.map((part) => {
    const cls = [
      'condition-chip',
      part.type ? `condition-chip--${part.type}` : '',
      part.ok ? 'is-ok' : 'is-miss',
    ].filter(Boolean).join(' ');
    const text = escHtml(String(part.text || '').trim());
    const suffix = part.suffix ? `<span class="condition-op">${escHtml(part.suffix)}</span>` : '';
    return `<span class="${cls}"><span>${text}</span>${suffix}</span>`;
  }).join('');
  return `<div class="condition-title">${title}</div><div class="condition-list">${chips}</div>`;
}

function isConditionsOk(row) {
  if (row && typeof row.conditions_ok === 'boolean') return row.conditions_ok;
  const rows = row && Array.isArray(row.conditions) ? row.conditions : [];
  if (rows.length) return rows.every((c) => !!c.ok);
  const missing = row && Array.isArray(row.missing) ? row.missing : [];
  return !missing.length;
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

  const selectedName = (mode === 'simulate' && res && res.selected && res.selected !== '(none)')
    ? String(res.selected)
    : '';
  const selectedReason = selectedName ? String(res.selected_reason || '') : '';
  const cookable = Array.isArray(res.cookable) ? res.cookable : [];
  const near = Array.isArray(res.near_miss) ? res.near_miss : [];
  const nearTiers = Array.isArray(res.near_miss_tiers) ? res.near_miss_tiers : [];
  const cookableFiltered = selectedName
    ? cookable.filter((row) => String(row.name || '') !== selectedName)
    : cookable;

  if (selectedName) {
    const selectedWrap = document.createElement('div');
    selectedWrap.className = 'result-section result-section--selected';
    const selectedGrid = document.createElement('div');
    selectedGrid.className = 'result-grid result-grid--selected';
    const findRow = (items) => items.find((row) => String(row.name || '') === selectedName);
    let selectedRow = findRow(cookable) || findRow(near);
    if (!selectedRow && nearTiers.length) {
      for (const tier of nearTiers) {
        const items = Array.isArray(tier.items) ? tier.items : [];
        selectedRow = findRow(items);
        if (selectedRow) break;
      }
    }
    const card = document.createElement('div');
    const note = selectedReason ? `<div class="small muted result-note">${escHtml(selectedReason)}</div>` : '';
    if (selectedRow) {
      const conditions = formatConditions(selectedRow);
      const rule = selectedRow.rule_mode ? String(selectedRow.rule_mode).toUpperCase() : '';
      const weightVal = Number(selectedRow.weight);
      const showWeight = Number.isFinite(weightVal) && weightVal !== 1;
      const attrs = renderAttrPills(selectedRow);
      const isOk = isConditionsOk(selectedRow);
      card.className = `result-card ${isOk ? 'is-ok' : 'is-miss'} is-selected`;
      card.innerHTML = `
        <div>${renderItem(selectedName)}</div>
        <div class="result-conditions">${conditions}</div>
        ${attrs ? `<div class="result-attrs">${attrs}</div>` : ''}
        ${note}
        <div class="result-meta">
          <span class="pill">p=${escHtml(Number(selectedRow.priority || 0))}</span>
          ${showWeight ? `<span class="pill pill-weight">w=${escHtml(weightVal)}</span>` : ''}
          ${rule ? `<span class="pill pill-rule">${escHtml(rule)}</span>` : ''}
        </div>
      `;
    } else {
      card.className = 'result-card is-selected';
      card.innerHTML = `
        <div>${renderItem(selectedName)}</div>
        ${note}
      `;
    }
    if (typeof selectRecipe === 'function') {
      card.onclick = () => selectRecipe(selectedName);
    }
    selectedGrid.appendChild(card);
    selectedWrap.appendChild(selectedGrid);
    box.appendChild(selectedWrap);
  }

  const sections = [
    { title: t('cooking.results.cookable', 'Cookable'), items: cookableFiltered },
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

    const grid = document.createElement('div');
    grid.className = 'result-grid';
    for (const row of sec.items) {
      const name = String(row.name || '').trim();
      if (!name) continue;
      const conditions = formatConditions(row);
      const rule = row.rule_mode ? String(row.rule_mode).toUpperCase() : '';
      const weightVal = Number(row.weight);
      const showWeight = Number.isFinite(weightVal) && weightVal !== 1;
      const attrs = renderAttrPills(row);
      const card = document.createElement('div');
      const isOk = isConditionsOk(row);
      card.className = `result-card ${isOk ? 'is-ok' : 'is-miss'}`;
      card.style.animationDelay = `${Math.min(animIdx * 0.03, 0.4)}s`;
      animIdx += 1;
      card.innerHTML = `
        <div>${renderItem(name)}</div>
        <div class="result-conditions">${conditions}</div>
        ${attrs ? `<div class="result-attrs">${attrs}</div>` : ''}
        <div class="result-meta">
          <span class="pill">p=${escHtml(Number(row.priority || 0))}</span>
          ${showWeight ? `<span class="pill pill-weight">w=${escHtml(weightVal)}</span>` : ''}
          ${rule ? `<span class="pill pill-rule">${escHtml(rule)}</span>` : ''}
        </div>
      `;
      if (typeof selectRecipe === 'function') {
        card.onclick = () => selectRecipe(name);
      }
      grid.appendChild(card);
    }
    wrap.appendChild(grid);
    box.appendChild(wrap);
  }
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
    virtual: Boolean(raw.virtual),
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
  box.scrollLeft = 0;
  const items = (state.ingredients || []).filter(it => !it.virtual);
  for (const cat of ING_CATEGORIES) {
    const count = items.filter(it => _ingredientMatchesCategory(it, cat.key)).length;
    if (cat.key === 'other' && !count) continue;
    const btn = document.createElement('button');
    btn.className = 'ingredient-filter' + (state.ingredientFilter === cat.key ? ' active' : '');
    const label = cat.label();
    const countHtml = count ? ` <span class="tag-count">(${count})</span>` : '';
    btn.innerHTML = `<span class="tag-label">${escHtml(label)}</span>${countHtml}`;
    btn.onclick = () => {
      state.ingredientFilter = cat.key;
      renderIngredientFilters();
      renderIngredientGrid();
    };
    box.appendChild(btn);
  }
  updateFilterPager();
}

function renderIngredientGridItems(grid, items) {
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
}

function renderIngredientGrid() {
  const grid = el('ingredientGrid');
  const virtualGrid = el('ingredientGridVirtual');
  if (!grid) return;
  grid.innerHTML = '';
  if (virtualGrid) virtualGrid.innerHTML = '';
  syncVirtualToggleState();
  if (!state.ingredients.length) {
    grid.innerHTML = `<div class="muted small">${escHtml(t('cooking.ingredients.empty', 'Ingredient index not ready.'))}</div>`;
    return;
  }
  const filterFn = (item) => _ingredientMatchesCategory(item, state.ingredientFilter) && _ingredientQueryMatch(item);
  const primary = state.ingredients.filter(it => !it.virtual).filter(filterFn);
  const virtual = state.ingredients.filter(it => it.virtual).filter(filterFn);
  if (!primary.length) {
    grid.innerHTML = `<div class="muted small">${escHtml(t('cooking.ingredients.empty_filter', 'No ingredients match.'))}</div>`;
  } else {
    renderIngredientGridItems(grid, primary);
  }
  if (virtualGrid && state.showVirtualIngredients && !isToolMobile()) {
    renderIngredientGridItems(virtualGrid, virtual);
  }
  updateIngredientSelection();
}

function updateFilterPager() {
  const row = el('ingredientFilters');
  const prev = el('ingredientFilterPrev');
  const next = el('ingredientFilterNext');
  if (!row || !prev || !next) return;
  const maxScroll = Math.max(0, row.scrollWidth - row.clientWidth);
  const atStart = row.scrollLeft <= 2;
  const atEnd = row.scrollLeft >= maxScroll - 2;
  prev.disabled = atStart;
  next.disabled = atEnd;
}

function updateIngredientSelection() {
  const grids = [el('ingredientGrid'), el('ingredientGridVirtual')].filter(Boolean);
  if (!grids.length) return;
  const selected = new Set(parseAvailable(el('slots')?.value || ''));
  for (const grid of grids) {
    for (const btn of grid.querySelectorAll('button.ingredient-item')) {
      const iid = btn.getAttribute('data-id') || '';
      btn.classList.toggle('active', selected.has(iid));
    }
  }
}

function renderSlotPreview() {
  const box = el('slotPreview');
  if (!box) return;
  box.innerHTML = '';
  const inv = parseSlots(el('slots')?.value || '');
  const ids = Object.keys(inv || {}).filter(Boolean);
  if (!ids.length) {
    box.innerHTML = `<div class="slot-empty muted small">${escHtml(t('cooking.slots.empty', 'No ingredients selected.'))}</div>`;
    return;
  }
  const list = [];
  const isSim = state.view === 'simulate';
  ids.sort();
  for (const iid of ids) {
    const count = Math.max(1, Number(inv[iid] || 0));
    const times = isSim ? count : 1;
    for (let i = 0; i < times; i += 1) list.push(iid);
  }
  for (const iid of list) {
    const chip = document.createElement('div');
    chip.className = 'slot-chip';
    chip.innerHTML = `${renderItem(iid)}`;
    chip.onclick = () => {
      if (state.view === 'explore') {
        toggleAvailable(iid, true);
        return;
      }
      updateSlots(iid, -1);
    };
    box.appendChild(chip);
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
    state.virtualIngredientIds = new Set(items.filter(it => it.virtual).map(it => it.id));
    if (!state.virtualIngredientIds.size) state.showVirtualIngredients = false;
  } catch (e) {
    state.ingredients = [];
    state.ingredientSource = '';
    state.virtualIngredientIds = new Set();
    state.showVirtualIngredients = false;
  }
  updateIngredientSourceHint();
  renderIngredientFilters();
  renderIngredientGrid();
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
  renderResultList();
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
    selected: res.result || '',
    selected_reason: res.reason || '',
  };
  renderResultList();

  const result = res.result || '(none)';
  if (el('out')) el('out').textContent = '';

  if (res.recipe) {
    state.activeRecipe = result;
    state.activeRecipeData = res.recipe;
    if (state.activeRecipeData && !state.activeRecipeData.name) state.activeRecipeData.name = result;
    if (typeof renderRecipeDetail === 'function') renderRecipeDetail(state.activeRecipeData);
  }
}

if (PAGE_ROLE === 'tool') {
  document.querySelectorAll('.tool-mode-toggle').forEach((btn) => {
    btn.onclick = () => {
      const next = (state.view === 'simulate') ? 'explore' : 'simulate';
      setView(next);
      const query = window.location.search || '';
      const nextUrl = `${APP_ROOT}/cooking/${next}${query}`;
      if (window.history && window.history.replaceState) {
        window.history.replaceState(null, document.title, nextUrl);
      }
      if (next === 'simulate') {
        doSimulate().catch(e => setError(String(e)));
      } else {
        doExplore().catch(e => setError(String(e)));
      }
    };
  });

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
  const ingVirtualToggle = el('ingredientVirtualToggle');
  if (ingVirtualToggle) {
    ingVirtualToggle.onclick = () => {
      state.showVirtualIngredients = !state.showVirtualIngredients;
      syncVirtualToggleState();
      renderIngredientGrid();
    };
  }

  const filterRow = el('ingredientFilters');
  const filterPrev = el('ingredientFilterPrev');
  const filterNext = el('ingredientFilterNext');
  const scrollFilterRow = (dir) => {
    if (!filterRow) return;
    const offset = Math.max(Math.round(filterRow.clientWidth * 0.9), 120);
    filterRow.scrollBy({ left: dir * offset, behavior: 'smooth' });
  };
  if (filterPrev) filterPrev.onclick = () => scrollFilterRow(-1);
  if (filterNext) filterNext.onclick = () => scrollFilterRow(1);
  if (filterRow) {
    filterRow.addEventListener('scroll', () => updateFilterPager());
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

  syncToolLayout();
  window.addEventListener('resize', syncToolLayout);
  window.addEventListener('orientationchange', syncToolLayout);
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', syncToolLayout);
  }

  const boot = window.COOKING_BOOT || Promise.resolve();
  boot.then(async () => {
    if (el('ingredientPicker') || el('ingredientGrid')) {
      await loadIngredients();
    }
    setView(state.view);
    renderResultList();
  }).catch(e => setError(String(e)));
}
