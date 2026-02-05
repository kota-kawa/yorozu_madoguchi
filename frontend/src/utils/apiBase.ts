const rawBase = (import.meta.env.VITE_API_BASE || '').trim()
const normalizedBase = rawBase ? rawBase.replace(/\/+$/, '') : ''

export const apiUrl = (path: string) => {
  if (!normalizedBase) {
    return path
  }
  if (!path) {
    return normalizedBase
  }
  return path.startsWith('/') ? `${normalizedBase}${path}` : `${normalizedBase}/${path}`
}
