# SendGridメール送信テスト手順

送信元メールアドレスが認証済み（verified）の場合、実際にメール送信ができるかテストします。

## 方法1: Django管理コマンドでテスト（推奨）

### テストメールを送信

```bash
# Dockerコンテナ内で実行
docker exec -it django python manage.py test_sendgrid --to <送信先メールアドレス>
```

例:
```bash
docker exec -it django python manage.py test_sendgrid --to your-email@example.com
```

### 設定のみ確認（メール送信なし）

```bash
docker exec -it django python manage.py test_sendgrid --check-only --to dummy@example.com
```

## 方法2: 検証スクリプトで確認

```bash
# Dockerコンテナ内で実行
docker exec -it django python3 verify_sendgrid.py
```

このスクリプトは以下を確認します：
- 設定値の確認
- APIキーの形式チェック
- SendGrid APIでの検証
- 送信元メールアドレスの認証状態確認

## 方法3: Djangoシェルで直接テスト

```bash
# Dockerコンテナ内で実行
docker exec -it django python manage.py shell
```

シェル内で以下を実行:

```python
from django.conf import settings
from django.core.mail import send_mail

# 設定値の確認
print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")

# テストメール送信
try:
    send_mail(
        '[SCore AI] SendGrid設定テスト',
        'これはSendGrid設定のテストメールです。\n\n送信元メールアドレスが認証済みの場合、このメールが届くはずです。',
        settings.DEFAULT_FROM_EMAIL,
        ['your-email@example.com'],  # ここに送信先メールアドレスを入力
        fail_silently=False,
    )
    print("✓ メール送信に成功しました")
    print("  送信先メールアドレスを確認してください（スパムフォルダも確認）")
except Exception as e:
    print(f"✗ メール送信に失敗しました: {str(e)}")
```

## 期待される結果

### 成功した場合

- メールが送信先に届く
- SendGridダッシュボードの「Activity」に送信履歴が表示される
- エラーメッセージが表示されない

### 失敗した場合

エラーメッセージの例：
- `550 The from address does not match a verified Sender Identity.`
  - → 送信元メールアドレスが認証されていません
- `401 Unauthorized`
  - → APIキーが無効です
- `403 Forbidden`
  - → APIキーに権限がありません

## トラブルシューティング

### メールが届かない場合

1. **スパムフォルダを確認**
   - 認証メールと同様、スパムフォルダに入っている可能性があります

2. **SendGridダッシュボードの「Activity」を確認**
   - https://app.sendgrid.com/activity
   - メールが送信されているか確認
   - エラーメッセージがあるか確認

3. **送信制限を確認**
   - 無料プラン: 100通/日
   - 送信制限に達していないか確認

4. **送信先メールアドレスを確認**
   - 正しいメールアドレスを入力しているか確認

### エラーメッセージが表示される場合

1. **APIキーを確認**
   - SendGridダッシュボードでAPIキーが有効か確認
   - APIキーに「Mail Send」権限があるか確認

2. **送信元メールアドレスの認証状態を確認**
   - SendGridダッシュボードで「verified」になっているか確認
   - `score/local_settings.py`の`DEFAULT_FROM_EMAIL`が認証済みのメールアドレスと一致しているか確認

## 現在の設定

- **送信元メールアドレス**: `noreply@score-ai.net`（`score/local_settings.py`で設定）
- **認証状態**: verified（確認済み）

これでメール送信が可能な状態です。上記の方法でテストメールを送信して、正常に動作するか確認してください。
