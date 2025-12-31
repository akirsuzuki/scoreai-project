# Heroku本番環境の環境変数設定ガイド

## 必要な環境変数一覧

Heroku本番環境に設定する必要がある環境変数は以下の通りです。

### 必須環境変数

#### 1. Django基本設定
```bash
SECRET_KEY=<本番用のDjango秘密鍵>
DEBUG=False
```

#### 2. Google Gemini API
```bash
GEMINI_API_KEY=<Google Gemini APIキー>
```

#### 3. Google Cloud Vision API
```bash
GOOGLE_APPLICATION_CREDENTIALS=<サービスアカウントキーのJSONファイルのパス>
GOOGLE_CLOUD_PROJECT_ID=<Google CloudプロジェクトID>
```

**注意**: Herokuではファイルシステムが一時的なため、サービスアカウントキーは環境変数としてJSON文字列を設定するか、Heroku Config Varsで設定する必要があります。

#### 4. Stripe（本番環境用）
```bash
STRIPE_PUBLIC_KEY=<本番用のStripe公開キー（pk_live_...）>
STRIPE_SECRET_KEY=<本番用のStripe秘密キー（sk_live_...）>
STRIPE_WEBHOOK_SECRET=<本番用のStripe Webhookシークレット（whsec_...）>
```

#### 5. Google Drive OAuth2（本番環境用）
```bash
GOOGLE_DRIVE_CLIENT_ID=<本番用のOAuth2クライアントID>
GOOGLE_DRIVE_CLIENT_SECRET=<本番用のOAuth2シークレット>
GOOGLE_DRIVE_REDIRECT_URI=<本番用のリダイレクトURI（例: https://your-app.herokuapp.com/storage/google-drive/callback/）>
```

### オプション環境変数

#### Redis（キャッシュ用）
```bash
REDIS_URL=<Redis URL（例: redis://...）>
```

### 自動設定される環境変数

Herokuが自動的に設定する環境変数：
- `DATABASE_URL` - PostgreSQLデータベース接続URL（`dj_database_url`で自動的に読み込まれます）

---

## Herokuでの環境変数設定方法

### 方法1: Heroku CLIを使用（推奨）

#### 個別に設定する場合
```bash
# Herokuにログイン
heroku login

# アプリを指定（アプリ名を確認）
heroku apps

# 環境変数を設定
heroku config:set SECRET_KEY="your-secret-key-here" --app your-app-name
heroku config:set DEBUG="False" --app your-app-name
heroku config:set GEMINI_API_KEY="your-gemini-api-key" --app your-app-name
heroku config:set GOOGLE_CLOUD_PROJECT_ID="your-project-id" --app your-app-name
heroku config:set STRIPE_PUBLIC_KEY="pk_live_..." --app your-app-name
heroku config:set STRIPE_SECRET_KEY="sk_live_..." --app your-app-name
heroku config:set STRIPE_WEBHOOK_SECRET="whsec_..." --app your-app-name
heroku config:set GOOGLE_DRIVE_CLIENT_ID="your-client-id" --app your-app-name
heroku config:set GOOGLE_DRIVE_CLIENT_SECRET="your-client-secret" --app your-app-name
heroku config:set GOOGLE_DRIVE_REDIRECT_URI="https://your-app.herokuapp.com/storage/google-drive/callback/" --app your-app-name
```

#### 一括で設定する場合
```bash
# 環境変数を一括設定（.envファイルから読み込む場合）
heroku config:set $(cat .env | grep -v '^#' | xargs) --app your-app-name
```

### 方法2: Heroku Dashboardを使用

1. [Heroku Dashboard](https://dashboard.heroku.com/)にログイン
2. アプリを選択
3. 「Settings」タブをクリック
4. 「Config Vars」セクションで「Reveal Config Vars」をクリック
5. 「KEY」と「VALUE」を入力して「Add」をクリック

### 方法3: 環境変数を確認

```bash
# すべての環境変数を確認
heroku config --app your-app-name

# 特定の環境変数を確認
heroku config:get SECRET_KEY --app your-app-name
```

---

## 重要な注意事項

### 1. SECRET_KEYの生成

本番環境用の新しいSECRET_KEYを生成してください：

```python
# Djangoシェルで実行
python manage.py shell
>>> from django.core.management.utils import get_random_secret_key
>>> print(get_random_secret_key())
```

または：

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 2. Google Cloudサービスアカウントキーの設定

Herokuではファイルシステムが一時的なため、以下のいずれかの方法で設定します：

#### 方法A: 環境変数としてJSON文字列を設定
```bash
# JSONファイルの内容を環境変数として設定
heroku config:set GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type":"service_account",...}' --app your-app-name
```

その後、`settings.py`で以下のように読み込む：

```python
import json
import os

if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON'):
    import tempfile
    creds_json = json.loads(os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON'))
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
    json.dump(creds_json, temp_file)
    temp_file.close()
    GOOGLE_APPLICATION_CREDENTIALS = temp_file.name
```

#### 方法B: Heroku Config Varsで直接設定
Heroku DashboardのConfig Varsで`GOOGLE_APPLICATION_CREDENTIALS`にJSONファイルのパスを設定（ただし、ファイルをアップロードする必要があります）

### 3. Stripe本番環境キーの取得

1. [Stripe Dashboard](https://dashboard.stripe.com/)にログイン
2. 右上の「Test mode」トグルをオフにして本番モードに切り替え
3. 「Developers」→「API keys」から本番用のキーを取得
4. 「Developers」→「Webhooks」から本番用のWebhookシークレットを取得

### 4. Google Drive OAuth2本番環境設定

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 「APIs & Services」→「Credentials」を選択
3. OAuth2クライアントIDを選択
4. 「Authorized redirect URIs」に本番環境のURIを追加：
   ```
   https://your-app.herokuapp.com/storage/google-drive/callback/
   ```

### 5. 環境変数の確認

設定後、以下のコマンドで確認：

```bash
heroku config --app your-app-name
```

---

## 設定例（完全版）

```bash
# Django基本設定
heroku config:set SECRET_KEY="django-insecure-..." --app your-app-name
heroku config:set DEBUG="False" --app your-app-name

# Google Gemini API
heroku config:set GEMINI_API_KEY="AIzaSy..." --app your-app-name

# Google Cloud Vision API
heroku config:set GOOGLE_CLOUD_PROJECT_ID="s-core-482410" --app your-app-name
# GOOGLE_APPLICATION_CREDENTIALSは方法AまたはBで設定

# Stripe（本番環境）
heroku config:set STRIPE_PUBLIC_KEY="pk_live_51SjBhOAsDtpInVoy..." --app your-app-name
heroku config:set STRIPE_SECRET_KEY="sk_live_51SjBhOAsDtpInVoy..." --app your-app-name
heroku config:set STRIPE_WEBHOOK_SECRET="whsec_..." --app your-app-name

# Google Drive OAuth2（本番環境）
heroku config:set GOOGLE_DRIVE_CLIENT_ID="your-production-client-id" --app your-app-name
heroku config:set GOOGLE_DRIVE_CLIENT_SECRET="your-production-client-secret" --app your-app-name
heroku config:set GOOGLE_DRIVE_REDIRECT_URI="https://your-app.herokuapp.com/storage/google-drive/callback/" --app your-app-name

# Redis（オプション）
heroku config:set REDIS_URL="redis://..." --app your-app-name
```

---

## トラブルシューティング

### 環境変数が読み込まれない場合

1. アプリを再起動：
   ```bash
   heroku restart --app your-app-name
   ```

2. ログを確認：
   ```bash
   heroku logs --tail --app your-app-name
   ```

3. 環境変数を再確認：
   ```bash
   heroku config --app your-app-name
   ```

### サービスアカウントキーのエラー

- JSONファイルの内容が正しいか確認
- 環境変数の設定方法を確認（方法AまたはB）
- `settings.py`での読み込み処理を確認

---

## 参考リンク

- [Heroku Config Vars](https://devcenter.heroku.com/articles/config-vars)
- [Django on Heroku](https://devcenter.heroku.com/articles/django-app-configuration)
- [Stripe API Keys](https://stripe.com/docs/keys)
- [Google Cloud Service Accounts](https://cloud.google.com/iam/docs/service-accounts)


