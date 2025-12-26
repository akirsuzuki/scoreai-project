#!/bin/bash
# 必要なライブラリをインストールするスクリプト

echo "=== 必要なライブラリをインストール中 ==="

# Dockerコンテナ内でライブラリをインストール
docker compose exec django pip install --upgrade pip
docker compose exec django pip install google-generativeai google-cloud-vision chardet pdf2image Pillow

echo ""
echo "=== インストール完了 ==="
echo ""
echo "インストールされたライブラリを確認:"
docker compose exec django pip list | grep -E "(google-generativeai|google-cloud-vision|chardet|pdf2image|Pillow)"

