# ベースイメージとして軽量な Python 3.9-slim を使用
FROM python:3.9-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なシステムパッケージがあればインストール（必要に応じてコメントアウトを解除）
# RUN apt-get update && apt-get install -y build-essential

# 依存パッケージリスト（requirements.txt）をコピー
COPY requirements.txt .

# pip のアップグレードと依存パッケージのインストール
RUN pip install --upgrade pip && pip install -r requirements.txt

# アプリケーションのソースコードを全てコピー
COPY . .

# コンテナ外部に公開するポートを指定
EXPOSE 5003

# gunicorn を使ってアプリケーションを起動
#CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5003", "run:app"]

########## デバッグ用の実行 ##############
# Flask の環境変数を設定（run.py がエントリーポイントの場合）
ENV FLASK_APP=run.py
ENV FLASK_ENV=development
CMD ["flask", "run", "--host=0.0.0.0", "--port=5003"]