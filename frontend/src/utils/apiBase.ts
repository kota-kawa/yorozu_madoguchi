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
 * EN: Declare the normalizedBase value.
 * JP: normalizedBase の値を宣言する。
 */
const normalizedBase = rawBase ? rawBase.replace(/\/+$/, '') : ''

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
