/** CloudDS API contract v1: cookies HttpOnly + CSRF; no mock accounts or fake files. */
(() => {
  'use strict';
  const BASE = '/api/v1';
  let csrfToken = null;
  class ApiError extends Error {
    constructor(message, status = 0, code = 'NETWORK_ERROR', details = null) {
      super(message); this.name = 'ApiError'; this.status = status; this.code = code; this.details = details;
    }
  }
  const qs = values => {
    const query = new URLSearchParams();
    Object.entries(values || {}).forEach(([key, value]) => { if (value !== undefined && value !== null && value !== '') query.set(key, String(value)); });
    return query.toString();
  };
  function safePath(path) {
    if (!path.startsWith('/') || path.startsWith('//') || /^\/https?:/i.test(path)) throw new ApiError('Đường dẫn API không hợp lệ.');
    return BASE + path;
  }
  async function parseFailure(response) {
    const type = response.headers.get('content-type') || '';
    let payload = null;
    if (type.includes('json')) { try { payload = await response.json(); } catch {} }
    const error = payload?.error || {};
    const defaults = {
      400: 'Dữ liệu yêu cầu chưa hợp lệ.', 401: 'Phiên đăng nhập hết hạn hoặc chưa đăng nhập.',
      403: 'Bạn không có quyền thực hiện thao tác này.', 404: 'Không tìm thấy dữ liệu.',
      409: 'Không thể hoàn tất thao tác. Kiểm tra giới hạn hoặc trùng tên.',
      413: 'Tệp vượt quá kích thước cho phép.', 422: 'Dữ liệu nhập chưa hợp lệ.',
      429: 'Bạn thao tác quá nhanh. Vui lòng thử lại sau.', 500: 'Máy chủ gặp lỗi.',
      503: 'Dịch vụ hiện không sẵn sàng.'
    };
    return new ApiError(error.message || defaults[response.status] || `Lỗi máy chủ (HTTP ${response.status}).`, response.status, error.code || 'HTTP_ERROR', error.details);
  }
  async function csrf(force = false) {
    if (csrfToken && !force) return csrfToken;
    const response = await raw('/auth/csrf', { method: 'GET', skipCsrf: true });
    const token = response?.csrf_token || response?.token;
    if (!token) throw new ApiError('Máy chủ chưa cung cấp CSRF token.', 0, 'CSRF_UNAVAILABLE');
    csrfToken = token;
    return token;
  }
  async function raw(path, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const headers = new Headers(options.headers || {});
    const modifying = !['GET', 'HEAD', 'OPTIONS'].includes(method);
    if (modifying && !options.skipCsrf) headers.set('X-CSRF-Token', await csrf());
    const body = options.body;
    if (body !== undefined && body !== null && !(body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json; charset=utf-8');
    }
    let response;
    try {
      response = await fetch(safePath(path), {
        method, headers, credentials: 'same-origin',
        body: body instanceof FormData || typeof body === 'string' ? body : body === undefined || body === null ? undefined : JSON.stringify(body),
        signal: options.signal,
      });
    } catch {
      throw new ApiError('Không thể kết nối Flask API. Kiểm tra backend và cấu hình Apache.', 0, 'NETWORK_ERROR');
    }
    if (!response.ok) {
      if (response.status === 403 && modifying) csrfToken = null;
      throw await parseFailure(response);
    }
    if (options.binary) return response;
    if (response.status === 204) return null;
    const type = response.headers.get('content-type') || '';
    if (!type.includes('json')) throw new ApiError('API không trả về JSON như hợp đồng đã thống nhất.', response.status, 'INVALID_RESPONSE');
    let value;
    try { value = await response.json(); } catch { throw new ApiError('Dữ liệu phản hồi của API không hợp lệ.', response.status, 'INVALID_RESPONSE'); }
    if (value?.success !== true) throw new ApiError(value?.error?.message || 'Phản hồi API không đúng định dạng.', response.status, value?.error?.code || 'INVALID_RESPONSE');
    return options.withMeta ? { data: value.data, meta: value.meta || {} } : value.data;
  }
  function fileNameFromHeader(value) {
    if (!value) return null;
    const encoded = value.match(/filename\*=UTF-8''([^;]+)/i);
    if (encoded) { try { return decodeURIComponent(encoded[1]); } catch {} }
    const simple = value.match(/filename="?([^";]+)"?/i);
    return simple?.[1] || null;
  }
  async function download(path, preferredName = 'download') {
    const response = await raw(path, { binary: true });
    const blob = await response.blob();
    const safeName = (fileNameFromHeader(response.headers.get('content-disposition')) || preferredName).replace(/[\\/]/g, '_');
    const url = URL.createObjectURL(blob);
    try { const link = document.createElement('a'); link.href = url; link.download = safeName; document.body.append(link); link.click(); link.remove(); }
    finally { setTimeout(() => URL.revokeObjectURL(url), 30000); }
  }
  const app = window.CloudDS = window.CloudDS || {};
  app.api = Object.freeze({
    base: BASE, ApiError, qs, csrf, clearCsrf: () => { csrfToken = null; },
    get: (path, options) => raw(path, options),
    page: path => raw(path, { withMeta: true }),
    post: (path, body) => raw(path, { method: 'POST', body: body ?? {} }),
    patch: (path, body) => raw(path, { method: 'PATCH', body }),
    delete: path => raw(path, { method: 'DELETE' }),
    upload: (path, formData) => raw(path, { method: 'POST', body: formData }),
    download,
  });
})();
