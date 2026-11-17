import { siteConfig } from '../js/config.js';

const originalBody = document.body;
const originalHead = Array.from(document.head.childNodes);
const originalUrl = window.location.href;
const originalDocumentLanguage = document.documentElement.lang;
const originalConfig = { ...siteConfig };
const originalWindowAdd = window.addEventListener;
const originalDocumentAdd = document.addEventListener;
const originalTimeout = window.setTimeout;
const originalClearTimeout = window.clearTimeout;
const listeners = [];
const timers = new Set();
let mounted = false;
let sequence = 0;

export function restoreFixture() {
  if (!mounted) return;
  for (const [target, type, listener, options] of listeners) target.removeEventListener(type, listener, options);
  listeners.length = 0;
  for (const timer of timers) originalClearTimeout(timer);
  timers.clear();
  window.addEventListener = originalWindowAdd;
  document.addEventListener = originalDocumentAdd;
  window.setTimeout = originalTimeout;
  document.body.replaceWith(originalBody);
  document.head.replaceChildren(...originalHead);
  document.documentElement.lang = originalDocumentLanguage;
  history.replaceState(null, '', originalUrl);
  Object.assign(siteConfig, originalConfig);
  mounted = false;
}

export async function mountFixture(page, state, originalFetch) {
  restoreFixture();
  const response = await originalFetch(`/${page === 'home' ? 'index' : page}.html`);
  if (!response.ok) throw new Error('Actual frontend HTML must be available.');
  const source = new DOMParser().parseFromString(await response.text(), 'text/html');
  source.querySelectorAll('script').forEach((node) => node.remove());
  document.head.replaceChildren(...source.head.childNodes);
  document.body.replaceWith(source.body);
  history.replaceState(null, '', `/${page}.html?slug=demo-product`);
  mounted = true;
  window.addEventListener = function (type, listener, options) {
    listeners.push([window, type, listener, options]);
    return originalWindowAdd.call(window, type, listener, options);
  };
  document.addEventListener = function (type, listener, options) {
    listeners.push([document, type, listener, options]);
    return originalDocumentAdd.call(document, type, listener, options);
  };
  window.setTimeout = function (handler, delay, ...args) {
    const timer = originalTimeout(handler, delay, ...args);
    timers.add(timer);
    return timer;
  };
  const calls = [];
  window.fetch = async (path, options = {}) => {
    const method = options.method || 'GET';
    const body = options.body ? JSON.parse(options.body) : null;
    calls.push({ path, method, body, headers: options.headers });
    let status = 200;
    let data;
    if (path.endsWith('/csrf/')) data = { csrfToken: 'fixture-csrf' };
    else if (path.endsWith('/token/refresh/')) {
      status = state.refreshStatus || 200;
      data = { access: state.access || 'fixture-memory-access' };
    }
    else if (path.endsWith('/logout/')) {
      status = state.logoutStatus || 204;
      if (status < 400) state.refreshStatus = 401;
      data = {};
    }
    else if (path.endsWith('/token/') || path.endsWith('/register/')) {
      status = state.authStatus || 400;
      data = state.authErrors || { username: ['invalid'], password: ['invalid'] };
    }
    else if (path.includes('/categories/')) data = new URL(path, location.origin).pathname === '/api/v1/categories/'
      ? state.categories || [state.category]
      : { category: state.category, products: state.products || [state.product] };
    else if (path.includes('/products/')) {
      status = state.productStatus || 200;
      data = state.product;
    } else if (path.includes('/me/saved-products/')) {
      if (method === 'GET') {
        status = state.listStatus || 200;
        data = state.saved ? state.products || [state.product] : [];
      } else if (method === 'POST') {
        status = state.saveStatus || (state.saved ? 200 : 201);
        if (status < 400) state.saved = true;
        data = { message: status === 200 ? 'Mahsulot avval saqlangan.' : 'Mahsulot saqlandi.' };
      } else if (method === 'DELETE') {
        status = state.deleteStatus || 204;
        if (status < 400) state.saved = false;
        data = {};
      }
    } else throw new Error(`Unexpected fixture request: ${path}`);
    return new Response(status === 204 ? null : JSON.stringify(data), {
      status, headers: { 'Content-Type': 'application/json' },
    });
  };
  if (state.brandName !== undefined) {
    siteConfig.name = state.brandName;
    siteConfig.logoUrl = state.logoUrl || '';
  }
  // Fresh page code; auth.js memory is cleared through logout before each fixture.
  await import(`/js/app.js?fixture=${sequence += 1}`);
  return { document, state, calls };
}
