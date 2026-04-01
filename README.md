> 一番下に日本語版もあります

# 🌟 Yorozu Madoguchi (よろず窓口)

![Backend](https://img.shields.io/badge/Backend-Flask-black)
![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20TypeScript-61DAFB)
![Bundler](https://img.shields.io/badge/Bundler-Vite-646CFF)
![DB](https://img.shields.io/badge/DB-PostgreSQL-336791)
![Cache](https://img.shields.io/badge/Cache-Redis-DC382D)
![AI](https://img.shields.io/badge/AI-Groq-orange)
![Container](https://img.shields.io/badge/Container-Docker-2496ED)

**Yorozu Madoguchi** is an AI-assisted travel planning web app where users chat with an assistant and receive personalized itineraries. It is designed to demonstrate end-to-end product thinking: conversational UX, robust backend services, and a modern frontend—all orchestrated with Docker Compose for easy onboarding.

👉 **Try it now: [https://chat.project-kk.com/](https://chat.project-kk.com/)**

## UI Preview

<p align="center">
  <img src="assets/images/Yorozu-Madoguchi-ScreenShot.png" alt="Yorozu Madoguchi UI Preview" width="1100">
</p>

## 🎬 Demo Video

A glimpse of planning a trip together with the user. Click a thumbnail to open the video on YouTube.

<a href="https://youtu.be/g3DgbxYkKDw">
  <img src="https://img.youtube.com/vi/g3DgbxYkKDw/hqdefault.jpg" alt="Demo Video" width="100%">
</a>

## 🔎 Highlights (for recruiters)

- **Product-focused AI UX**: Converts free-form chat into actionable travel plans, showcasing how to bridge natural language input with structured outcomes.
- **Full-stack architecture**: React + Vite frontend, Flask API, PostgreSQL, and Redis wired together with Docker Compose for reproducible development.
- **Maintainability & growth-ready**: Clear service boundaries, environment-based configuration, and a containerized workflow that mirrors production practices.

## 🧰 Tech Stack

- **Frontend**: React, Vite (fast dev server, modern tooling)
- **Backend**: Python (Flask)
- **Data**: PostgreSQL, Redis
- **Infra**: Docker, Docker Compose

## 🧭 Design Decisions

- **Why Flask**: Lightweight and explicit API structure was a good fit for a chat-first backend, with fast iteration and clear route-level control.
- **Why Redis for session state**: Chat history and decision context require low-latency read/write access; Redis provides simple key-based storage with TTL support.
- **Why PostgreSQL for reservation data**: Finalized plans are relational and persistent; PostgreSQL offers reliability, indexing, and straightforward queryability.
- **Why React + Vite**: React gives composable UI state management, while Vite keeps frontend feedback loops fast during frequent UX iteration.
- **Why Docker Compose**: Keeps local setup reproducible across frontend, backend, DB, and cache, mirroring production-like service boundaries.

## 🏗️ Architecture

```mermaid
flowchart LR
    U[User Browser]

    subgraph DC[Docker Compose]
        FE[Frontend<br/>React + Vite]
        API[Backend API<br/>Flask]
        PG[(PostgreSQL)]
        RD[(Redis)]
    end

    LLM[Groq API]

    U -->|HTTPS| FE
    FE -->|/api/*| API
    API --> PG
    API --> RD
    API -->|LLM calls| LLM
```

## ▶️ Quick Start (Docker Compose only)

> **Prerequisites:** Docker Desktop (or Docker Engine + Docker Compose plugin)

1. Create an environment file from the example:

```bash
cp .env.example .env
```

2. Build and start all services:

```bash
docker compose up --build
```

3. Open the app in your browser:

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:5003

4. Stop the services when finished:

```bash
docker compose down
```

## 🧪 Tests

```bash
python3 tests/run_unit_tests.py
```

Coverage report:

```bash
coverage run --branch tests/run_unit_tests.py
coverage report -m --omit='tests/*'
```

## 🗃️ Database Migrations (Alembic)

Apply the latest schema version:

```bash
alembic upgrade head
```

Rollback one revision:

```bash
alembic downgrade -1
```

Check current revision:

```bash
alembic current
```

## 📜 License

Apache License 2.0. See `LICENSE` for details.

---

<details>
<summary>日本語版（クリックして開く）</summary>

# 🌟 よろず窓口 (Yorozu Madoguchi)

**「よろず窓口」** は、AIとチャットしながら旅行プランを作成できるWebアプリです。会話形式のUXと、フロントエンド・バックエンド・データ基盤を一体化した構成により、プロダクトとしての完成度と拡張性を意識して設計しています。

👉 **今すぐ試す: [https://chat.project-kk.com/](https://chat.project-kk.com/)**

## UI プレビュー

<p align="center">
  <img src="assets/images/Yorozu-Madoguchi-ScreenShot.png" alt="よろず窓口 UI プレビュー" width="1100">
</p>

## 🎬 デモ動画

ユーザーと旅行計画をしている様子です。サムネイルをクリックするとYouTubeで動画を開きます。

<a href="https://youtu.be/g3DgbxYkKDw">
  <img src="https://img.youtube.com/vi/g3DgbxYkKDw/hqdefault.jpg" alt="デモ動画" width="100%">
</a>

## 🔎 就職活動向けのアピールポイント

- **会話UXの実装**: 自然言語の入力を、具体的な旅行プランに変換する設計で、ユーザー価値を意識したプロダクト開発力を示せます。
- **フルスタック構成**: React + Vite のフロント、Flask API、PostgreSQL/Redis を Docker Compose で統合。
- **運用に近い開発体験**: 環境変数管理・サービス分離・コンテナ化により、実運用を想定した開発フローを構築。

## 🧰 技術スタック

- **フロントエンド**: React, Vite
- **バックエンド**: Python (Flask)
- **データ基盤**: PostgreSQL, Redis
- **インフラ**: Docker, Docker Compose

## 🧭 技術的な意思決定（Design Decisions）

- **なぜ Flask を選んだか**: 軽量で構造が明快なため、チャット中心APIの実装と高速な改善サイクルに適しているためです。
- **なぜ Redis をセッション管理に使ったか**: チャット履歴や意思決定コンテキストを低遅延で読み書きでき、TTLで期限管理もしやすいためです。
- **なぜ PostgreSQL を使ったか**: 確定した予約情報は永続化と整合性が重要で、リレーショナルな検索・拡張に強いためです。
- **なぜ React + Vite を使ったか**: ReactでUI状態を分割管理しやすく、Viteで試行錯誤時の開発体験を高速化できるためです。
- **なぜ Docker Compose を使ったか**: フロント・API・DB・Redisを同じ手順で再現でき、環境差分を減らせるためです。

## 🏗️ アーキテクチャ

```mermaid
flowchart LR
    U[ユーザーのブラウザ]

    subgraph DC[Docker Compose]
        FE[フロントエンド<br/>React + Vite]
        API[バックエンド API<br/>Flask]
        PG[(PostgreSQL)]
        RD[(Redis)]
    end

    LLM[Groq API]

    U -->|HTTPS| FE
    FE -->|/api/*| API
    API --> PG
    API --> RD
    API -->|LLM 呼び出し| LLM
```

## ▶️ 実行方法（Docker Composeで一本化）

> **前提:** Docker Desktop（または Docker Engine + Compose プラグイン）

1. `.env` を作成します。

```bash
cp .env.example .env
```

2. サービスを起動します。

```bash
docker compose up --build
```

3. ブラウザからアクセスします。

- **フロントエンド**: http://localhost:5173
- **バックエンド API**: http://localhost:5003

4. 終了時は次のコマンドで停止します。

```bash
docker compose down
```

## 🧪 テスト

```bash
python3 tests/run_unit_tests.py
```

カバレッジ計測:

```bash
coverage run --branch tests/run_unit_tests.py
coverage report -m --omit='tests/*'
```

## 📜 ライセンス

Apache License 2.0（詳細は `LICENSE` を参照）

</details>
