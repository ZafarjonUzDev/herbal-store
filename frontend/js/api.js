import { getLanguage, t } from './i18n.js';
export class ApiError extends Error {
  constructor(status, data = null) {
    super(`API request failed (${status})`);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export async function request(path, { method = 'GET', body, headers = {} } = {}) {
  if (typeof path !== 'string' || !path.startsWith('/api/v1/')) {
    throw new TypeError('Only local API paths are allowed.');
  }
  if (method === 'GET' && /^\/api\/v1\/(categories\/|products\/|me\/saved-products\/)/.test(path)) {
    const url = new URL(path, window.location.origin);
    url.searchParams.set('lang', getLanguage());
    path = `${url.pathname}${url.search}`;
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch(path, {
      method,
      credentials: 'same-origin',
      cache: 'no-store',
      redirect: 'error',
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...headers,
      },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    const text = response.status === 204 ? '' : await response.text();
    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        throw new ApiError(response.ok ? 502 : response.status);
      }
    }
    if (!response.ok) throw new ApiError(response.status, data);
    return data;
  } catch (error) {
    if (error instanceof ApiError || error instanceof TypeError && error.message.startsWith('Only local')) {
      throw error;
    }
    throw new ApiError(0);
  } finally {
    clearTimeout(timeout);
  }
}

export function errorMessage(error) {
  if (!(error instanceof ApiError)) return t('Kutilmagan xato yuz berdi. Qayta urinib ko‘ring.');
  if (error.status === 0) return t('Server bilan bog‘lanib bo‘lmadi. Internet aloqangizni tekshirib, qayta urinib ko‘ring.');
  if (error.status === 401) return t('Sessiya mavjud emas yoki muddati tugagan. Hisobingizga qayta kiring.');
  if (error.status === 403) return t('Xavfsizlik tekshiruvi so‘rovni rad etdi. Sahifani yangilab, qayta urinib ko‘ring.');
  if (error.status === 404) return t('So‘ralgan ma’lumot topilmadi. U katalogdan olib tashlangan bo‘lishi mumkin.');
  if (error.status === 429) return t('Qisqa vaqtda juda ko‘p so‘rov yuborildi. Biroz kutib, qayta urinib ko‘ring.');
  if (error.status === 400) return t('Kiritilgan ma’lumotni tekshiring va qayta urinib ko‘ring.');
  return t('Server so‘rovni bajara olmadi. Birozdan so‘ng qayta urinib ko‘ring.');
}
