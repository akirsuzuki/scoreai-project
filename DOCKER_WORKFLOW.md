# Docker開発ワークフロー

## 初回セットアップ

```bash
# 1. Dockerイメージをビルド
docker compose build

# 2. コンテナを起動
docker compose up -d

# 3. サーバーを起動
docker compose exec django python manage.py runserver 0.0.0.0:8000
```

## requirements.txtを更新した場合

`requirements.txt`に新しいライブラリを追加した場合は、**Dockerイメージを再ビルド**する必要があります。

### 方法1: 再ビルドスクリプトを使用（推奨）

```bash
./rebuild_docker.sh
```

### 方法2: 手動で再ビルド

```bash
# イメージを再ビルド
docker compose build --no-cache django

# コンテナを再起動
docker compose up -d
```

## コードを変更した場合

Pythonコード（`.py`ファイル）を変更した場合は、**再ビルドは不要**です。ボリュームマウントにより、変更は自動的に反映されます。

サーバーを再起動するだけでOK:

```bash
# サーバーを再起動（コード変更を反映）
docker compose restart django
```

## よくあるシナリオ

### シナリオ1: 新しいライブラリを追加した

1. `requirements.txt`にライブラリを追加
2. `docker compose build --no-cache django` を実行
3. `docker compose up -d` でコンテナを再起動

### シナリオ2: Pythonコードを変更した

1. コードを編集
2. `docker compose restart django` でサーバーを再起動（または自動リロード）

### シナリオ3: 設定ファイル（settings.py等）を変更した

1. 設定ファイルを編集
2. `docker compose restart django` でサーバーを再起動

## まとめ

| 変更内容 | 必要な操作 |
|---------|----------|
| `requirements.txt`を更新 | `docker compose build --no-cache django` |
| Pythonコード（`.py`）を変更 | `docker compose restart django`（または自動リロード） |
| 設定ファイルを変更 | `docker compose restart django` |
| テンプレート（`.html`）を変更 | 自動リロード（開発モード） |

## トラブルシューティング

### ライブラリが見つからないエラー

```bash
# 1. requirements.txtにライブラリが含まれているか確認
cat requirements.txt | grep [ライブラリ名]

# 2. イメージを再ビルド
docker compose build --no-cache django

# 3. コンテナを再起動
docker compose up -d
```

### 変更が反映されない

```bash
# コンテナを完全に再起動
docker compose down
docker compose up -d
```

