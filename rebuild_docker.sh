#!/bin/bash
# Dockerイメージを再ビルドして、requirements.txtの変更を反映するスクリプト

echo "=== Dockerイメージを再ビルド中 ==="
echo "requirements.txtの変更が反映されます..."

# Dockerイメージを再ビルド（キャッシュを使わない）
docker compose build --no-cache django

echo ""
echo "=== 再ビルド完了 ==="
echo ""
echo "コンテナを起動:"
echo "  docker compose up -d"
echo ""
echo "サーバーを起動:"
echo "  docker compose exec django python manage.py runserver 0.0.0.0:8000"

