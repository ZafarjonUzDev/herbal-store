import { ApiError, request } from '../js/api.js';
import { authenticatedRequest, ensureAuthenticated, hasAccessToken, login, logout, register, resetAuthentication } from '../js/auth.js';
import { authDestination, authNavigationCancelsPending, authUrl, clearPendingSave, formatPrice, imageUrl, pageUrl, pendingSave, rememberSave, validSlug } from '../js/navigation.js';
import { mountFixture, restoreFixture } from './fixture.js';
import { getLanguage, LANGUAGE_KEY, resultCount, setLanguage, t } from '../js/i18n.js';

const output = document.getElementById('test-results');
const originalFetch = window.fetch;
const originalPending = sessionStorage.getItem('herbalStore.pendingSave');
const originalLanguage = localStorage.getItem(LANGUAGE_KEY);
setLanguage('uz');
const originalUrl = window.location.href;
let calls = [];
let handler;
let passed = 0;
let failed = 0;
const results = [];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function json(data, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });
}

function mock(fn) {
  calls = [];
  handler = fn;
  window.fetch = async (path, options) => {
    const call = { path, ...options, body: options.body ? JSON.parse(options.body) : null };
    calls.push(call);
    return handler(call);
  };
}

function csrf(call) {
  if (call.path.endsWith('/csrf/')) return json({ csrfToken: 'test-csrf' });
  assert(call.headers['X-CSRFToken'] === 'test-csrf', 'Auth POST requires CSRF header.');
  assert(call.credentials === 'same-origin', 'Cookie flow must use same-origin credentials.');
  assert(call.method === 'POST', 'Auth mutation must be POST.');
  return null;
}

async function rejects(fn, status) {
  try { await fn(); } catch (error) {
    assert(error instanceof ApiError && error.status === status, `Expected safe API error ${status}.`);
    return;
  }
  throw new Error(`Expected rejection ${status}.`);
}

async function test(name, fn) {
  try {
    await fn();
    passed += 1;
    results.push(`PASS ${name}`);
  } catch (error) {
    failed += 1;
    results.push(`FAIL ${name}: ${error.message}`);
  } finally {
    restoreFixture();
    setLanguage('uz');
  }
  output.textContent = results.join('\n');
}

async function waitFor(check, message) {
  const deadline = Date.now() + 8000;
  while (Date.now() < deadline) {
    if (check()) return;
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
  throw new Error(message);
}

const category = { id: 1, name: 'Giyohlar', slug: 'giyohlar' };
const product = {
  id: 7, slug: 'demo-product', name: 'Sinov giyohi', category,
  price: '35000.00', image: null, is_available: true,
  description: 'Qisqa tavsif.', detailed_information: 'Do‘kon tasdiqlagan qadoq yo‘riqnomasi.',
  saved_at: '2026-10-13T21:30:00Z',
};

async function appFixture(page, overrides = {}) {
  mock((call) => csrf(call) || json(null, 204));
  await logout();
  const fixture = await mountFixture(page, { product, category, saved: false, ...overrides }, originalFetch);
  await waitFor(() => ['login', 'register'].includes(page)
    ? document.querySelector('#password-toggle')
    : document.querySelector('#page-content[aria-busy="false"]'), `${page} fixture did not initialize.`);
  return fixture;
}

await test('Narxlar Decimal string sifatida aniq formatlanadi', () => {
  assert(formatPrice('35000.00') === '35\u00a0000 so‘m', 'Whole UZS price.');
  assert(formatPrice('9999999999.99') === '9\u00a0999\u00a0999\u00a0999,99 so‘m', 'Maximum decimal precision.');
  assert(formatPrice('0.05') === '0,05 so‘m', 'Fraction must preserve leading zero.');
  assert(formatPrice('-1.00') === 'Narx ko‘rsatilmagan', 'Invalid negative display.');
});

await test('Havolalar, slug va rasmlar same-origin chegarasida', () => {
  assert(validSlug('demo_product-1') && !validSlug('../admin') && !validSlug('x?next=evil'), 'Slug validation.');
  assert(pageUrl('product', 'demo_product-1') === '/product.html?slug=demo_product-1', 'Product route.');
  assert(imageUrl('https://external.invalid/image.jpg') === null, 'External image blocked.');
  assert(imageUrl('javascript:alert(1)') === null, 'Unsafe image protocol blocked.');
  assert(imageUrl('/media/demo.jpg') === `${window.location.origin}/media/demo.jpg`, 'Local media allowed.');
  history.replaceState(null, '', '/tests/index.html?next=https://external.invalid');
  assert(authUrl() === '/login.html' && authDestination() === '/favorites.html', 'Open redirect rejected.');
  history.replaceState(null, '', originalUrl);
});

await test('Pending Save faqat tekshirilgan ID, slug va lokal origin saqlaydi', () => {
  clearPendingSave();
  rememberSave({ id: 7, slug: 'demo-product' });
  const pending = pendingSave();
  assert(pending.productId === 7 && pending.origin === '/product.html?slug=demo-product', 'Validated intent.');
  const stored = JSON.parse(sessionStorage.getItem('herbalStore.pendingSave'));
  assert(Object.keys(stored).sort().join(',') === 'origin,productId,slug', 'Only non-secret fields stored.');
  sessionStorage.setItem('herbalStore.pendingSave', JSON.stringify({ productId: 7, slug: 'demo', origin: '//external.invalid' }));
  assert(pendingSave() === null, 'External return route rejected.');
  sessionStorage.setItem('herbalStore.pendingSave', '{broken');
  assert(pendingSave() === null, 'Malformed storage cleared.');
  sessionStorage.setItem('herbalStore.pendingSave', JSON.stringify({ productId: true, slug: 'demo', origin: '/index.html' }));
  assert(pendingSave() === null, 'Boolean ID rejected.');
});

await test('Auth reload/switch intentni saqlaydi, public yoki external link cancel qiladi', () => {
  assert(!authNavigationCancelsPending('/register.html') && !authNavigationCancelsPending('/login.html?next=favorites'), 'Reload and auth switch preserve intent.');
  assert(!authNavigationCancelsPending('/register.html#main'), 'In-page keyboard skip link preserves intent.');
  assert(authNavigationCancelsPending('/index.html') && authNavigationCancelsPending('/product.html?slug=demo'), 'Leaving auth for catalog cancels intent.');
  assert(authNavigationCancelsPending('https://external.invalid/register.html') && authNavigationCancelsPending('//external.invalid/login.html'), 'External same-name route still cancels intent.');
});

await test('Guest refresh 401 beradi, CSRF header cookie flowda mavjud', async () => {
  mock((call) => csrf(call) || json({ detail: 'Unauthorized' }, 401));
  assert(await ensureAuthenticated() === false && !hasAccessToken(), 'Guest must remain unauthenticated.');
  assert(calls.length === 2 && !('refresh' in calls[1].body), 'Refresh input comes only from HttpOnly cookie.');
});

await test('Parallel sessiya tiklash bitta refresh so‘rovini yuboradi', async () => {
  mock(async (call) => {
    const token = csrf(call);
    if (token) return token;
    await new Promise((resolve) => setTimeout(resolve, 5));
    return json({ access: 'first-memory-access' });
  });
  const states = await Promise.all([ensureAuthenticated(), ensureAuthenticated(), ensureAuthenticated()]);
  assert(states.every(Boolean), 'All callers receive same authentication result.');
  assert(calls.filter((call) => call.path.endsWith('/refresh/')).length === 1, 'Single-flight refresh.');
});

await test('Access 401 faqat bir marta refresh va retry qiladi', async () => {
  let protectedCount = 0;
  mock((call) => {
    if (call.path.includes('/auth/')) return csrf(call) || json({ access: 'new-memory-access' });
    protectedCount += 1;
    if (protectedCount === 1) {
      assert(call.headers.Authorization === 'Bearer first-memory-access', 'Old access in memory.');
      return json({}, 401);
    }
    assert(call.headers.Authorization === 'Bearer new-memory-access', 'New access used on retry.');
    return json([]);
  });
  assert(Array.isArray(await authenticatedRequest('/api/v1/me/saved-products/')), 'Retried response returned.');
  assert(protectedCount === 2 && calls.filter((call) => call.path.endsWith('/refresh/')).length === 1, 'Bounded retry.');
});

await test('Ikkinchi 401 cheksiz retryga aylanmaydi', async () => {
  mock((call) => call.path.includes('/auth/') ? csrf(call) || json({ access: 'still-rejected' }) : json({}, 401));
  await rejects(() => authenticatedRequest('/api/v1/me/saved-products/'), 401);
  assert(calls.filter((call) => call.path.includes('/me/')).length === 2, 'Only one retry allowed.');
});

await test('403 authorization xatosi refresh bilan yashirilmaydi', async () => {
  mock(() => json({}, 403));
  await rejects(() => authenticatedRequest('/api/v1/me/saved-products/'), 403);
  assert(calls.length === 1, 'No refresh for forbidden response.');
});

await test('Login whitespace va passwordni xavfsiz kontraktga mos yuboradi', async () => {
  mock((call) => {
    const token = csrf(call);
    if (token) return token;
    assert(call.body.username === 'Ali', 'Username edges trimmed; case retained.');
    assert(call.body.password === ' password spaces ', 'Password whitespace retained.');
    return json({ access: 'login-memory-access' });
  });
  await login('  Ali  ', ' password spaces ');
  assert(hasAccessToken(), 'Login stores access only in module memory.');
});

await test('Registration ham accessni memoryda o‘rnatadi', async () => {
  mock((call) => csrf(call) || json({ user: { id: 1, username: 'ali' }, access: 'register-memory-access' }, 201));
  await register('ali', 'strong-password');
  assert(hasAccessToken() && calls.some((call) => call.path.endsWith('/register/')), 'Register supports pending-save authentication.');
  for (const storage of [localStorage, sessionStorage]) {
    for (let index = 0; index < storage.length; index += 1) {
      const value = storage.getItem(storage.key(index));
      assert(!value.includes('memory-access') && !value.includes('strong-password'), 'No credentials in web storage.');
    }
  }
});

await test('Logout CSRF bilan cookie flow va memory tozalashni bajaradi', async () => {
  mock((call) => csrf(call) || json(null, 204));
  await logout();
  assert(!hasAccessToken(), 'Access cleared after logout.');
  assert(calls.at(-1).path.endsWith('/logout/') && !('Authorization' in calls.at(-1).headers), 'Logout uses cookie lifecycle.');
});

await test('Refresh 403 yoki network xatosi guest deb talqin qilinmaydi', async () => {
  mock((call) => csrf(call) || json({}, 403));
  await rejects(ensureAuthenticated, 403);
  mock(() => { throw new Error('Network disconnected'); });
  await rejects(ensureAuthenticated, 0);
});

await test('Eski refresh kech tugasa yangi login tokenini almashtirmaydi', async () => {
  let finishRefresh;
  mock((call) => {
    if (call.path.endsWith('/csrf/')) return csrf(call);
    if (call.path.endsWith('/refresh/')) {
      csrf(call);
      return new Promise((resolve) => { finishRefresh = () => resolve(json({ access: 'old-refresh-access' })); });
    }
    if (call.path.endsWith('/token/')) return csrf(call) || json({ access: 'latest-login-access' });
    assert(call.headers.Authorization === 'Bearer latest-login-access', 'Latest explicit login wins.');
    return json([]);
  });
  const restoring = ensureAuthenticated();
  while (!finishRefresh) await new Promise((resolve) => setTimeout(resolve, 0));
  await login('ali', 'password');
  finishRefresh();
  assert(await restoring === true, 'Current authenticated state retained.');
  await authenticatedRequest('/api/v1/me/saved-products/');
});

await test('API client tashqi endpointga Bearer yuborishga yo‘l qo‘ymaydi', async () => {
  mock(() => { throw new Error('Must not fetch external endpoint'); });
  try {
    await request('https://external.invalid/api/v1/');
    throw new Error('Expected local path rejection.');
  } catch (error) {
    assert(error instanceof TypeError, 'Local endpoint guard.');
  }
  assert(calls.length === 0, 'No external request.');
});

await test('Logout in-flight rotation cookie javobini kutadi va yangi refreshni bloklaydi', async () => {
  mock((call) => csrf(call) || json(null, 204));
  await logout();
  let finishRefresh;
  let rotationFinished = false;
  mock((call) => {
    const token = csrf(call);
    if (token) return token;
    if (call.path.endsWith('/refresh/')) {
      return new Promise((resolve) => {
        finishRefresh = () => { rotationFinished = true; resolve(json({ access: 'rotated-access' })); };
      });
    }
    assert(call.path.endsWith('/logout/') && rotationFinished, 'Logout cookie clearing follows rotation response.');
    return json(null, 204);
  });
  const restoring = ensureAuthenticated();
  while (!finishRefresh) await new Promise((resolve) => setTimeout(resolve, 0));
  const exiting = logout();
  assert(await ensureAuthenticated() === false, 'No new authentication while logout is active.');
  assert(!calls.some((call) => call.path.endsWith('/logout/')), 'Logout waits for existing rotation.');
  finishRefresh();
  await Promise.all([restoring, exiting]);
  assert(!hasAccessToken(), 'Logout wins after cookie rotation settles.');
  assert(calls.filter((call) => call.path.endsWith('/refresh/')).length === 1, 'No extra refresh during logout.');
});

await test('Auth reset eski refresh javobini bekor qilib joriy cookie sessiyasini tiklaydi', async () => {
  let finishRefresh;
  mock((call) => {
    const token = csrf(call);
    if (token) return token;
    return new Promise((resolve) => { finishRefresh = () => resolve(json({ access: 'previous-user-access' })); });
  });
  const restoring = ensureAuthenticated();
  while (!finishRefresh) await new Promise((resolve) => setTimeout(resolve, 0));
  const resetting = resetAuthentication();
  finishRefresh();
  await Promise.all([restoring, resetting]);
  assert(!hasAccessToken(), 'A stale refresh cannot restore the previous user after reset.');
  mock((call) => {
    if (call.path.includes('/auth/')) return csrf(call) || json({ access: 'current-cookie-user-access' });
    assert(call.headers.Authorization === 'Bearer current-cookie-user-access', 'Next protected request uses current cookie user.');
    return json([]);
  });
  await authenticatedRequest('/api/v1/me/saved-products/');
});

await test('Detail va qayta ochilgan sahifa haqiqiy favorites holatini tiklaydi', async () => {
  for (let visit = 0; visit < 2; visit += 1) {
    const fixture = await appFixture('product', { saved: true });
    const button = fixture.document.querySelector('[data-save-product]');
    await waitFor(() => button && !button.disabled, 'Saved membership must settle.');
    assert(button.getAttribute('aria-pressed') === 'true' && button.textContent.trim() === 'Saqlangan', 'Saved label must follow API membership after each page load.');
    assert(button.querySelector('path').getAttribute('d') === 'M6 4h12v17l-6-4-6 4Z', 'Saved product must retain bookmark, never a check icon.');
    assert(fixture.calls.some((call) => call.path.endsWith('/token/refresh/')), 'Reload restores HttpOnly cookie session before favorites.');
  assert(fixture.calls.some((call) => call.path === '/api/v1/me/saved-products/?lang=uz' && call.method === 'GET'), 'Initial saved state comes from favorites API with selected language.');
  }
});

await test('Saqlash ↔ Saqlangan API orqali qo‘shadi va o‘chiradi', async () => {
  const fixture = await appFixture('product');
  const button = fixture.document.querySelector('[data-save-product]');
  await waitFor(() => !button.disabled, 'Initial membership must settle.');
  assert(button.getAttribute('aria-pressed') === 'false' && button.textContent.trim() === 'Saqlash', 'Unsaved state.');
  button.click();
  await waitFor(() => !button.disabled && button.getAttribute('aria-pressed') === 'true', 'POST must update saved state.');
  assert(button.textContent.trim() === 'Saqlangan' && fixture.state.saved, 'Successful POST is reflected.');
  assert(fixture.calls.some((call) => call.method === 'POST' && call.path === '/api/v1/me/saved-products/' && call.body.product_id === product.id), 'Save sends only current product ID.');
  button.click();
  await waitFor(() => !button.disabled && button.getAttribute('aria-pressed') === 'false', 'DELETE must update unsaved state.');
  assert(button.textContent.trim() === 'Saqlash' && !fixture.state.saved, 'Successful DELETE is reflected.');
  assert(fixture.calls.some((call) => call.method === 'DELETE' && call.path === `/api/v1/me/saved-products/${product.id}/`), 'Remove uses product relation endpoint.');
});

await test('Saqlash yoki o‘chirish xatosi mavjud tugma holatini saqlaydi', async () => {
  const fixture = await appFixture('product', { saveStatus: 500 });
  const button = fixture.document.querySelector('[data-save-product]');
  const notice = fixture.document.querySelector('#notice');
  await waitFor(() => !button.disabled, 'Initial membership must settle.');
  button.click();
  await waitFor(() => !button.disabled && !notice.hidden, 'Failed save must be reported.');
  assert(button.getAttribute('aria-pressed') === 'false' && button.textContent.trim() === 'Saqlash' && !fixture.state.saved, 'Failed POST cannot appear saved.');
  fixture.state.saveStatus = 201;
  button.click();
  await waitFor(() => !button.disabled && button.getAttribute('aria-pressed') === 'true', 'Save retry must recover.');
  fixture.state.deleteStatus = 500;
  button.click();
  await waitFor(() => !button.disabled && notice.classList.contains('is-error'), 'Failed delete must be reported.');
  assert(button.getAttribute('aria-pressed') === 'true' && button.textContent.trim() === 'Saqlangan' && fixture.state.saved, 'Failed DELETE cannot appear unsaved.');
});

await test('Favorites holatini olish xatosida qayta tekshirish mutatsiyadan oldin bajariladi', async () => {
  const fixture = await appFixture('product', { saved: true, listStatus: 503 });
  const button = fixture.document.querySelector('[data-save-product]');
  await waitFor(() => !button.disabled && button.textContent.includes('Qayta tekshirish'), 'Unknown membership must offer retry.');
  assert(!fixture.calls.some((call) => ['POST', 'DELETE'].includes(call.method) && call.path.includes('/me/')), 'Unknown membership never causes a blind mutation.');
  fixture.state.listStatus = 200;
  button.click();
  await waitFor(() => !button.disabled && button.textContent.trim() === 'Saqlangan', 'Membership retry must recover.');
  assert(button.getAttribute('aria-pressed') === 'true', 'Recovered state follows server.');
  assert(!fixture.calls.some((call) => ['POST', 'DELETE'].includes(call.method) && call.path.includes('/me/')), 'Retry only checks current membership.');
});

await test('Kategoriya kartasi alohida Batafsil va favorites boshqaruvini ko‘rsatadi', async () => {
  const fixture = await appFixture('category', { saved: true });
  const card = fixture.document.querySelector('.product-card');
  const button = card.querySelector('[data-save-product]');
  await waitFor(() => !button.disabled, 'Category membership must settle.');
  assert(button.getAttribute('aria-pressed') === 'true', 'Category shares true saved membership.');
  const details = Array.from(card.querySelectorAll('a')).find((link) => link.textContent.trim() === 'Batafsil');
  assert(details && details.getAttribute('href') === pageUrl('product', product.slug), 'Explicit details link must be independent of product image.');
  assert(details !== card.querySelector('.product-visual') && !details.contains(button), 'Navigation and favorite action remain independent.');
});

await test('Katalog va saqlangan kartalar bir xil vertikal responsive tuzilishda, uzun matnlar sig‘adi', async () => {
  const products = Array.from({ length: 6 }, (_, index) => ({
    ...product, id: index + 20, slug: `long-product-${index}`,
    name: index % 2 ? 'Juda uzun mahsulot nomi va do‘kon tasdiqlagan tabiiy giyohlar to‘plami' : 'Uzunmahsulotnomiorasidahechqandaybo‘shliqqoldirilmagansinov',
    image: '/tests/logo.svg', price: '9999999999.99', is_available: index % 2 === 0,
  }));
  for (const page of ['category', 'favorites']) {
    const fixture = await appFixture(page, { products, saved: true });
    const grid = fixture.document.querySelector('.product-grid');
    await waitFor(() => getComputedStyle(grid).display === 'grid', 'Product stylesheet must load.');
    const columns = innerWidth >= 1400 ? 5 : innerWidth >= 1000 ? 4 : innerWidth >= 700 ? 3 : 2;
    assert(getComputedStyle(grid).gridTemplateColumns.split(' ').length === columns, `${page} must show ${columns} columns at ${innerWidth}px.`);
    const cards = Array.from(grid.querySelectorAll('.product-card'));
    assert(cards.length === products.length, 'Every mock product must remain visible.');
    for (const card of cards) {
      const nodes = ['.product-visual', '.product-name', '.availability', '.price', '.details-button', page === 'category' ? '[data-save-product]' : '[data-remove-product]'].map((selector) => card.querySelector(selector));
      assert(nodes.every(Boolean), 'Image, name, availability, price and both actions are required.');
      assert(nodes.every((node, index) => !index || nodes[index - 1].compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING), 'Card content must follow the approved reading order.');
      const [visual, name, , , details, action] = nodes;
      assert(visual.getBoundingClientRect().bottom <= name.getBoundingClientRect().top + 1, 'Image must stay above product information.');
      assert(getComputedStyle(visual.querySelector('img')).objectFit === 'contain', 'Product images must retain the whole image.');
      assert(!card.textContent.includes(product.description) && !card.textContent.includes(product.detailed_information), 'Descriptions and instructions belong on detail pages.');
      const cardBox = card.getBoundingClientRect();
      const detailsBox = details.getBoundingClientRect();
      const actionBox = action.getBoundingClientRect();
      assert(detailsBox.bottom <= actionBox.top + 1, 'Details and favorite actions must stack vertically.');
      for (const button of [details, action]) {
        const box = button.getBoundingClientRect();
        assert(box.height >= 44 && getComputedStyle(button).borderRadius === '12px', 'Card actions need 44px touch targets and 12px corners.');
        assert(Math.abs((box.left + box.right - cardBox.left - cardBox.right) / 2) < 2, 'Card actions must be horizontally centered.');
        assert(button.scrollWidth <= button.clientWidth + 1, 'Action text and icon must fit their button.');
      }
      assert(card.scrollWidth <= card.clientWidth + 1, 'Long names and prices must fit the card.');
      if (page === 'category') {
        assert(action.textContent.trim() === 'Saqlangan' && action.getAttribute('aria-pressed') === 'true', 'Saved cards must show current API membership.');
        assert(action.querySelector('path').getAttribute('d') === 'M6 4h12v17l-6-4-6 4Z' && getComputedStyle(action.querySelector('svg')).fill !== 'none', 'Saved state must use a filled bookmark.');
      } else {
        assert(action.textContent.trim() === 'O‘chirish' && !card.querySelector('[data-save-product]'), 'Favorites use a separate remove action.');
        assert(card.querySelector('.saved-date')?.textContent.trim() === 'Saqlangan: 14.10.2026', 'Every saved card includes its date.');
      }
    }
    assert(fixture.document.documentElement.scrollWidth <= innerWidth, 'Product grids must not create horizontal page overflow.');
  }
});

await test('Chiqish oynasida Bekor va native cancel sessiyani saqlab, fokusni qaytaradi', async () => {
  const fixture = await appFixture('product', { saved: true });
  const trigger = fixture.document.querySelector('#logout-button');
  const dialog = fixture.document.querySelector('#logout-confirmation');
  const cancel = fixture.document.querySelector('#logout-cancel');
  assert(dialog instanceof HTMLDialogElement && !dialog.open, 'Logout confirmation must start closed.');
  const logoutCalls = () => fixture.calls.filter((call) => call.path.endsWith('/logout/'));
  rememberSave(product);
  trigger.focus();
  trigger.click();
  assert(dialog.open && dialog.matches(':modal') && fixture.document.activeElement === cancel, 'Logout opens a native modal with safe initial focus.');
  assert(fixture.document.getElementById(dialog.getAttribute('aria-labelledby'))?.textContent.trim() === 'Hisobdan chiqish', 'Dialog must have an accessible title.');
  assert(fixture.document.getElementById(dialog.getAttribute('aria-describedby'))?.textContent.trim() === 'Hisobingizdan haqiqatan ham chiqmoqchimisiz?', 'Dialog must explain confirmation.');
  assert(logoutCalls().length === 0 && hasAccessToken(), 'Opening confirmation must not log out.');
  cancel.click();
  await waitFor(() => !dialog.open && fixture.document.activeElement === trigger, 'Cancel must close dialog and return focus.');
  assert(logoutCalls().length === 0 && hasAccessToken() && pendingSave()?.productId === product.id, 'Cancel preserves session and pending intent.');
  trigger.click();
  if (typeof dialog.requestClose === 'function') dialog.requestClose();
  else if (dialog.dispatchEvent(new Event('cancel', { cancelable: true }))) dialog.close();
  await waitFor(() => !dialog.open && fixture.document.activeElement === trigger, 'Native cancel/Escape lifecycle must close dialog and return focus.');
  assert(logoutCalls().length === 0 && hasAccessToken(), 'Native cancel must not log out.');
  clearPendingSave();
});

await test('Ha, chiqish mavjud CSRF logoutni bir marta bajaradi, xatoda sessiya saqlanadi', async () => {
  const fixture = await appFixture('product', { saved: true, logoutStatus: 503 });
  const trigger = fixture.document.querySelector('#logout-button');
  const dialog = fixture.document.querySelector('#logout-confirmation');
  const cancel = fixture.document.querySelector('#logout-cancel');
  const confirm = fixture.document.querySelector('#logout-confirm');
  trigger.click();
  assert(confirm.textContent.trim() === 'Ha, chiqish', 'Confirm action must clearly name logout.');
  confirm.click();
  confirm.click();
  assert(confirm.disabled && cancel.disabled && trigger.disabled, 'Pending logout prevents duplicate submission.');
  const cancelling = new Event('cancel', { cancelable: true });
  dialog.dispatchEvent(cancelling);
  assert(cancelling.defaultPrevented && dialog.open, 'An in-flight logout must finish before the modal can close.');
  await waitFor(() => !confirm.disabled && !cancel.disabled && dialog.querySelector('.dialog-error')?.textContent, 'Failed logout must show a recoverable error.');
  const submitted = fixture.calls.filter((call) => call.path.endsWith('/logout/'));
  assert(submitted.length === 1 && submitted[0].method === 'POST' && submitted[0].headers['X-CSRFToken'] === 'fixture-csrf', 'Confirmation must use the existing CSRF protected cookie logout once.');
  assert(dialog.open && hasAccessToken() && !trigger.disabled, 'Failed logout keeps current session available.');
  assert(dialog.querySelector('.dialog-error').getAttribute('role') === 'alert', 'Logout errors must be announced.');
  cancel.click();
  await waitFor(() => !dialog.open && fixture.document.activeElement === trigger, 'User can cancel after a failed logout.');
});

await test('Saqlanganlar sanasi aniq formatda, remove xatosi kartani saqlaydi', async () => {
  const fixture = await appFixture('favorites', { saved: true, deleteStatus: 500 });
  const button = fixture.document.querySelector('[data-remove-product]');
  assert(fixture.document.querySelector('.saved-date').textContent.trim() === 'Saqlangan: 14.10.2026', 'Saved date uses dd.mm.yyyy format.');
  assert(Array.from(fixture.document.querySelectorAll('.product-card a')).some((link) => link.textContent.trim() === 'Batafsil'), 'Favorites cards have a details button too.');
  button.click();
  await waitFor(() => !button.disabled && !fixture.document.querySelector('#notice').hidden, 'Failed remove must settle.');
  assert(fixture.document.querySelector('.product-card') && fixture.state.saved, 'Failed remove preserves relation and card.');
  fixture.state.deleteStatus = 204;
  button.click();
  await waitFor(() => !fixture.document.querySelector('.product-card'), 'Successful remove must remove card.');
  assert(fixture.document.querySelector('#result-count').textContent.startsWith('0'), 'Empty state count stays accurate.');
});

await test('Login va registration parol ko‘zchasi qiymatni va submitni o‘zgartirmaydi', async () => {
  for (const page of ['login', 'register']) {
    const fixture = await appFixture(page);
    const input = fixture.document.querySelector('#password');
    const toggle = fixture.document.querySelector('#password-toggle');
    input.value = ' Private password 12! ';
    assert(toggle.type === 'button' && input.type === 'password', 'Password is initially hidden and eye is not submit.');
    toggle.click();
    assert(input.type === 'text' && toggle.getAttribute('aria-pressed') === 'true', 'Eye shows password with accessible state.');
    toggle.click();
    assert(input.type === 'password' && toggle.getAttribute('aria-pressed') === 'false', 'Eye hides password again.');
    assert(input.value === ' Private password 12! ' && fixture.calls.length === 0, 'Visibility does not change password or send auth request.');
  }
});

await test('Markaziy brend sozlamasi va mavjud SVG logo fallback ishlaydi', async () => {
  const fixture = await appFixture('product', { brandName: 'Sinov do‘koni', logoUrl: 'https://external.invalid/logo.svg' });
  const names = Array.from(fixture.document.querySelectorAll('[data-brand-name]'));
  assert(names.length >= 2 && names.every((node) => node.textContent.trim() === 'Sinov do‘koni'), 'Header and footer use central configured name.');
  assert(fixture.document.title.endsWith(' — Sinov do‘koni'), 'Dynamic product title uses central name.');
  assert(fixture.document.querySelector('[data-brand-logo] svg'), 'Unusable logo keeps existing SVG fallback.');
  assert(!fixture.document.querySelector('[data-brand-logo] img'), 'External logo cannot bypass same-origin image policy.');
  assert(!fixture.document.querySelector('.site-footer').textContent.includes('Tabiiy mahsulotlar katalogi va saqlangan tanlovlar'), 'Duplicate footer text is removed.');
});

await test('Lokal logo yuklanadi, mavjud bo‘lmagan logo esa SVG fallbackni saqlaydi', async () => {
  const loaded = await appFixture('product', { brandName: 'Sinov do‘koni', logoUrl: '/tests/logo.svg' });
  const mark = loaded.document.querySelector('[data-brand-logo]');
  await waitFor(() => mark.querySelector('img')?.complete && !mark.querySelector('img').hidden, 'Local logo must become visible.');
  assert(mark.querySelector('img').naturalWidth > 0 && mark.querySelector('svg').hasAttribute('hidden'), 'Loaded logo hides SVG fallback.');
  const missing = await appFixture('product', { brandName: 'Sinov do‘koni', logoUrl: '/tests/missing-logo.png' });
  const fallback = missing.document.querySelector('[data-brand-logo]');
  await waitFor(() => !fallback.querySelector('img'), 'Broken logo must be removed.');
  assert(fallback.querySelector('svg') && !fallback.querySelector('svg').hasAttribute('hidden'), 'Broken image restores visible original SVG.');
});

await test('Yangilangan mahsulotning narxi, tavsifi va qo‘llanmasi keyingi yuklashda ko‘rinadi', async () => {
  const updated = {
    ...product, name: 'Yangilangan giyoh', price: '42000.50',
    description: 'Yangilangan qisqa tavsif.',
    detailed_information: 'Qadoqdagi tasdiqlangan yangi qo‘llanma.',
  };
  const fixture = await appFixture('product', { product: updated });
  assert(fixture.document.querySelector('#page-title').textContent === updated.name, 'Updated product name.');
  assert(fixture.document.querySelector('.price').textContent === '42\u00a0000,50 so‘m', 'Updated decimal price.');
  assert(fixture.document.querySelector('.product-description').textContent === updated.description, 'Short description stays separate.');
  assert(fixture.document.querySelector('.instruction-text').textContent === updated.detailed_information, 'Approved package instructions remain supported.');
  assert(fixture.document.querySelector('#product-back').getAttribute('href') === pageUrl('category', category.slug), 'Updated product keeps correct category return.');
});

await test('O‘chirilgan mahsulot detaili xavfsiz error va qayta urinishni ko‘rsatadi', async () => {
  const fixture = await appFixture('product', { productStatus: 404 });
  const state = fixture.document.querySelector('#page-content .state.error');
  assert(state && state.textContent.includes('topilmadi'), 'Missing product displays safe API error.');
  assert(state.querySelector('button') && !fixture.document.querySelector('[data-save-product]'), 'Missing product cannot be saved.');
});

await test('Oldin o‘chirilgan favorite relation 404 holatida Saqlashga qaytadi', async () => {
  const fixture = await appFixture('product', { saved: true, deleteStatus: 404 });
  const button = fixture.document.querySelector('[data-save-product]');
  await waitFor(() => !button.disabled, 'Initial membership must settle.');
  button.click();
  await waitFor(() => !button.disabled && button.getAttribute('aria-pressed') === 'false', 'Already removed relation must reconcile.');
  assert(button.textContent.trim() === 'Saqlash', '404 relation uses unsaved label.');
});

await test('Browser Back persisted sahifa boshqa hisobning haqiqiy favorites holatini tiklaydi', async () => {
  const fixture = await appFixture('product', { saved: true });
  await waitFor(() => !document.querySelector('[data-save-product]').disabled, 'Initial membership must settle.');
  fixture.state.saved = false;
  fixture.state.access = 'next-cookie-user-access';
  const previousRequests = fixture.calls.length;
  window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }));
  await waitFor(() => {
    const button = document.querySelector('[data-save-product]');
    return button && !button.disabled && button.getAttribute('aria-pressed') === 'false';
  }, 'Persisted page must restore current cookie session.');
  const renewed = fixture.calls.slice(previousRequests);
  assert(renewed.some((call) => call.path.endsWith('/token/refresh/')), 'Back invalidates memory token and silently refreshes.');
  assert(renewed.some((call) => call.path.includes('/me/') && call.headers.Authorization === 'Bearer next-cookie-user-access'), 'Favorites belong to the current cookie user.');
});

await test('Browser Back persisted sahifa logout qilingan foydalanuvchini guest ko‘rsatadi', async () => {
  const fixture = await appFixture('product', { saved: true });
  await waitFor(() => !document.querySelector('[data-save-product]').disabled, 'Initial membership must settle.');
  fixture.state.refreshStatus = 401;
  window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }));
  await waitFor(() => {
    const button = document.querySelector('[data-save-product]');
    return button && !button.disabled && button.getAttribute('aria-pressed') === 'false';
  }, 'Logged-out persisted page must return to guest state.');
  assert(!hasAccessToken() && document.querySelector('#logout-button').hidden, 'Old access and logout action are cleared.');
});

await test('Til faqat UZ/RU va alohida localStorage kalitida saqlanadi', () => {
  localStorage.removeItem(LANGUAGE_KEY);
  assert(getLanguage() === 'uz', 'Uzbek is the default language.');
  localStorage.setItem(LANGUAGE_KEY, 'en');
  assert(getLanguage() === 'uz', 'Unknown stored languages safely default to Uzbek.');
  setLanguage('ru');
  assert(getLanguage() === 'ru' && localStorage.getItem(LANGUAGE_KEY) === 'ru', 'Russian choice persists.');
  let rejected = false;
  try { setLanguage('en'); } catch { rejected = true; }
  assert(rejected && getLanguage() === 'ru', 'Unsupported language cannot replace selection.');
  assert(t('Saqlash') === 'Сохранить' && formatPrice('35000.50') === '35\u00a0000,50 сум', 'Interface and currency use the selected language.');
  assert(resultCount(1) === '1 товар' && resultCount(2) === '2 товара' && resultCount(11) === '11 товаров' && resultCount(21, true) === '21 категория', 'Russian counts use correct forms.');
});

await test('Katalog va Favorites GET tilni oladi, auth/mutation kontrakti saqlanadi', async () => {
  setLanguage('ru');
  mock((call) => json([]));
  for (const path of ['/api/v1/categories/', '/api/v1/categories/demo/products/', '/api/v1/products/demo/', '/api/v1/me/saved-products/']) {
    await request(path);
    assert(new URL(calls.at(-1).path, location.origin).searchParams.get('lang') === 'ru', 'Every catalog read must carry language.');
  }
  await request('/api/v1/me/saved-products/', { method: 'POST', body: { product_id: product.id } });
  assert(calls.at(-1).path === '/api/v1/me/saved-products/' && calls.at(-1).body.product_id === product.id, 'Save still sends the same shared product ID.');
  await request('/api/v1/auth/csrf/');
  assert(calls.at(-1).path === '/api/v1/auth/csrf/', 'Cookie authentication endpoints stay unchanged.');
});

await test('Barcha ommaviy sahifalarda RU interfeys, header va footer ishlaydi', async () => {
  setLanguage('ru');
  for (const page of ['home', 'category', 'product', 'favorites', 'login', 'register']) {
    const fixture = await appFixture(page, { saved: true });
    assert(document.documentElement.lang === 'ru', 'Document declares Russian.');
    assert(fixture.document.querySelector('[data-nav="catalog"]').textContent.trim() === 'Каталог', 'Catalog navigation translated.');
    assert(fixture.document.querySelector('[data-nav="favorites"]').textContent.trim() === 'Сохранённое', 'Favorites navigation translated.');
    assert(fixture.document.querySelector('.site-footer').textContent.includes('Ташкент'), 'Footer translated.');
    assert(fixture.document.querySelector('[data-language="ru"]').getAttribute('aria-pressed') === 'true', 'Selected language is accessible.');
    assert(fixture.document.querySelectorAll('.language-switch').length === 1, 'Auth updates never duplicate language controls.');
    assert(!fixture.document.querySelector('#page-content .state.error'), 'Page initializes in Russian.');
  }
});

await test('DB matni interfeys lug‘ati orqali tarjima qilinmaydi', async () => {
  setLanguage('ru');
  const exact = { ...product, name: 'Saqlash', description: 'Katalog', detailed_information: 'Batafsil', language: 'ru', translation_available: true };
  const fixture = await appFixture('product', { product: exact, saved: true });
  assert(fixture.document.querySelector('#page-title').textContent === 'Saqlash', 'Catalog name remains exactly the API value even if it matches an interface key.');
  assert(fixture.document.querySelector('.product-description').textContent === 'Katalog' && fixture.document.querySelector('.instruction-text').textContent === 'Batafsil', 'Catalog descriptions and instructions never use the interface dictionary.');
  assert(fixture.document.querySelector('[data-save-product]').textContent.trim() === 'Сохранено', 'Only interface action is translated.');
});

await test('Yetishmayotgan RU tarjima ID, slug, narx va bookmarkni yashirmaydi', async () => {
  setLanguage('ru');
  const missingCategory = { ...category, name: null, language: 'ru', translation_available: false };
  const missing = { ...product, name: null, description: null, detailed_information: null, category: missingCategory, language: 'ru', translation_available: false };
  for (const page of ['home', 'category', 'product', 'favorites']) {
    const fixture = await appFixture(page, { product: missing, category: missingCategory, saved: true });
    assert(!fixture.document.querySelector('#page-content .state.error'), 'Missing translation is not a broken API response.');
    assert(fixture.document.querySelector('#page-content').textContent.includes('Перевод ещё не добавлен') || fixture.document.querySelector('#page-title')?.textContent.includes('Перевод ещё не добавлен'), 'Missing translation is explicit.');
    assert(!fixture.document.querySelector('#page-content').textContent.includes(product.detailed_information), 'Uzbek instructions never masquerade as Russian.');
    if (page === 'product') {
      assert(fixture.document.querySelector('.translation-notice')?.textContent.includes('ответственными сотрудниками'), 'Instructions explain pending shop review.');
      assert(fixture.document.querySelector('[data-save-product]').dataset.saveProduct === String(product.id), 'Bookmark uses the original identity.');
      assert(fixture.document.querySelector('#product-back').getAttribute('href') === pageUrl('category', category.slug), 'Original category slug remains navigable.');
      assert(fixture.document.querySelector('.price').textContent === '35\u00a0000 сум', 'Shared decimal price remains visible.');
    }
  }
});

await test('RU auth validatsiya, pending Save va parol accessibility matnlari ishlaydi', async () => {
  setLanguage('ru');
  for (const page of ['login', 'register']) {
    rememberSave(product);
    const fixture = await appFixture(page);
    const form = fixture.document.querySelector('#auth-form');
    assert(pendingSave()?.productId === product.id && fixture.document.querySelector('#auth-context').textContent.includes('сохранится автоматически'), 'Language choice and auth page preserve pending Save.');
    form.requestSubmit();
    assert(fixture.document.querySelector('#username-error').textContent === 'Введите имя пользователя.' && fixture.document.querySelector('#password-error').textContent === 'Введите пароль.', 'Required fields use Russian validation.');
    fixture.document.querySelector('#password-toggle').click();
    assert(fixture.document.querySelector('#password-toggle').getAttribute('aria-label') === 'Скрыть пароль', 'Password visibility label translated.');
    fixture.document.querySelector('#username').value = 'demo';
    fixture.document.querySelector('#password').value = 'weak';
    form.requestSubmit();
    await waitFor(() => !fixture.document.querySelector('#form-message').hidden, 'Server validation must settle.');
    assert(fixture.document.querySelector('#form-message').textContent === 'Проверьте введённые данные.', 'Server validation is safely localized by status/field.');
    assert(pendingSave()?.productId === product.id, 'Validation never loses the pending product.');
  }
  clearPendingSave();
});

await test('RU bookmark, logout tasdiqlash va API xatosi tarjima qilingan', async () => {
  setLanguage('ru');
  const fixture = await appFixture('product', { saved: true, logoutStatus: 503 });
  assert(fixture.document.querySelector('[data-save-product]').textContent.trim() === 'Сохранено', 'Russian bookmark initially saved.');
  fixture.document.querySelector('[data-save-product]').click();
  await waitFor(() => fixture.document.querySelector('[data-save-product]').textContent.trim() === 'Сохранить', 'Russian remove must update bookmark.');
  assert(fixture.document.querySelector('#notice').textContent === 'Товар удалён из сохранённого.', 'Notification translated.');
  fixture.document.querySelector('#logout-button').click();
  assert(fixture.document.querySelector('#logout-dialog-title').textContent === 'Выход из аккаунта' && fixture.document.querySelector('#logout-cancel').textContent === 'Отмена', 'Logout dialog translated.');
  fixture.document.querySelector('#logout-confirm').click();
  await waitFor(() => !fixture.document.querySelector('.dialog-error').hidden, 'Russian logout error must settle.');
  assert(fixture.document.querySelector('.dialog-error').textContent.startsWith('Сервер не смог'), 'Safe status errors translated.');
});

window.fetch = originalFetch;
history.replaceState(null, '', originalUrl);
clearPendingSave();
if (originalPending !== null) sessionStorage.setItem('herbalStore.pendingSave', originalPending);
if (originalLanguage === null) localStorage.removeItem(LANGUAGE_KEY);
else localStorage.setItem(LANGUAGE_KEY, originalLanguage);
output.dataset.status = failed ? 'failed' : 'passed';
output.dataset.passed = String(passed);
output.dataset.failed = String(failed);
output.textContent = `${passed} PASS, ${failed} FAIL\n\n${results.join('\n')}`;
