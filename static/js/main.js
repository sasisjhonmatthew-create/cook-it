const dropZone = document.getElementById('dropZone');
const photoInput = document.getElementById('photoInput');
const chooseBtn = document.getElementById('chooseBtn');
const previewImg = document.getElementById('previewImg');
const dropIdle = document.getElementById('dropIdle');
const scanBtn = document.getElementById('scanBtn');
const scanStatus = document.getElementById('scanStatus');
const ticketWrap = document.getElementById('ticketWrap');
const emptyState = document.getElementById('emptyState');
const chipList = document.getElementById('chipList');
const addIngredientInput = document.getElementById('addIngredientInput');
const addIngredientBtn = document.getElementById('addIngredientBtn');
const findRecipesBtn = document.getElementById('findRecipesBtn');
const recipeResults = document.getElementById('recipeResults');
const ticketNo = document.getElementById('ticketNo');

let currentIngredients = [];
let savedMealIds = new Set();

// ---------- Navigation ----------
document.querySelectorAll('.nav-pill').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const view = btn.dataset.view;
    document.querySelectorAll('.view').forEach(v => v.hidden = true);
    document.getElementById(`view-${view}`).hidden = false;
    if (view === 'cookbook') loadCookbook();
  });
});

// ---------- Photo selection ----------
chooseBtn.addEventListener('click', () => photoInput.click());
dropZone.addEventListener('click', (e) => { if (e.target === dropZone) photoInput.click(); });

photoInput.addEventListener('change', () => {
  const file = photoInput.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    previewImg.src = e.target.result;
    previewImg.hidden = false;
    dropIdle.hidden = true;
  };
  reader.readAsDataURL(file);
  scanBtn.disabled = false;
  scanStatus.textContent = '';
});

['dragover', 'dragenter'].forEach(evt =>
  dropZone.addEventListener(evt, (e) => { e.preventDefault(); dropZone.style.borderColor = '#5B6E3A'; })
);
['dragleave', 'drop'].forEach(evt =>
  dropZone.addEventListener(evt, (e) => { e.preventDefault(); dropZone.style.borderColor = ''; })
);
dropZone.addEventListener('drop', (e) => {
  const file = e.dataTransfer.files[0];
  if (file) {
    photoInput.files = e.dataTransfer.files;
    photoInput.dispatchEvent(new Event('change'));
  }
});

// ---------- Scan ----------
scanBtn.addEventListener('click', async () => {
  const file = photoInput.files[0];
  if (!file) return;

  scanBtn.disabled = true;
  scanStatus.textContent = 'Reading ingredients…';

  const formData = new FormData();
  formData.append('photo', file);

  try {
    const res = await fetch('/api/scan', { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Scan failed.');

    currentIngredients = data.ingredients;
    renderTicket();
    scanStatus.textContent = data.ingredients.length
      ? `Found ${data.ingredients.length} ingredient${data.ingredients.length > 1 ? 's' : ''}.`
      : 'No known ingredients recognized — add them manually below.';
    ticketNo.textContent = String(Math.floor(Math.random() * 900) + 100);
  } catch (err) {
    scanStatus.textContent = err.message;
  } finally {
    scanBtn.disabled = false;
  }
});

// ---------- Ticket rendering ----------
function renderTicket() {
  ticketWrap.hidden = currentIngredients.length === 0 && false; // always show once scanned
  ticketWrap.hidden = false;
  emptyState.hidden = true;
  chipList.innerHTML = '';
  currentIngredients.forEach((ing) => {
    const chip = document.createElement('span');
    chip.className = 'chip';
    chip.innerHTML = `${ing}<span class="x">✕</span>`;
    chip.addEventListener('click', () => {
      currentIngredients = currentIngredients.filter(i => i !== ing);
      renderTicket();
    });
    chipList.appendChild(chip);
  });
}

addIngredientBtn.addEventListener('click', addIngredient);
addIngredientInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') { e.preventDefault(); addIngredient(); }
});
function addIngredient() {
  const val = addIngredientInput.value.trim().toLowerCase();
  if (!val) return;
  if (!currentIngredients.includes(val)) {
    currentIngredients.push(val);
    renderTicket();
  }
  addIngredientInput.value = '';
}

// ---------- Recipe search ----------
findRecipesBtn.addEventListener('click', async () => {
  if (currentIngredients.length === 0) {
    showToast('Add at least one ingredient first.');
    return;
  }
  recipeResults.innerHTML = `<p class="section-label">searching…</p>`;
  try {
    const res = await fetch('/api/recipes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ingredients: currentIngredients }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Search failed.');
    renderRecipes(data.recipes, recipeResults, true);
  } catch (err) {
    recipeResults.innerHTML = `<p class="section-label">${err.message}</p>`;
  }
});

function renderRecipes(recipes, container, allowSave) {
  container.innerHTML = '';
  if (recipes.length === 0) {
    container.innerHTML = `<p class="section-label">No recipe matches — try adding more ingredients.</p>`;
    return;
  }
  const label = document.createElement('p');
  label.className = 'section-label';
  label.textContent = allowSave ? `${recipes.length} recipes you can make` : `${recipes.length} saved`;
  container.appendChild(label);

  recipes.forEach(r => {
    const card = document.createElement('div');
    card.className = 'recipe-card';
    const matchText = r.matched_ingredients && r.matched_ingredients.length
      ? `matches ${r.matched_ingredients.length} of your ingredients`
      : (r.matched_ingredients_str || '');

    card.innerHTML = `
      <img class="recipe-thumb" src="${r.thumbnail}" alt="${r.title}">
      <div class="recipe-body">
        ${allowSave ? `<div class="recipe-match">${matchText}</div>` : ''}
        <div class="recipe-title">${r.title}</div>
        <div class="recipe-meta">${r.category || ''} ${r.area ? '· ' + r.area : ''}</div>
        <div class="recipe-snippet">${(r.instructions || '').slice(0, 140)}${r.instructions && r.instructions.length > 140 ? '…' : ''}</div>
        <div class="recipe-actions">
          <a class="btn-view" href="${r.source_url}" target="_blank" rel="noopener">View recipe</a>
          ${allowSave ? `<button class="btn-save" data-meal="${r.meal_id}">${savedMealIds.has(r.meal_id) ? 'Saved ✓' : 'Save'}</button>` : ''}
        </div>
        ${!allowSave ? `<button class="btn-remove" data-id="${r.db_id}">Remove from cookbook</button>` : ''}
      </div>
    `;
    container.appendChild(card);

    if (allowSave) {
      card.querySelector('.btn-save').addEventListener('click', async (e) => {
        const btn = e.target;
        btn.disabled = true;
        const res = await fetch('/api/cookbook', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            meal_id: r.meal_id,
            title: r.title,
            thumbnail: r.thumbnail,
            source_url: r.source_url,
            matched_ingredients: r.matched_ingredients,
          }),
        });
        const data = await res.json();
        savedMealIds.add(r.meal_id);
        btn.textContent = 'Saved ✓';
        showToast(data.message);
      });
    } else {
      card.querySelector('.btn-remove').addEventListener('click', async (e) => {
        const id = e.target.dataset.id;
        await fetch(`/api/cookbook/${id}`, { method: 'DELETE' });
        loadCookbook();
        showToast('Removed from cookbook.');
      });
    }
  });
}

// ---------- Cookbook ----------
async function loadCookbook() {
  const grid = document.getElementById('cookbookGrid');
  const empty = document.getElementById('cookbookEmpty');
  const res = await fetch('/api/cookbook');
  const data = await res.json();
  savedMealIds = new Set(data.recipes.map(r => r.meal_id));

  if (data.recipes.length === 0) {
    grid.innerHTML = '';
    empty.hidden = false;
    return;
  }
  empty.hidden = true;
  const mapped = data.recipes.map(r => ({
    ...r,
    db_id: r.id,
    matched_ingredients_str: r.matched_ingredients ? `saved · matched: ${r.matched_ingredients}` : 'saved',
  }));
  renderRecipes(mapped, grid, false);
}

// ---------- Toast ----------
let toastTimer;
function showToast(msg) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2200);
}
