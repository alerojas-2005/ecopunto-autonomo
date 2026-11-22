const defaultApiBaseUrl = 'http://127.0.0.1:8000/api/v1'

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL?.trim() || defaultApiBaseUrl).replace(/\/+$/, '')

type RequestOptions = {
  token?: string
  body?: unknown
  signal?: AbortSignal
}

export class ApiError extends Error {
  readonly status: number | null
  readonly details?: unknown

  constructor(
    message: string,
    status: number | null,
    details?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }

  get isUnauthorized() {
    return this.status === 401
  }
}

function detailMessage(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map(item => {
        if (typeof item === 'string') return item
        if (typeof item === 'object' && item !== null && 'msg' in item) {
          const message = String(item.msg)
          const location = 'loc' in item && Array.isArray(item.loc)
            ? item.loc.filter((part: unknown) => part !== 'body').map(String).join(' → ')
            : ''
          return location ? `${location}: ${message}` : message
        }
        return 'Revisa los datos ingresados.'
      })
      .join(' ')
  }
  return 'No fue posible completar la solicitud.'
}

async function request<T>(path: string, method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE', options: RequestOptions = {}): Promise<T> {
  const headers = new Headers({ Accept: 'application/json' })
  if (options.body !== undefined) headers.set('Content-Type', 'application/json')
  if (options.token) headers.set('Authorization', `Bearer ${options.token}`)

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`, {
      method,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(`No se pudo conectar con EcoPunto (${API_BASE_URL}). Verifica que el backend esté en ejecución y que CORS permita este origen.`, null, error)
  }

  const responseText = await response.text()
  let payload: unknown
  if (responseText) {
    try {
      payload = JSON.parse(responseText) as unknown
    } catch {
      payload = responseText
    }
  }

  if (!response.ok) {
    const detail = typeof payload === 'object' && payload !== null && 'detail' in payload
      ? payload.detail
      : undefined
    throw new ApiError(detailMessage(detail), response.status, detail ?? payload)
  }

  return payload as T
}

export function apiGet<T>(path: string, token?: string, signal?: AbortSignal): Promise<T> {
  return request<T>(path, 'GET', { token, signal })
}

export function apiPost<T, TBody>(path: string, body: TBody, token?: string, signal?: AbortSignal): Promise<T> {
  return request<T>(path, 'POST', { body, token, signal })
}

export function apiPut<T, TBody>(path: string, body: TBody, token?: string, signal?: AbortSignal): Promise<T> {
  return request<T>(path, 'PUT', { body, token, signal })
}

export function apiDelete<T>(path: string, token?: string): Promise<T> {
  return request<T>(path, 'DELETE', { token })
}

export function apiPatch<T, TBody>(path: string, body: TBody, token?: string, signal?: AbortSignal): Promise<T> {
  return request<T>(path, 'PATCH', { body, token, signal })
}
