import { getLanguage, localizeInterface, resultCount, setLanguage, t } from './i18n.js';
import { siteConfig } from './config.js';
import { ApiError, errorMessage, request } from './api.js';
import { authenticatedRequest, ensureAuthenticated, hasAccessToken, login, logout, register, resetAuthentication } from './auth.js';
import { authDestination, authNavigationCancelsPending, authUrl, clearPendingSave, formatPrice, imageUrl, pageSlug, pageUrl, pendingSave, rememberSave, validSlug } from './navigation.js';

const page = document.body.dataset.page;
const content = document.getElementById('page-content');
let noticeTimeout;
let favoriteIds = null;

function element(tag, className = '', text = '') {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function icon(name) {
  const paths = {
    leaf: ['M20 3C9 2 4 7 5 16c6 3 16 0 15-13Z', 'M4 21 16 8'],
    bookmark: ['M6 4h12v17l-6-4-6 4Z'],
    eye: ['M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z', 'M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0'],
    eyeOff: ['m3 3 18 18', 'M10 5a12 12 0 0 1 12 7 17 17 0 0 1-4 5', 'M6 6a18 18 0 0 0-4 6s4 7 10 7a13 13 0 0 0 5-1', 'M10 10a3 3 0 0 0 4 4'],
    trash: ['M3 6h18', 'M8 6V3h8v3', 'm6 6 1 15h10l1-15', 'M10 10v7', 'M14 10v7'],
    retry: ['M20 7v5h-5', 'M4 17v-5h5', 'M6 6a8 8 0 0 1 14 6', 'M18 18A8 8 0 0 1 4 12'],
  };
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('aria-hidden', 'true');
  for (const d of paths[name] || paths.leaf) {
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', d);
    svg.append(path);
  }
  return svg;
}

function notify(message, isError = false) {
  const notice = document.getElementById('notice');
  clearTimeout(noticeTimeout);
  notice.textContent = message;
  notice.classList.toggle('is-error', isError);
  notice.setAttribute('role', isError ? 'alert' : 'status');
  notice.hidden = false;
  noticeTimeout = setTimeout(() => { notice.hidden = true; }, isError ? 10000 : 6000);
}

function setCount(value, word = 'mahsulot') {
  const count = document.getElementById('result-count');
  if (count) count.textContent = resultCount(value, word === 'kategoriya');
}

function showState({ title, message, error = false, retry, link, symbol = 'leaf' }) {
  const state = element('section', `state${error ? ' error' : ''}`);
  const mark = element('span', 'state-symbol');
  mark.append(icon(error ? 'retry' : symbol));
  state.append(mark, element('h2', '', title), element('p', '', message));
  if (retry) {
    const button = element('button', 'button button-secondary', t('Qayta urinish'));
    button.type = 'button';
    button.addEventListener('click', retry);
    state.append(button);
  }
  if (link) {
    const anchor = element('a', 'button button-primary', link.label);
    anchor.href = link.href;
    state.append(anchor);
  }
  content.replaceChildren(state);
}

async function loadPage(loader, loading = t('Ma’lumot yuklanmoqda…')) {
  content.setAttribute('aria-busy', 'true');
  content.replaceChildren(element('p', 'loading', loading));
  try {
    await loader();
  } catch (error) {
    if (page === 'favorites' && error instanceof ApiError && error.status === 401) {
      window.location.replace('/login.html?next=favorites');
      return;
    }
    showState({ title: t('Ma’lumotni yuklab bo‘lmadi'), message: errorMessage(error), error: true, retry: () => loadPage(loader, loading) });
  } finally {
    content.setAttribute('aria-busy', 'false');
  }
}

function updateNavbar() {
  const authLink = document.getElementById('nav-auth-link');
  const logoutButton = document.getElementById('logout-button');
  authLink.hidden = hasAccessToken();
  logoutButton.hidden = !hasAccessToken();
}

function initializeLanguageSwitcher() {
  const languages = element('div', 'language-switch');
  languages.setAttribute('role', 'group');
  languages.setAttribute('aria-label', t('Til tanlash'));
  for (const language of ['uz', 'ru']) {
    const button = element('button', 'language-button', language.toUpperCase());
    button.type = 'button';
    button.dataset.language = language;
    button.lang = language;
    button.setAttribute('aria-label', language === 'uz' ? t('O‘zbekcha') : 'Русский');
    button.setAttribute('aria-pressed', String(getLanguage() === language));
    button.addEventListener('click', () => {
      if (getLanguage() === language) return;
      try {
        setLanguage(language);
        window.location.reload();
      } catch {
        notify(t('Til tanlovini saqlab bo‘lmadi. Brauzer sozlamalarini tekshiring.'), true);
      }
    });
    languages.append(button);
  }
  document.querySelector('.main-nav').append(languages);
  const restoreLanguage = () => {
    if (document.documentElement.lang !== getLanguage()) window.location.reload();
  };
  window.addEventListener('pageshow', restoreLanguage);
  window.addEventListener('storage', (event) => {
    if (event.key === 'herbalStore.language' || event.key === null) restoreLanguage();
  });
}

function initializeLogoutConfirmation(logoutButton) {
  const dialog = element('dialog', 'logout-dialog');
  dialog.id = 'logout-confirmation';
  dialog.setAttribute('aria-labelledby', 'logout-dialog-title');
  dialog.setAttribute('aria-describedby', 'logout-dialog-description');
  const title = element('h2', 'dialog-title', t('Hisobdan chiqish'));
  title.id = 'logout-dialog-title';
  const description = element('p', 'dialog-description', t('Hisobingizdan haqiqatan ham chiqmoqchimisiz?'));
  description.id = 'logout-dialog-description';
  const message = element('p', 'dialog-error');
  message.setAttribute('role', 'alert');
  message.hidden = true;
  const actions = element('div', 'dialog-actions');
  const cancel = element('button', 'button button-secondary', t('Bekor qilish'));
  cancel.id = 'logout-cancel';
  cancel.type = 'button';
  cancel.autofocus = true;
  const confirm = element('button', 'button button-primary logout-confirm-button', t('Ha, chiqish'));
  confirm.id = 'logout-confirm';
  confirm.type = 'button';
  actions.append(cancel, confirm);
  dialog.append(title, description, message, actions);
  document.body.append(dialog);
  let busy = false;

  logoutButton.addEventListener('click', () => {
    if (busy || dialog.open || logoutButton.disabled) return;
    message.hidden = true;
    message.textContent = '';
    dialog.showModal();
    cancel.focus();
  });
  cancel.addEventListener('click', () => { if (!busy) dialog.close(); });
  dialog.addEventListener('cancel', (event) => { if (busy) event.preventDefault(); });
  dialog.addEventListener('close', () => {
    if (!logoutButton.hidden && !logoutButton.disabled) logoutButton.focus();
  });
  confirm.addEventListener('click', async () => {
    if (busy || !dialog.open) return;
    busy = true;
    cancel.disabled = true;
    confirm.disabled = true;
    logoutButton.disabled = true;
    confirm.textContent = t('Chiqilmoqda…');
    logoutButton.textContent = t('Chiqilmoqda…');
    dialog.setAttribute('aria-busy', 'true');
    message.hidden = true;
    try {
      await logout();
      clearPendingSave();
      window.location.assign('/index.html');
    } catch (error) {
      message.textContent = errorMessage(error);
      message.hidden = false;
      busy = false;
      cancel.disabled = false;
      confirm.disabled = false;
      logoutButton.disabled = false;
      confirm.textContent = t('Ha, chiqish');
      logoutButton.textContent = t('Chiqish');
      dialog.removeAttribute('aria-busy');
      cancel.focus();
    }
  });
}

function initializeNavbar() {
  initializeLanguageSwitcher();
  const catalog = document.querySelector('[data-nav="catalog"]');
  const favorites = document.querySelector('[data-nav="favorites"]');
  if (['home', 'category', 'product'].includes(page)) catalog.setAttribute('aria-current', 'page');
  if (page === 'favorites') favorites.setAttribute('aria-current', 'page');
  const authLink = document.getElementById('nav-auth-link');
  if (!['login', 'register'].includes(page)) {
    authLink.textContent = t('Hisob');
    authLink.href = '/favorites.html';
  }
  const logoutButton = document.getElementById('logout-button');
  initializeLogoutConfirmation(logoutButton);
  updateNavbar();
}

function validCatalogText(item) {
  return typeof item?.name === 'string' || item?.translation_available === false && item.name === null;
}

function catalogName(item) {
  return item.translation_available === false ? t('Tarjima hali kiritilmagan') : item.name;
}

function translationNotice() {
  return element('p', 'translation-notice', t('Tanlangan tildagi ma’lumot hali kiritilmagan. Uni do‘kon mas’ullari tekshirganidan keyin administrator qo‘shadi.'));
}

function validProduct(product) {
  return Number.isSafeInteger(product?.id) && product.id > 0 && validSlug(product.slug) && validCatalogText(product);
}

function productVisual(product, detail = false) {
  const visual = element(detail ? 'div' : 'a', `product-visual${detail ? ' detail-image' : ''}`);
  if (!detail) {
    visual.href = pageUrl('product', product.slug);
    visual.setAttribute('aria-label', `${catalogName(product)}: ${t('batafsil ma’lumot')}`);
  }
  const fallback = element('span', 'image-fallback');
  fallback.append(icon('leaf'), element('span', '', t('Rasm mavjud emas')));
  const src = imageUrl(product.image);
  if (src) {
    const image = document.createElement('img');
    image.src = src;
    image.alt = catalogName(product);
    image.loading = detail ? 'eager' : 'lazy';
    image.decoding = 'async';
    image.addEventListener('error', () => { visual.replaceChildren(fallback); }, { once: true });
    visual.append(image);
  } else {
    visual.append(fallback);
  }
  return visual;
}

function availability(product) {
  return element('span', `availability${product.is_available ? '' : ' unavailable'}`, product.is_available ? t('Mavjud') : t('Hozircha mavjud emas'));
}

function buttonLabel(button, text, symbol = 'bookmark') {
  button.replaceChildren(icon(symbol), element('span', '', text));
}

function beginGuestSave(product) {
  rememberSave(product);
  window.location.assign('/register.html');
}

function renderSaveButton(button) {
  if (button.dataset.busy === 'true') return;
  const known = favoriteIds !== null;
  const saved = known && favoriteIds.has(Number(button.dataset.saveProduct));
  if (known) button.setAttribute('aria-pressed', String(saved));
  else button.removeAttribute('aria-pressed');
  button.disabled = button.dataset.busy === 'true';
  buttonLabel(button, known ? saved ? t('Saqlangan') : t('Saqlash') : t('Qayta tekshirish'));
  button.setAttribute('aria-label', `${button.dataset.productName}: ${known ? saved ? t('saqlanganlardan olib tashlash') : t('saqlash') : t('saqlangan holatini qayta tekshirish')}`);
}

function renderSaveButtons() {
  document.querySelectorAll('[data-save-product]').forEach(renderSaveButton);
}

async function synchronizeFavorites() {
  favoriteIds = null;
  document.querySelectorAll('[data-save-product]').forEach((button) => {
    button.disabled = true;
    button.removeAttribute('aria-pressed');
    buttonLabel(button, t('Tekshirilmoqda…'));
  });
  try {
    let products = [];
    if (await ensureAuthenticated()) products = await authenticatedRequest('/api/v1/me/saved-products/');
    if (!Array.isArray(products) || products.some((product) => !Number.isSafeInteger(product?.id) || product.id <= 0)) throw new ApiError(502);
    favoriteIds = new Set(products.map((product) => product.id));
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) favoriteIds = new Set();
    else notify(`${t('Saqlangan holatini tekshirib bo‘lmadi.')} ${errorMessage(error)}`, true);
  } finally {
    updateNavbar();
    renderSaveButtons();
  }
}

function saveButton(product, detail = false) {
  const button = element('button', detail ? 'button button-secondary detail-save' : 'save-button');
  button.type = 'button';
  button.dataset.saveProduct = String(product.id);
  button.dataset.productName = catalogName(product);
  renderSaveButton(button);
  button.addEventListener('click', async () => {
    if (button.disabled) return;
    if (favoriteIds === null) {
      await synchronizeFavorites();
      return;
    }
    const wasSaved = favoriteIds.has(product.id);
    const authenticate = () => {
      if (wasSaved) {
        clearPendingSave();
        window.location.assign('/login.html?next=favorites');
      } else {
        beginGuestSave(product);
      }
    };
    button.dataset.busy = 'true';
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    buttonLabel(button, wasSaved ? t('O‘chirilmoqda…') : t('Saqlanmoqda…'));
    try {
      if (!await ensureAuthenticated()) {
        authenticate();
        return;
      }
      if (wasSaved) {
        await authenticatedRequest(`/api/v1/me/saved-products/${product.id}/`, { method: 'DELETE' });
        favoriteIds.delete(product.id);
        notify(t('Mahsulot saqlanganlardan o‘chirildi.'));
      } else {
        const data = await authenticatedRequest('/api/v1/me/saved-products/', { method: 'POST', body: { product_id: product.id } });
        favoriteIds.add(product.id);
        notify(data?.message === 'Mahsulot avval saqlangan.' ? t('Mahsulot avvaldan saqlangan.') : t('Mahsulot saqlandi.'));
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        try { authenticate(); } catch (storageError) { notify(storageError.message, true); }
      } else if (wasSaved && error instanceof ApiError && error.status === 404) {
        favoriteIds.delete(product.id);
        notify(t('Mahsulot allaqachon saqlanganlardan o‘chirilgan.'));
      } else {
        notify(error instanceof ApiError && error.status === 400 ? t('Mahsulotni saqlab bo‘lmadi. U katalogdan olib tashlangan bo‘lishi mumkin.') : errorMessage(error), true);
      }
    } finally {
      delete button.dataset.busy;
      button.removeAttribute('aria-busy');
      updateNavbar();
      renderSaveButtons();
    }
  });
  return button;
}

function productCard(product, { removable = false, onRemove } = {}) {
  if (!validProduct(product)) throw new ApiError(502);
  const card = element('article', 'product-card');
  card.dataset.productId = String(product.id);
  card.append(productVisual(product));
  const info = element('div', 'product-card-content');
  const title = element('h2', 'product-name');
  const link = element('a', '', catalogName(product));
  link.href = pageUrl('product', product.slug);
  title.append(link);
  info.append(title, availability(product));
  const footer = element('div', 'product-card-footer');
  info.append(element('span', 'price', formatPrice(product.price)));
  const details = element('a', 'button button-secondary details-button', t('Batafsil'));
  details.href = pageUrl('product', product.slug);
  details.setAttribute('aria-label', `${catalogName(product)}: ${t('batafsil ma’lumot')}`);
  footer.append(details);
  if (removable) {
    const button = element('button', 'save-button remove-button');
    button.type = 'button';
    button.dataset.removeProduct = String(product.id);
    button.setAttribute('aria-label', `${catalogName(product)}: ${t('saqlanganlardan olib tashlash')}`);
    buttonLabel(button, t('O‘chirish'), 'trash');
    button.addEventListener('click', async () => {
      if (button.disabled) return;
      button.disabled = true;
      buttonLabel(button, t('O‘chirilmoqda…'), 'trash');
      try {
        await authenticatedRequest(`/api/v1/me/saved-products/${product.id}/`, { method: 'DELETE' });
        card.remove();
        onRemove(product.id);
        notify(t('Mahsulot saqlanganlardan o‘chirildi.'));
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          window.location.assign('/login.html?next=favorites');
          return;
        }
        if (error instanceof ApiError && error.status === 404) {
          card.remove();
          onRemove(product.id);
          notify(t('Mahsulot allaqachon saqlanganlardan o‘chirilgan.'));
          return;
        }
        notify(errorMessage(error), true);
        button.disabled = false;
        buttonLabel(button, t('O‘chirish'), 'trash');
      }
    });
    footer.append(button);
  } else {
    footer.append(saveButton(product));
  }
  info.append(footer);
  if (removable && typeof product.saved_at === 'string') {
    const date = new Date(product.saved_at);
    if (!Number.isNaN(date.getTime())) {
      const parts = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Tashkent', day: '2-digit', month: '2-digit', year: 'numeric' }).formatToParts(date);
      const part = (type) => parts.find((value) => value.type === type).value;
      const savedDate = element('time', 'saved-date', `${t('Saqlangan:')} ${part('day')}.${part('month')}.${part('year')}`);
      savedDate.dateTime = product.saved_at;
      info.append(savedDate);
    }
  }
  card.append(info);
  return card;
}

async function homePage() {
  const categories = await request('/api/v1/categories/');
  if (!Array.isArray(categories)) throw new ApiError(502);
  setCount(categories.length, 'kategoriya');
  if (!categories.length) {
    showState({ title: t('Katalog tez orada yangilanadi'), message: t('Hozircha kategoriyalar qo‘shilmagan. Keyinroq qaytib ko‘ring.') });
    return;
  }
  const grid = element('div', 'category-grid');
  for (const category of categories) {
    if (!validSlug(category?.slug) || !validCatalogText(category)) throw new ApiError(502);
    const card = element('a', 'category-card');
    card.href = pageUrl('category', category.slug);
    const symbol = element('span', 'category-symbol');
    symbol.append(icon('leaf'));
    const arrow = element('span', 'category-arrow', '↗');
    arrow.setAttribute('aria-hidden', 'true');
    card.append(symbol, element('h3', '', catalogName(category)), element('p', '', t('Mahsulotlarni ko‘rish')), arrow);
    grid.append(card);
  }
  content.replaceChildren(grid);
}

async function categoryPage() {
  const slug = pageSlug();
  if (!slug) {
    showState({ title: t('Kategoriya havolasi noto‘g‘ri'), message: t('Bosh sahifadan kerakli kategoriyani tanlang.'), link: { label: t('Kategoriyalarni ko‘rish'), href: '/index.html' } });
    return;
  }
  const data = await request(`/api/v1/categories/${encodeURIComponent(slug)}/products/`);
  if (!validSlug(data?.category?.slug) || !validCatalogText(data.category) || !Array.isArray(data.products)) throw new ApiError(502);
  document.getElementById('page-title').textContent = catalogName(data.category);
  document.title = `${catalogName(data.category)} — ${siteConfig.name}`;
  setCount(data.products.length);
  if (!data.products.length) {
    showState({ title: t('Bu kategoriyada hali mahsulot yo‘q'), message: t('Boshqa kategoriyalarni ko‘ring yoki keyinroq qaytib keling.'), link: { label: t('Kategoriyalarni ko‘rish'), href: '/index.html' } });
    return;
  }
  const grid = element('div', 'product-grid');
  for (const product of data.products) grid.append(productCard(product));
  content.replaceChildren(grid);
  await synchronizeFavorites();
}

async function productPage() {
  const slug = pageSlug();
  if (!slug) {
    showState({ title: t('Mahsulot havolasi noto‘g‘ri'), message: t('Katalogdan kerakli mahsulotni tanlang.'), link: { label: t('Katalogni ko‘rish'), href: '/index.html' } });
    return;
  }
  const product = await request(`/api/v1/products/${encodeURIComponent(slug)}/`);
  if (!validProduct(product) || !validSlug(product.category?.slug) || !validCatalogText(product.category) || !(typeof product.detailed_information === 'string' || product.translation_available === false && product.detailed_information === null)) throw new ApiError(502);
  document.title = `${catalogName(product)} — ${siteConfig.name}`;
  const back = document.getElementById('product-back');
  back.href = pageUrl('category', product.category.slug);
  back.replaceChildren(element('span', '', '←'), document.createTextNode(` ${t('Mahsulotlarga qaytish')}`));
  const detail = element('article', 'product-detail');
  detail.dataset.productId = String(product.id);
  detail.append(productVisual(product, true));
  const info = element('div', 'detail-info');
  const category = element('a', 'product-category', catalogName(product.category));
  category.href = pageUrl('category', product.category.slug);
  const title = element('h1', 'page-title', catalogName(product));
  title.id = 'page-title';
  info.append(category, title, availability(product), element('span', 'price', formatPrice(product.price)), element('p', 'product-description', product.description || ''), saveButton(product, true), element('p', 'save-caption', t('Saqlangan mahsulotlaringizni hisobingizdan ko‘rishingiz mumkin.')));
  detail.append(info);
  const instructions = element('section', 'detail-instructions');
  instructions.append(element('h2', '', t('Batafsil ma’lumot va qo‘llanma')));
  if (product.translation_available === false) instructions.append(translationNotice());
  else instructions.append(element('div', 'instruction-text', product.detailed_information));
  content.replaceChildren(detail, instructions);
  await synchronizeFavorites();
}

function emptyFavorites() {
  showState({ title: t('Birinchi tanlovingizni saqlang'), message: t('Hozircha saqlangan mahsulotlaringiz yo‘q. Katalogdagi yoqtirgan mahsulotingiz yonida “Saqlash”ni bosing.'), symbol: 'bookmark', link: { label: t('Katalogni ko‘rish'), href: '/index.html' } });
}

async function favoritesPage() {
  const products = await authenticatedRequest('/api/v1/me/saved-products/');
  if (!Array.isArray(products)) throw new ApiError(502);
  updateNavbar();
  let count = products.length;
  setCount(count);
  if (!count) {
    emptyFavorites();
    return;
  }
  const grid = element('div', 'product-grid');
  const onRemove = () => {
    count -= 1;
    setCount(count);
    if (!count) emptyFavorites();
  };
  for (const product of products) grid.append(productCard(product, { removable: true, onRemove }));
  content.replaceChildren(grid);
}

function initializeAuthPage() {
  const form = document.getElementById('auth-form');
  const username = document.getElementById('username');
  const password = document.getElementById('password');
  const passwordToggle = document.getElementById('password-toggle');
  passwordToggle.replaceChildren(icon('eye'));
  passwordToggle.addEventListener('click', () => {
    const visible = password.type === 'password';
    password.type = visible ? 'text' : 'password';
    passwordToggle.setAttribute('aria-pressed', String(visible));
    passwordToggle.setAttribute('aria-label', visible ? t('Parolni yashirish') : t('Parolni ko‘rsatish'));
    passwordToggle.replaceChildren(icon(visible ? 'eyeOff' : 'eye'));
  });
  const submit = document.getElementById('auth-submit');
  const message = document.getElementById('form-message');
  const switchLink = document.getElementById('switch-auth');
  const cancel = document.getElementById('cancel-auth');
  const pending = pendingSave();
  let authenticated = false;
  let busy = false;
  if (pending) {
    document.getElementById('auth-context').textContent = t('Hisobga kirganingizdan so‘ng tanlagan mahsulotingiz avtomatik saqlanadi.');
    cancel.href = pending.origin;
    cancel.replaceChildren(element('span', '', '←'), document.createTextNode(` ${t('Bekor qilish va mahsulotlarga qaytish')}`));
  }
  switchLink.href = authUrl(page === 'register' ? 'login' : 'register');
  cancel.addEventListener('click', clearPendingSave);
  document.addEventListener('click', (event) => {
    const anchor = event.target.closest?.('a[href]');
    if (!anchor || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    if (anchor.hasAttribute('download') || anchor.target && anchor.target.toLowerCase() !== '_self') return;
    if (authNavigationCancelsPending(anchor.href)) clearPendingSave();
  });

  function fieldError(field, text) {
    const error = document.getElementById(`${field.id}-error`);
    error.textContent = text;
    error.hidden = !text;
    field.setAttribute('aria-invalid', text ? 'true' : 'false');
  }

  function clearErrors() {
    fieldError(username, '');
    fieldError(password, '');
    message.hidden = true;
    message.classList.remove('success');
  }

  function formMessage(text, success = false) {
    message.textContent = text;
    message.classList.toggle('success', success);
    message.hidden = false;
    message.focus();
  }

  async function finishAuthentication() {
    const intent = pendingSave();
    if (intent) {
      try {
        await authenticatedRequest('/api/v1/me/saved-products/', { method: 'POST', body: { product_id: intent.productId } });
        clearPendingSave();
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          window.location.assign(authUrl('login'));
          return;
        }
        if (error instanceof ApiError && error.status === 400) {
          clearPendingSave();
          formMessage(t('Hisobga kirdingiz. Tanlangan mahsulot katalogdan olib tashlangani uchun saqlanmadi.'), true);
          submit.textContent = t('Saqlanganlarga o‘tish →');
        } else {
          formMessage(`${t('Hisobga kirdingiz, lekin mahsulot hali saqlanmadi.')} ${errorMessage(error)}`);
          submit.textContent = t('Saqlashni qayta urinish →');
        }
        return;
      }
    }
    window.location.assign(authDestination());
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (busy) return;
    clearErrors();
    if (!authenticated) {
      if (!username.value.trim()) fieldError(username, t('Foydalanuvchi nomini kiriting.'));
      if (!password.value) fieldError(password, t('Parol kiriting.'));
      if (!username.value.trim() || !password.value) {
        (!username.value.trim() ? username : password).focus();
        return;
      }
    }
    busy = true;
    submit.disabled = true;
    const original = submit.textContent;
    submit.textContent = authenticated ? t('Saqlanmoqda…') : t('Tekshirilmoqda…');
    try {
      if (!authenticated) {
        await (page === 'register' ? register : login)(username.value, password.value);
        authenticated = true;
        password.value = '';
        password.type = 'password';
        passwordToggle.disabled = true;
        passwordToggle.setAttribute('aria-pressed', 'false');
        passwordToggle.setAttribute('aria-label', t('Parolni ko‘rsatish'));
        passwordToggle.replaceChildren(icon('eye'));
        username.disabled = true;
        password.disabled = true;
        switchLink.hidden = true;
        updateNavbar();
      }
      await finishAuthentication();
    } catch (error) {
      if (error instanceof ApiError && error.status === 400) {
        if (error.data?.username) fieldError(username, t('Foydalanuvchi nomi band yoki unda ruxsat etilmagan belgilar bor. Boshqa nom kiriting.'));
        if (error.data?.password) fieldError(password, t('Kuchliroq parol tanlang: kamida 8 ta belgidan iborat, foydalanuvchi nomiga o‘xshamaydigan, keng tarqalgan bo‘lmagan va faqat raqamlardan tuzilmagan parol.'));
        formMessage(t('Kiritilgan ma’lumotni tekshiring.'));
      } else if (error instanceof ApiError && error.status === 401) {
        formMessage(t('Foydalanuvchi nomi yoki parol noto‘g‘ri. Qayta tekshirib ko‘ring.'));
      } else {
        formMessage(errorMessage(error));
      }
      submit.textContent = original;
    } finally {
      busy = false;
      submit.disabled = false;
      if (submit.textContent === t('Tekshirilmoqda…') || submit.textContent === t('Saqlanmoqda…')) submit.textContent = original;
    }
  });
}

function initializeBranding() {
  document.querySelectorAll('[data-brand-name]').forEach((node) => { node.textContent = siteConfig.name; });
  document.querySelectorAll('[data-brand-home]').forEach((node) => { node.setAttribute('aria-label', `${siteConfig.name}: ${t('Bosh sahifa')}`); });
  const title = document.querySelector('title');
  if (title?.dataset.pageTitle) document.title = `${t(title.dataset.pageTitle)} — ${siteConfig.name}`;
  const description = document.querySelector('meta[name="description"]');
  if (description) description.content = `${siteConfig.name} — ${t('Toshkentdagi dorivor giyohlar va tabiiy mahsulotlar axborot katalogi.')}`;
  const logo = imageUrl(siteConfig.logoUrl);
  if (logo) document.querySelectorAll('[data-brand-logo]').forEach((mark) => {
    const fallback = mark.firstElementChild;
    const image = document.createElement('img');
    image.alt = '';
    image.hidden = true;
    image.addEventListener('load', () => { image.hidden = false; if (fallback) fallback.setAttribute('hidden', ''); }, { once: true });
    image.addEventListener('error', () => { image.remove(); if (fallback) fallback.removeAttribute('hidden'); }, { once: true });
    mark.append(image);
    image.src = logo;
  });
}

localizeInterface();
initializeBranding();
initializeNavbar();
if (['login', 'register'].includes(page)) {
  initializeAuthPage();
} else {
  clearPendingSave();
  window.addEventListener('pageshow', (event) => {
    clearPendingSave();
    if (event.persisted && loaders[page]) loadPage(async () => {
      await resetAuthentication();
      updateNavbar();
      await loaders[page]();
    });
  });
  const loaders = { home: homePage, category: categoryPage, product: productPage, favorites: favoritesPage };
  if (loaders[page]) loadPage(loaders[page]);
}
