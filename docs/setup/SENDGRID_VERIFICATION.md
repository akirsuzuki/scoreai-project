# SendGrid設定の検証方法

SendGrid設定を検証する方法を説明します。

## 方法1: 検証スクリプトを使用（推奨）

### Dockerコンテナ内で実行

```bash
# Dockerコンテナに入る
docker exec -it django bash

# 検証スクリプトを実行（設定値とAPIキーの形式のみ確認）
python3 verify_sendgrid.py

# または、Docker Composeを使用
docker-compose exec django python3 verify_sendgrid.py
```

### 検証内容

1. **設定値の確認**
   - `EMAIL_BACKEND`
   - `EMAIL_HOST`
   - `EMAIL_PORT`
   - `EMAIL_USE_TLS`
   - `EMAIL_HOST_USER`
   - `DEFAULT_FROM_EMAIL`
   - `SENDGRID_API_KEY`（マスク表示）

2. **APIキーの形式チェック**
   - APIキーが "SG." で始まるか
   - APIキーの長さが適切か（50-100文字）

3. **SendGrid APIでの検証**（`requests`モジュールが必要）
   - APIキーが有効か
   - ユーザー情報の取得

4. **送信元メールアドレスの認証確認**（`requests`モジュールが必要）
   - 送信元メールアドレスが認証済みか

## 方法2: Django管理コマンドを使用

### 設定のみ確認

```bash
# Dockerコンテナ内で実行
docker exec -it django python manage.py test_sendgrid --check-only --to dummy@example.com
```

### 実際にメール送信をテスト

```bash
# Dockerコンテナ内で実行
docker exec -it django python manage.py test_sendgrid --to <送信先メールアドレス>
```

例:
```bash
docker exec -it django python manage.py test_sendgrid --to your-email@example.com
```

## 方法3: Djangoシェルで直接確認

```bash
# Dockerコンテナ内で実行
docker exec -it django python manage.py shell
```

シェル内で以下を実行:

```python
from django.conf import settings
from django.core.mail import send_mail

# 設定値の確認
print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")

# APIキーの確認（マスク表示）
api_key = settings.EMAIL_HOST_PASSWORD
if api_key:
    masked_key = api_key[:8] + '...' + api_key[-4:] if len(api_key) > 12 else '***'
    print(f"SENDGRID_API_KEY: {masked_key}")

# テストメール送信
try:
    send_mail(
        '[SCore AI] SendGrid設定テスト',
        'これはSendGrid設定のテストメールです。',
        settings.DEFAULT_FROM_EMAIL,
        ['your-email@example.com'],
        fail_silently=False,
    )
    print("✓ メール送信に成功しました")
except Exception as e:
    print(f"✗ メール送信に失敗しました: {str(e)}")
```

## トラブルシューティング

### APIキーが無効な場合

1. SendGridダッシュボードでAPIキーが有効か確認
   - https://app.sendgrid.com/settings/api_keys
2. APIキーが削除されていないか確認
3. APIキーに 'Mail Send' 権限があるか確認

### 送信元メールアドレスが認証されていない場合

1. SendGridダッシュボードにログイン
   - https://app.sendgrid.com/
2. 「Settings」→「Sender Authentication」→「Single Sender Verification」を選択
3. 「Create New Sender」をクリック
4. From Email Address に送信元メールアドレスを入力
5. その他の必須項目を入力して「Create」をクリック
6. 送信された認証メールのリンクをクリックして認証を完了

詳細: https://sendgrid.com/docs/for-developers/sending-email/sender-identity/

### メールが届かない場合

1. SendGridダッシュボードの「Activity」で送信状況を確認
   - https://app.sendgrid.com/activity
2. スパムフォルダを確認
3. 送信先メールアドレスが正しいか確認
4. SendGridの送信制限に達していないか確認（無料プラン: 100通/日）

## 現在の設定値

設定値は `score/local_settings.py` または環境変数から読み込まれます。

- `SENDGRID_API_KEY`: SendGrid APIキー
- `DEFAULT_FROM_EMAIL`: 送信元メールアドレス（デフォルト: `noreply@score-ai.net`）

本番環境では環境変数から取得されます（`score/settings.py`参照）。
