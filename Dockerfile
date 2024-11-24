# ベースイメージを指定
FROM python:3.12-slim

# 作業ディレクトリを作成
RUN mkdir -p /app

# 依存関係のファイルをコピー
COPY requirements.txt /app

# 作業ディレクトリを設定
WORKDIR /app

# システム依存関係をインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をインストール
RUN pip install --no-cache-dir -r ./requirements.txt

# アプリケーションコードをコピー
COPY . /app

# 環境変数を設定（必要に応じて）
ENV PYTHONUNBUFFERED=1

# デバッグ用: ディレクトリの内容を表示
RUN ls -la

# 静的ファイルを収集
RUN python3 manage.py collectstatic --noinput

# アプリケーションを起動
# CMD gunicorn --bind 0.0.0.0:$PORT app.wsgi

