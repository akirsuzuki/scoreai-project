#!/bin/bash
# テスト環境セットアップスクリプト

echo "=== テスト環境セットアップ ==="

# Dockerコンテナが起動しているか確認
echo "1. Dockerコンテナの状態を確認..."
docker compose ps

# 必要なライブラリをインストール
echo ""
echo "2. 必要なライブラリをインストール..."
docker compose exec django pip install -r requirements.txt

# インストールされたライブラリを確認
echo ""
echo "3. インストールされたライブラリを確認..."
docker compose exec django pip list | grep -E "(chardet|google-generativeai|google-cloud-vision|pdf2image|Pillow)"

# Djangoのマイグレーションを確認
echo ""
echo "4. Djangoマイグレーションの状態を確認..."
docker compose exec django python manage.py showmigrations

# サーバーを起動（バックグラウンド）
echo ""
echo "5. サーバーを起動..."
echo "サーバーは http://localhost:8000 で起動します"
echo "停止するには: docker compose stop django"
docker compose up -d django

echo ""
echo "=== セットアップ完了 ==="
echo ""
echo "次のステップ:"
echo "1. ブラウザで http://localhost:8000 にアクセス"
echo "2. TESTING_GUIDE.md に従ってテストを実行"
echo "3. ログを確認: docker compose logs -f django"
