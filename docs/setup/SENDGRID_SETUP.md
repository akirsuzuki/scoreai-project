# SendGrid設定ガイド

## 概要
SCore AIでは、ユーザー招待メールの送信にSendGridを使用しています。

## SendGridアカウントの作成

1. [SendGrid](https://sendgrid.com/)にアクセス
2. アカウントを作成（無料プラン: 100通/日）
3. メールアドレスを認証

## APIキーの取得

1. SendGridダッシュボードにログイン
2. 左メニューから「Settings」→「API Keys」を選択
3. 「Create API Key」をクリック
4. APIキー名を入力（例: "SCore AI Production"）
5. 権限を選択（「Full Access」または「Mail Send」）
6. 「Create & View」をクリック
7. 表示されたAPIキーをコピー（**この画面を閉じると二度と表示されません**）

## ローカル環境での設定

### 方法1: 環境変数を使用（推奨）

`.env`ファイルまたは環境変数に設定：

```bash
export SENDGRID_API_KEY='SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
export DEFAULT_FROM_EMAIL='noreply@score-ai.net'
```

### 方法2: local_settings.pyに直接設定

`score/local_settings.py`のコメントを外して設定：

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'apikey'
EMAIL_HOST_PASSWORD = 'SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
DEFAULT_FROM_EMAIL = 'noreply@score-ai.net'
```

**注意**: 開発環境では、`EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'`を使用すると、メールがコンソールに出力され、実際には送信されません。

## Heroku環境での設定

### 方法1: Herokuアドオンを使用（推奨）

```bash
# SendGridアドオンを追加
heroku addons:create sendgrid:starter

# 環境変数が自動的に設定されます
# SENDGRID_API_KEY と SENDGRID_USERNAME が設定されます
```

### 方法2: 手動で環境変数を設定

```bash
# SendGrid APIキーを設定
heroku config:set SENDGRID_API_KEY='SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

# 送信元メールアドレスを設定
heroku config:set DEFAULT_FROM_EMAIL='noreply@score-ai.net'
```

## 送信元メールアドレスの設定

SendGridでは、送信元メールアドレスを認証する必要があります：

1. SendGridダッシュボードにログイン
2. 「Settings」→「Sender Authentication」を選択
3. 「Single Sender Verification」または「Domain Authentication」を設定
   - **Single Sender Verification**: 1つのメールアドレスを認証（開発・テスト用）
   - **Domain Authentication**: ドメイン全体を認証（本番環境推奨）

### Single Sender Verification（簡単）

1. 「Create a Sender」をクリック
2. メールアドレスと送信者名を入力
3. 送信された認証メールを確認してリンクをクリック

### Domain Authentication（本番推奨）

1. 「Authenticate Your Domain」をクリック
2. ドメイン名を入力（例: `score-ai.net`）
3. DNSレコードを追加（SendGridが提供するCNAMEレコード）
4. 認証が完了するまで待つ（通常数時間〜24時間）

## 設定の確認

### ローカル環境でのテスト

```bash
# Djangoシェルでテスト
python manage.py shell

# 以下を実行
from django.core.mail import send_mail
send_mail(
    'Test Subject',
    'Test message',
    'noreply@score-ai.net',
    ['your-email@example.com'],
    fail_silently=False,
)
```

### Heroku環境での確認

```bash
# Herokuログを確認
heroku logs --tail

# メール送信のログを確認
heroku logs --tail | grep -i "email\|sendgrid"
```

## トラブルシューティング

### メールが送信されない

1. **APIキーの確認**
   - APIキーが正しく設定されているか確認
   - `heroku config:get SENDGRID_API_KEY` で確認

2. **送信元メールアドレスの認証**
   - SendGridダッシュボードで「Sender Authentication」を確認
   - 認証されていないメールアドレスからは送信できません

3. **ログの確認**
   - Djangoのログでエラーメッセージを確認
   - SendGridダッシュボードの「Activity」で送信状況を確認

4. **レート制限**
   - 無料プランでは100通/日の制限があります
   - 制限に達している場合は、SendGridダッシュボードで確認

### よくあるエラー

- **401 Unauthorized**: APIキーが間違っている、または権限が不足している
- **403 Forbidden**: 送信元メールアドレスが認証されていない
- **429 Too Many Requests**: レート制限に達している

## 参考リンク

- [SendGrid公式ドキュメント](https://docs.sendgrid.com/)
- [Djangoメール送信ドキュメント](https://docs.djangoproject.com/en/5.1/topics/email/)
- [Heroku SendGridアドオン](https://elements.heroku.com/addons/sendgrid)

