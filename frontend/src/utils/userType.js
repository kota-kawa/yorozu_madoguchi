const USER_TYPE_KEY = 'yorozu_user_type'

export const normalizeUserType = (value) => {
  if (!value) return ''
  const normalized = String(value).trim().toLowerCase()
  return normalized === 'normal' || normalized === 'premium' ? normalized : ''
}

export const getStoredUserType = () => {
  try {
    return normalizeUserType(window.localStorage.getItem(USER_TYPE_KEY))
  } catch {
    return ''
  }
}

export const setStoredUserType = (value) => {
  try {
    window.localStorage.setItem(USER_TYPE_KEY, value)
  } catch {
    // LocalStorage unavailable; rely on in-memory state.
  }
}

export const userTypeKey = USER_TYPE_KEY
