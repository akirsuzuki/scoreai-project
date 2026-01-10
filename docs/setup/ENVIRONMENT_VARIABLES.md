# 環境変数設定ガイド

本ドキュメントでは、SCore AIアプリケーションで使用する環境変数の設定方法を統一して説明します。

## 環境変数の一覧

### 必須環境変数

| 変数名 | 説明 | 設定例 |
|--------|------|--------|
| `SECRET_KEY` | Djangoのシークレットキー | `django-insecure-...` |
| `SENDGRID_API_KEY` | SendGrid APIキー | `SG.xxxxxxxxxxxxxxxx...` |
| `DEFAULT_FROM_EMAIL` | 送信元メールアドレス | `noreply@score-ai.net` |

### オプション環境変数

| 変数名 | 説明 | 設定例 |
|--------|------|--------|
| `GEMINI_API_KEY` | Google Gemini APIキー | `AIzaSy...` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google Cloud認証情報のパス | `/app/credentials/...` |
| `STRIPE_PUBLIC_KEY` | Stripe公開キー | `pk_test_...` |
| `STRIPE_SECRET_KEY` | Stripeシークレットキー | `sk_test_...` |
| `STRIPE_WEBHOOK_SECRET` | Stripe Webhookシークレット | `whsec_...` |
| `DEBUG` | デバッグモード | `True` / `False` |

## 環境別の設定方法

### ローカル環境（Docker Compose）

#### 方法1: `.env`ファイルを使用（推奨）

プロジェクトルートに`.env`ファイルを作成：

```bash
# .env
SECRET_KEY=django-insecure-your-secret-key-here
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DEFAULT_FROM_EMAIL=noreply@score-ai.net
GEMINI_API_KEY=AIzaSy...
DEBUG=True
```

`docker-compose.yml`で`.env`ファイルを読み込む：

```yaml
services:
  django:
    env_file:
      - .env
    # ... その他の設定
```

#### 方法2: `docker-compose.yml`に直接記述

```yaml
services:
  django:
    environment:
      - SECRET_KEY=django-insecure-your-secret-key-here
      - SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
      - DEFAULT_FROM_EMAIL=noreply@score-ai.net
    # ... その他の設定
```

### 本番環境（Heroku）

```bash
# SendGrid設定
heroku config:set SENDGRID_API_KEY='SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
heroku config:set DEFAULT_FROM_EMAIL='noreply@score-ai.net'

# その他の環境変数
heroku config:set SECRET_KEY='your-secret-key'
heroku config:set GEMINI_API_KEY='AIzaSy...'
heroku config:set DEBUG='False'
```

### 本番環境（その他のホスティング）

環境変数を設定する方法はホスティングサービスによって異なりますが、基本的には以下の方法があります：

1. **コントロールパネルから設定**
   - ホスティングサービスの管理画面から環境変数を設定

2. **設定ファイルから読み込み**
   - `.env`ファイルや設定ファイルから読み込み

3. **シェルスクリプトで設定**
   ```bash
   export SENDGRID_API_KEY='SG.xxxxxxxxxxxxxxxx...'
   export DEFAULT_FROM_EMAIL='noreply@score-ai.net'
   ```

## SendGrid設定の詳細

### APIキーの取得方法

1. [SendGrid](https://sendgrid.com/)にログイン
2. 「Settings」→「API Keys」を選択
3. 「Create API Key」をクリック
4. APIキー名を入力（例: "SCore AI Production"）
5. 権限を選択：
   - **推奨**: 「Restricted Access（カスタム）」を選択し、「Mail Send」権限のみを有効化
   - ユーザー登録時の認証メール送信が主な用途のため、「Mail Send」権限で十分です
   - セキュリティの観点から、必要最小限の権限を付与することを推奨します
6. 「Create & View」をクリック
7. APIキーをコピー（**この画面を閉じると二度と表示されません**）

### 送信元メールアドレスの認証

SendGridでは送信元メールアドレスを認証する必要があります：

1. 「Settings」→「Sender Authentication」を選択
2. 「Single Sender Verification」または「Domain Authentication」を設定
3. 認証メールを確認してリンクをクリック（Single Senderの場合）

詳細は`docs/setup/SENDGRID_SETUP.md`を参照してください。

## 設定の確認

### ローカル環境での確認

```bash
# SendGrid設定を確認
docker compose exec django python manage.py test_sendgrid --to your-email@example.com --check-only

# テストメールを送信
docker compose exec django python manage.py test_sendgrid --to your-email@example.com
```

### Heroku環境での確認

```bash
# 環境変数を確認
heroku config

# 特定の環境変数を確認
heroku config:get SENDGRID_API_KEY
heroku config:get DEFAULT_FROM_EMAIL
```

## セキュリティに関する注意事項

1. **`.env`ファイルをGitにコミットしない**
   - `.gitignore`に`.env`を追加
   - 機密情報を含むファイルはリポジトリに含めない

2. **本番環境では環境変数を使用**
   - `local_settings.py`に直接値を書かない
   - 環境変数から取得するように設定

3. **APIキーの管理**
   - 定期的にAPIキーをローテーション
   - 不要になったAPIキーは削除

## トラブルシューティング

### 環境変数が読み込まれない

1. `.env`ファイルの場所を確認（プロジェクトルート）
2. `docker-compose.yml`で`env_file`が正しく設定されているか確認
3. コンテナを再起動：`docker compose restart`

### SendGrid設定が反映されない

1. 環境変数が正しく設定されているか確認
2. `local_settings.py`の設定を確認
3. アプリケーションを再起動

