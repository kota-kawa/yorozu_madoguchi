/**
 * EN: Declare the USER_TYPE_KEY value.
 * JP: USER_TYPE_KEY の値を宣言する。
 */
/**
 * EN: Provide the userType module implementation.
 * JP: userType モジュールの実装を定義する。
 */
const USER_TYPE_KEY = 'yorozu_user_type'

/**
 * EN: Declare the normalizeUserType value.
 * JP: normalizeUserType の値を宣言する。
 */
export const normalizeUserType = (value) => {
  if (!value) return ''
  /**
   * EN: Declare the normalized value.
   * JP: normalized の値を宣言する。
   */
  const normalized = String(value).trim().toLowerCase()
  return normalized === 'normal' || normalized === 'premium' ? normalized : ''
}

/**
 * EN: Declare the getStoredUserType value.
 * JP: getStoredUserType の値を宣言する。
 */
export const getStoredUserType = () => {
  try {
    return normalizeUserType(window.localStorage.getItem(USER_TYPE_KEY))
  } catch {
    return ''
  }
}

/**
 * EN: Declare the setStoredUserType value.
 * JP: setStoredUserType の値を宣言する。
 */
export const setStoredUserType = (value) => {
  try {
    window.localStorage.setItem(USER_TYPE_KEY, value)
  } catch {
    // LocalStorage unavailable; rely on in-memory state.
  }
}

/**
 * EN: Declare the userTypeKey value.
 * JP: userTypeKey の値を宣言する。
 */
export const userTypeKey = USER_TYPE_KEY
