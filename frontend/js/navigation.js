import { t } from './i18n.js';
const PENDING_KEY = 'herbalStore.pendingSave';

export function validSlug(value) {
  return typeof value === 'string' && value.length > 0 && value.length <= 230 && /^[A-Za-z0-9_-]+$/.test(value);
}

export function pageUrl(page, slug) {
  if (!['category', 'product'].includes(page) || !validSlug(slug)) throw new TypeError('Invalid page route.');
  return `/${page}.html?slug=${encodeURIComponent(slug)}`;
}

export function pageSlug() {
  const slug = new URLSearchParams(window.location.search).get('slug');
  return validSlug(slug) ? slug : null;
}

function safeOrigin(value) {
  if (typeof value !== 'string' || !value.startsWith('/')) return null;
  try {
    const url = new URL(value, window.location.origin);
    if (url.origin !== window.location.origin || url.username || url.password) return null;
    if (url.pathname === '/' || url.pathname === '/index.html') return '/index.html';
    if (['/category.html', '/product.html'].includes(url.pathname)) {
      const slug = url.searchParams.get('slug');
      return validSlug(slug) ? pageUrl(url.pathname.slice(1, -5), slug) : null;
    }
  } catch {
    return null;
  }
  return null;
}

export function clearPendingSave() {
  try { sessionStorage.removeItem(PENDING_KEY); } catch { /* Storage may be disabled. */ }
}

export function pendingSave() {
  try {
    const raw = sessionStorage.getItem(PENDING_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw);
    const origin = safeOrigin(data?.origin);
    if (!Number.isSafeInteger(data?.productId) || data.productId <= 0 || !validSlug(data.slug) || !origin) {
      clearPendingSave();
      return null;
    }
    return { productId: data.productId, slug: data.slug, origin };
  } catch {
    clearPendingSave();
    return null;
  }
}

export function rememberSave(product) {
  if (!Number.isSafeInteger(product?.id) || product.id <= 0 || !validSlug(product.slug)) {
    throw new TypeError('Invalid product.');
  }
  const origin = safeOrigin(`${window.location.pathname}${window.location.search}`) || pageUrl('product', product.slug);
  try {
    sessionStorage.setItem(PENDING_KEY, JSON.stringify({ productId: product.id, slug: product.slug, origin }));
  } catch {
    throw new Error(t('Brauzer vaqtinchalik saqlashga ruxsat bermadi. Brauzer sozlamalarini tekshiring.'));
  }
}

export function authUrl(page = 'login') {
  const target = page === 'register' ? 'register' : 'login';
  const next = new URLSearchParams(window.location.search).get('next');
  return `/${target}.html${next === 'favorites' ? '?next=favorites' : ''}`;
}

export function authDestination() {
  return '/favorites.html';
}

export function authNavigationCancelsPending(href) {
  try {
    const destination = new URL(href, window.location.href);
    return destination.origin !== window.location.origin || !['/login.html', '/register.html'].includes(destination.pathname);
  } catch {
    return true;
  }
}

export function formatPrice(value) {
  const match = /^(\d{1,10})(?:\.(\d{1,2}))?$/.exec(String(value));
  if (!match) return t('Narx ko‘rsatilmagan');
  const whole = match[1].replace(/\B(?=(\d{3})+(?!\d))/g, '\u00a0');
  const fraction = (match[2] || '').padEnd(2, '0');
  return `${whole}${fraction === '00' ? '' : `,${fraction}`} ${t('so‘m')}`;
}

export function imageUrl(value) {
  if (typeof value !== 'string' || !value) return null;
  try {
    const url = new URL(value, window.location.origin);
    return ['http:', 'https:'].includes(url.protocol) && url.origin === window.location.origin && !url.username && !url.password ? url.href : null;
  } catch {
    return null;
  }
}
