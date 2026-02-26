/**
 * EN: Provide the eslint.config module implementation.
 * JP: eslint.config モジュールの実装を定義する。
 */
import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'

/**
 * EN: Declare the baseConfig value.
 * JP: baseConfig の値を宣言する。
 */
const baseConfig = js.configs.recommended
/**
 * EN: Declare the hooksConfig value.
 * JP: hooksConfig の値を宣言する。
 */
const hooksConfig = reactHooks.configs.flat.recommended
/**
 * EN: Declare the refreshConfig value.
 * JP: refreshConfig の値を宣言する。
 */
const refreshConfig = reactRefresh.configs.vite

export default [
  {
    ignores: ['dist'],
  },
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...baseConfig.rules,
      ...hooksConfig.rules,
      ...refreshConfig.rules,
      'no-unused-vars': ['error', { varsIgnorePattern: '^[A-Z_]' }],
    },
  },
]
