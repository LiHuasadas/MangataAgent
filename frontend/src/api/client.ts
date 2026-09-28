/**
 * Unified HTTP Fetch Client with Header Injection and Error Interception
 */

export class ApiError extends Error {
  public status: number;
  public detail: string;

  constructor(status: number, detail: string) {
    super(`API Error [${status}]: ${detail}`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export function getUserId(): string {
  return localStorage.getItem('mangata_user_id') || 'default_user';
}

export function setUserId(userId: string): void {
  localStorage.setItem('mangata_user_id', userId);
}

export function getAuthToken(): string | null {
  return localStorage.getItem('mangata_auth_token');
}

export function setAuthToken(token: string): void {
  localStorage.setItem('mangata_auth_token', token);
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

export async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, headers = {}, body, ...customOptions } = options;

  let url = `${API_BASE}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null) {
        searchParams.append(key, String(val));
      }
    });
    const qs = searchParams.toString();
    if (qs) {
      url += (url.includes('?') ? '&' : '?') + qs;
    }
  }

  const reqHeaders: Record<string, string> = {
    'X-User-ID': getUserId(),
    ...(headers as Record<string, string>),
  };

  const token = getAuthToken();
  if (token && !reqHeaders['Authorization']) {
    reqHeaders['Authorization'] = `Bearer ${token}`;
  }

  // If body is NOT FormData, set default Content-Type to application/json
  if (body && !(body instanceof FormData) && !reqHeaders['Content-Type']) {
    reqHeaders['Content-Type'] = 'application/json';
  }

  const response = await fetch(url, {
    headers: reqHeaders,
    body,
    ...customOptions,
  });

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // Non-JSON response
    }
    throw new ApiError(response.status, errorDetail);
  }

  // If 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}
