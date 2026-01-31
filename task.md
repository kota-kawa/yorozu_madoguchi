# Current Task Context

## 今回やること・目的 (Goal/Objective)
<!-- 何のために何をするのか簡潔に記述 -->
- [ ] フロントエンドの重要箇所を優先してTypeScriptへ段階的に移行し、型安全性を高める
- [ ] 残りのページコンポーネントをTypeScript化し、型を明確にする

## やること (Must)
<!-- 具体的なタスクリスト -->
- [ ] `frontend` にTypeScript導入（`typescript` 追加、`tsconfig.json` 追加）
- [ ] まずは型の恩恵が大きい箇所をTS化
  - `frontend/src/hooks/`（チャット系 hooks）
  - `frontend/src/components/Chat/`（Message表示関連）
  - `frontend/src/utils/streamHelper.js` と `frontend/src/workers/textGeneratorWorker.js`
- [ ] 共有型（Message、APIレスポンス、Workerメッセージ）を `frontend/src/types/` に作成
- [ ] `ChatInput` のイベント型の扱いを整理（擬似イベントから値渡しへ寄せる）
- [ ] 残りのページを `*.tsx` に移行
  - `frontend/src/main.jsx`
  - `frontend/src/App.jsx`
  - `frontend/src/pages/CompletePage.jsx`
  - `frontend/src/pages/TravelPage.jsx`
  - `frontend/src/pages/ReplyPage.jsx`
  - `frontend/src/pages/FitnessPage.jsx`
  - `frontend/src/pages/JobPage.jsx`
  - `frontend/src/pages/StudyPage.jsx`
- [ ] ページ移行時に必要な型定義を追加（props/イベント/返却型）

## やらないこと (Non-goals)
<!-- 今回のスコープ外のこと -->
- [ ] すべてのページ/コンポーネントを一括でTS化しない
- [ ] 既存のUI/挙動の変更は行わない
- [ ] バックエンド側の変更はしない
- [ ] ルーティング構成やページ遷移の仕様変更は行わない

## 受け入れ基準 (Acceptance Criteria)
<!-- 完了とみなす条件 -->
- [ ] 既存の動作が変わらないこと（チャット送信、表示、プラン保存）
- [ ] 移行対象のTSファイルで型エラーが出ないこと
- [ ] ビルド/開発起動が通ること（`vite`）
- [ ] 主要ページ（Travel/Reply/Fitness/Job/Study/Complete）の表示・遷移が維持されること

## 影響範囲 (Impact/Scope)
<!-- 変更するファイルや注意すべき既存機能 -->
- **触るファイル**:
  - `frontend/package.json`
  - `frontend/tsconfig.json`
  - `frontend/vite.config.*`
  - `frontend/src/hooks/*`
  - `frontend/src/components/Chat/*`
  - `frontend/src/utils/streamHelper.*`
  - `frontend/src/workers/textGeneratorWorker.*`
  - `frontend/src/types/*`
  - `frontend/src/main.*`
  - `frontend/src/App.*`
  - `frontend/src/pages/*`
- **壊しちゃいけない挙動**:
  - チャットの送受信・ストリーミング表示
  - Yes/No・選択肢・日付入力の動作
  - プラン保存と完了画面遷移
