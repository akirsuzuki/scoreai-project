#!/bin/bash
# サーバー起動スクリプト

echo "=== サーバーを起動中 ==="

# コンテナを起動（バックグラウンド）
echo "1. Dockerコンテナを起動..."
docker compose up -d

# サーバーを起動
echo ""
echo "2. Djangoサーバーを起動..."
echo "サーバーは http://localhost:8000 で起動します"
echo ""
echo "停止するには: Ctrl+C を押すか、別のターミナルで 'docker compose stop django' を実行"
echo ""

# サーバーを起動（フォアグラウンドで実行）
docker compose exec django python manage.py runserver 0.0.0.0:8000

