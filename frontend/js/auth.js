import { ApiError, request } from './api.js';

let accessToken = null;
let refreshPromise = null;
let csrfPromise = null;
let logoutPromise = null;
let authVersion = 0;

async function csrfToken() {
  if (!csrfPromise) {
    csrfPromise = request('/api/v1/auth/csrf/')
      .then((data) => {
        if (typeof data?.csrfToken !== 'string' || !data.csrfToken) throw new ApiError(502);
        return data.csrfToken;
      })
      .finally(() => { csrfPromise = null; });
  }
  return csrfPromise;
}

async function authPost(path, body = {}) {
  const csrf = await csrfToken();
  return request(path, { method: 'POST', body, headers: { 'X-CSRFToken': csrf } });
}

function acceptAccess(data) {
  if (typeof data?.access !== 'string' || !data.access) throw new ApiError(502);
  accessToken = data.access;
}

export async function resetAuthentication() {
  // Browser Back boshqa sahifada almashtirilgan hisobning eski accessini ishlatmasin.
  authVersion += 1;
  accessToken = null;
  if (refreshPromise) await refreshPromise.catch(() => {});
}

export function hasAccessToken() {
  return Boolean(accessToken);
}

export async function ensureAuthenticated() {
  if (logoutPromise) return false;
  if (accessToken) return true;
  return refreshAuthentication();
}

export async function refreshAuthentication() {
  if (logoutPromise) return false;
  if (!refreshPromise) {
    const version = authVersion;
    refreshPromise = (async () => {
      try {
        const data = await authPost('/api/v1/auth/token/refresh/');
        if (version === authVersion) acceptAccess(data);
        return Boolean(accessToken);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          if (version === authVersion) accessToken = null;
          return Boolean(accessToken);
        }
        throw error;
      }
    })().finally(() => { refreshPromise = null; });
  }
  return refreshPromise;
}

export async function authenticatedRequest(path, options = {}) {
  if (!await ensureAuthenticated()) throw new ApiError(401);
  const send = () => request(path, {
    ...options,
    headers: { ...options.headers, Authorization: `Bearer ${accessToken}` },
  });
  try {
    return await send();
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
    accessToken = null;
    if (!await refreshAuthentication()) throw new ApiError(401);
    return send();
  }
}

export async function login(username, password) {
  const data = await authPost('/api/v1/auth/token/', { username: username.trim(), password });
  authVersion += 1;
  acceptAccess(data);
  return data;
}

export async function register(username, password) {
  const data = await authPost('/api/v1/auth/register/', { username: username.trim(), password });
  authVersion += 1;
  acceptAccess(data);
  return data;
}

export async function logout() {
  if (!logoutPromise) {
    logoutPromise = (async () => {
      // Rotation javobi cookie'ni o‘rnatib bo‘lgachgina logout uni tozalaydi.
      if (refreshPromise) await refreshPromise.catch(() => {});
      await authPost('/api/v1/auth/logout/');
      authVersion += 1;
      accessToken = null;
    })().finally(() => { logoutPromise = null; });
  }
  return logoutPromise;
}
