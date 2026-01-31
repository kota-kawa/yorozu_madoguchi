# Project Specifications & Guidelines

## 全体ルール (General Rules)
<!-- プロジェクト全体で遵守すべき原則 -->
- [ ] フロントエンドは段階的にTypeScriptへ移行し、既存の挙動を壊さないことを最優先にする
- [ ] 仕様変更は行わず、型安全性の向上と保守性改善を目的とする
- [ ] 変更単位は小さくし、移行対象外の箇所へ影響を広げない
- [ ] 残りのページ移行は既存のprops/フローを維持し、必要最小限の型付けのみ行う

## コーディング規約 (Coding Conventions)
<!-- 言語ごとのスタイルガイド、フォーマッター設定など -->
- **Python**:
  - 既存のスタイルを維持
- **JavaScript/React**:
  - 新規・変更箇所はTypeScriptで記述する（可能な範囲で）
  - Reactコンポーネントは関数コンポーネントを維持
  - APIレスポンスは型定義 or 型ガードを用意する
  - ページコンポーネントは `*.tsx` 化し、props型は明示する（必要な場合のみ）

## 命名規則 (Naming Conventions)
<!-- 変数、関数、クラス、ファイル名の命名ルール -->
- **Variables/Functions**: camelCase
- **Classes/Types**: PascalCase
- **Files**: ReactコンポーネントはPascalCase、その他はcamelCase
- **Constants**: UPPER_SNAKE_CASE

## ディレクトリ構成方針 (Directory Structure Policy)
<!-- ファイルの配置ルール、モジュール分割の方針 -->
- フロントエンドの型定義は `frontend/src/types/` に集約する
- Worker関連の型は `frontend/src/workers/` か `frontend/src/types/` に置く

## エラーハンドリング方針 (Error Handling Policy)
<!-- 例外処理、ログ出力、ユーザーへのフィードバック方法 -->
- フロントエンドのAPI失敗時は既存のユーザー向けメッセージを維持する
- 例外はログ出力しつつ、UI上の表示は現行の文言を踏襲

## テスト方針 (Testing Policy)
<!-- テストの種類、カバレッジ目標、使用ツール -->
- **Unit Tests**: 今回は追加しない（移行優先）
- **E2E Tests**: 既存の手動確認を維持
