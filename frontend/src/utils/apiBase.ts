/**
 * EN: Declare the rawBase value.
 * JP: rawBase の値を宣言する。
 */
/**
 * EN: Provide the apiBase module implementation.
 * JP: apiBase モジュールの実装を定義する。
 */
const rawBase = (import.meta.env.VITE_API_BASE || '').trim()

/**
 * EN: Declare the resolveLocalFallbackBase value.
 * JP: resolveLocalFallbackBase の値を宣言する。
 */
const resolveLocalFallbackBase = () => {
  if (import.meta.env.DEV || typeof window === 'undefined') {
    return ''
  }

  const { protocol, hostname } = window.location
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return `${protocol}//${hostname}:5003`
  }

  return ''
}
/**
 * EN: Declare the normalizedBase value.
 * JP: normalizedBase の値を宣言する。
 */
const normalizedBase = (rawBase || resolveLocalFallbackBase()).replace(/\/+$/, '')

/**
 * EN: Declare the apiUrl value.
 * JP: apiUrl の値を宣言する。
 */
export const apiUrl = (path: string) => {
  if (!normalizedBase) {
    return path
  }
  if (!path) {
    return normalizedBase
  }
  return path.startsWith('/') ? `${normalizedBase}${path}` : `${normalizedBase}/${path}`
}
