/**
 * EN: Provide the eslint.config module implementation.
 * JP: eslint.config モジュールの実装を定義する。
 */
import js from '@eslint/js'
import tsParser from '@typescript-eslint/parser'
import tsPlugin from '@typescript-eslint/eslint-plugin'
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
/**
 * EN: Declare the tsRecommendedRules value.
 * JP: tsRecommendedRules の値を宣言する。
 */
const tsRecommendedRules = tsPlugin.configs.recommended.rules

export default [
  {
    ignores: ['dist', 'node_modules', 'node_modules_root_backup'],
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
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parser: tsParser,
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: globals.browser,
    },
    plugins: {
      '@typescript-eslint': tsPlugin,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...baseConfig.rules,
      ...tsRecommendedRules,
      ...hooksConfig.rules,
      ...refreshConfig.rules,
      'no-undef': 'off',
      'no-unused-vars': 'off',
      'react-hooks/set-state-in-effect': 'off',
      '@typescript-eslint/no-unused-vars': ['error', { varsIgnorePattern: '^[A-Z_]' }],
    },
  },
]
