# ベースイメージとして軽量な Python 3.12-slim を使用
FROM python:3.12-slim

# uv を公式イメージからコピー
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 作業ディレクトリを設定
WORKDIR /app

# 環境変数の設定
# 仮想環境を /app 以外の場所に作成することで、ボリュームマウントの影響を避ける
ENV UV_PROJECT_ENVIRONMENT=/venv
ENV PATH="$UV_PROJECT_ENVIRONMENT/bin:$PATH"
ENV UV_COMPILE_BYTECODE=1

# 依存パッケージリスト（requirements.txt）をコピー
COPY requirements.txt .

# 仮想環境の作成と依存パッケージのインストール
RUN uv venv /venv && \
    uv pip install -r requirements.txt

# アプリケーションのソースコードを全てコピー
COPY . .

# コンテナ外部に公開するポートを指定
EXPOSE 5003

# gunicorn を使ってアプリケーションを起動
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5003", "run:app"]
