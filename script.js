/* beautiful.js
  Place in: static/js/beautiful.js
  Expects backend API at /api (same origin). If your backend is on another host, change API_BASE.
*/
const API_BASE = '/api';

function qs(sel, ctx=document) { return ctx.querySelector(sel); }
function qsa(sel, ctx=document) { return Array.from(ctx.querySelectorAll(sel)); }
const yearEl = qs('#year'); if (yearEl) yearEl.textContent = new Date().getFullYear();

// UI elements
const ingredientInput = qs('#ingredientInput');
const notesInput = qs('#notesInput');
const findBtn = qs('#findBtn');
const recipeContainer = qs('#recipeContainer');
const noResults = qs('#noResults');
const authModal = qs('#authModal');
const btnLogin = qs('#btn-login');
const btnSignup = qs('#btn-signup');
const btnLogout = qs('#btn-logout');
const usageText = qs('#usageText');

// modal elements
const modalClose = qs('#modalClose');
const tabLogin = qs('#tabLogin');
const tabSignup = qs('#tabSignup');
const loginForm = qs('#loginForm');
const signupForm = qs('#signupForm');

// mobile nav
const mobileToggle = qs('#mobile-menu-toggle');
const mainNav = qs('#main-nav');

mobileToggle && mobileToggle.addEventListener('click', e=>{
  const open = mainNav.classList.toggle('open');
  mobileToggle.setAttribute('aria-expanded', String(open));
});

// open auth modal
btnLogin && btnLogin.addEventListener('click', ()=>openAuthModal('login'));
btnSignup && btnSignup.addEventListener('click', ()=>openAuthModal('signup'));
modalClose && modalClose.addEventListener('click', closeAuthModal);

// switch tabs
tabLogin && tabLogin.addEventListener('click', ()=>switchAuthTab('login'));
tabSignup && tabSignup.addEventListener('click', ()=>switchAuthTab('signup'));

function openAuthModal(tab='login'){
  authModal.classList.remove('hidden');
  authModal.classList.add('fade-in');
  switchAuthTab(tab);
}
function closeAuthModal(){
  authModal.classList.add('hidden');
}
function switchAuthTab(tab){
  if(tab==='login'){
    tabLogin.classList.add('active'); tabSignup.classList.remove('active');
    loginForm.classList.remove('hidden'); signupForm.classList.add('hidden');
  } else {
    tabSignup.classList.add('active'); tabLogin.classList.remove('active');
    signupForm.classList.remove('hidden'); loginForm.classList.add('hidden');
  }
}

// example chips
qsa('.chip').forEach(ch => ch.addEventListener('click', e => {
  const text = ch.dataset.example || ch.textContent || '';
  ingredientInput.value = text;
  ingredientInput.focus();
}));

// helpers
async function api(path, method='GET', body=null) {
  const opts = {method, headers: {'Content-Type':'application/json'}, credentials:'include'};
  if(body) opts.body = JSON.stringify(body);
  const res = await fetch(API_BASE + path, opts);
  let data;
  try { data = await res.json(); } catch(e) { data = null; }
  if(!res.ok){
    if(data) throw data;
    throw { error: res.statusText || 'Request failed' };
  }
  return data;
}

// fetch current user info
async function refreshMe(){
  try {
    const me = await api('/me');
    if(me && me.user){
      usageText.textContent = `${me.user} • ${me.used_today}/${me.limit} today`;
      btnLogin?.classList.add('hidden');
      btnSignup?.classList.add('hidden');
      btnLogout?.classList.remove('hidden');
    } else {
      usageText.textContent = '';
      btnLogin?.classList.remove('hidden');
      btnSignup?.classList.remove('hidden');
      btnLogout?.classList.add('hidden');
    }
  } catch (e){
    console.error('me error', e);
  }
}

// login / signup handlers
loginForm && loginForm.addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const u = qs('#loginUsername').value.trim();
  const p = qs('#loginPassword').value;
  qs('#loginError').textContent = '';
  try {
    await api('/login', 'POST', {username:u, password:p});
    closeAuthModal();
    await refreshMe();
  } catch (err) {
    qs('#loginError').textContent = err.error || 'Login failed';
  }
});

signupForm && signupForm.addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const u = qs('#signupUsername').value.trim();
  const p = qs('#signupPassword').value;
  qs('#signupError').textContent = '';
  try {
    await api('/signup', 'POST', {username:u, password:p});
    // auto-login on success: call login
    await api('/login', 'POST', {username:u, password:p});
    closeAuthModal();
    await refreshMe();
  } catch (err) {
    qs('#signupError').textContent = err.error || 'Signup failed';
  }
});

btnLogout && btnLogout.addEventListener('click', async () => {
  await api('/logout', 'POST');
  await refreshMe();
});

// building skeletons
function showSkeletons(n=3){
  recipeContainer.innerHTML = '';
  for(let i=0;i<n;i++){
    const s = document.createElement('div');
    s.className = 'recipe-card skeleton';
    s.style.minHeight = '140px';
    recipeContainer.appendChild(s);
  }
}

// render recipes
function renderRecipes(recipes){
  recipeContainer.innerHTML = '';
  if(!recipes || recipes.length===0){
    noResults.hidden = false;
    return;
  }
  noResults.hidden = true;
  recipes.forEach((r, idx) => {
    const el = document.createElement('article');
    el.className = 'recipe-card fade-in';
    el.setAttribute('role','listitem');

    // image: prefer provided image, else use Unsplash random by title or keywords
    const imgSrc = r.image || `https://source.unsplash.com/collection/1199681/400x300?sig=${idx}`; // fallback
    const img = document.createElement('img');
    img.className = 'recipe-img';
    img.alt = r.title || 'Recipe image';
    img.loading = 'lazy';
    img.src = imgSrc;

    const head = document.createElement('div'); head.className = 'recipe-head';
    const txt = document.createElement('div'); txt.style.flex='1';
    const title = document.createElement('div'); title.className='title'; title.textContent = r.title || 'Untitled';
    const desc = document.createElement('div'); desc.className='desc'; desc.textContent = r.description || '';

    txt.appendChild(title); txt.appendChild(desc);

    head.appendChild(img); head.appendChild(txt);

    el.appendChild(head);

    // ingredients pills
    const ingWrap = document.createElement('div'); ingWrap.className = 'ingredients';
    (r.ingredients || []).slice(0,6).forEach(i => {
      const pill = document.createElement('span'); pill.className='pill'; pill.textContent = i;
      ingWrap.appendChild(pill);
    });
    el.appendChild(ingWrap);

    // uses / meta
    const uses = document.createElement('div'); uses.className='uses';
    uses.innerHTML = `<strong>Prep:</strong> ${r.prep_minutes||'-'} min • <strong>Cook:</strong> ${r.cook_minutes||'-'} min`;
    el.appendChild(uses);

    // details toggle
    const toggle = document.createElement('button'); toggle.className='btn btn-ghost'; toggle.textContent='Show steps';
    toggle.style.marginTop='8px';
    const details = document.createElement('div'); details.className='card-details';
    // build step list
    const stepsList = document.createElement('ol');
    (r.steps || []).forEach(s => {
      const li = document.createElement('li'); li.textContent = s; stepsList.appendChild(li);
    });
    details.appendChild(stepsList);

    toggle.addEventListener('click', () => {
      const open = details.classList.toggle('open');
      toggle.textContent = open ? 'Hide steps' : 'Show steps';
      // smooth height animation
      if(open){
        details.style.height = details.scrollHeight + 'px';
      } else {
        details.style.height = '0px';
      }
    });

    el.appendChild(toggle);
    el.appendChild(details);

    recipeContainer.appendChild(el);
  });
}

/* ERROR UI helper */
function showError(msg){
  recipeContainer.innerHTML = `<div class="no-results">${escapeHtml(msg)}</div>`;
}

/* small html escape */
function escapeHtml(s){ return String(s||'').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }

/* main generate function */
async function generateRecipes(ingredients, notes, filters = {}, limit=3){
  try {
    showSkeletons(3);
    const payload = { ingredients, notes, filters, limit };
    const res = await api('/generate', 'POST', payload);
    if(res && res.error && res.checkout_url){
      // limit reached: redirect to payment flow
      if(confirm('Daily limit reached. Go to payment to unlock more recipes?')) {
        window.location.href = res.checkout_url;
      } else {
        showError(res.message || 'Limit reached.');
      }
      return;
    }
    if(res && res.recipes){
      renderRecipes(res.recipes);
      await refreshMe(); // update usage
    } else {
      showError('No recipes returned from server.');
    }
  } catch (err) {
    console.error(err);
    if(err && err.error) showError(err.error);
    else showError('Network or server error.');
  }if (res && res.error && res.checkout_url) {
  if (confirm('Daily limit reached. Do you want to upgrade?')) {
    window.location.href = res.checkout_url;
  }
}

}

/* wire find button and form */
qs('#searchForm').addEventListener('submit', ev => {
  ev.preventDefault();
  if(!ingredientInput.value.trim()){ showError('Please enter ingredients'); return; }
  const filters = {
    vegetarian: !!qs('#filterVegetarian')?.checked,
    vegan: !!qs('#filterVegan')?.checked,
    gluten_free: !!qs('#filterGlutenFree')?.checked,
    dairy_free: !!qs('#filterDairyFree')?.checked
  };
  generateRecipes(ingredientInput.value.trim(), notesInput.value.trim(), filters, 3);
});

// initial load
(async function init(){
  await refreshMe();
  // optional: show sample recipes on load (fetch with a friendly example)
  // generateRecipes('tomato, basil, mozzarella', 'vegetarian', {}, 2);
})();
