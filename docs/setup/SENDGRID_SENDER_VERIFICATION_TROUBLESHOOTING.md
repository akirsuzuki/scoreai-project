# SendGrid送信元メールアドレス認証メールが届かない場合の対処法

## 確認手順

### 1. スパムフォルダを確認

認証メールはスパムフォルダに入っている可能性があります。

- Gmail: 「迷惑メール」フォルダを確認
- Outlook: 「迷惑メール」フォルダを確認
- その他のメールクライアント: スパム/迷惑メールフォルダを確認

### 2. SendGridダッシュボードで送信状態を確認

1. SendGridダッシュボードにログイン
   - https://app.sendgrid.com/
2. 「Activity」をクリック
   - https://app.sendgrid.com/activity
3. メール送信履歴を確認
   - 認証メールが送信されているか確認
   - エラーメッセージがあるか確認

### 3. 送信元メールアドレスを再確認

1. 「Settings」→「Sender Authentication」→「Single Sender Verification」を選択
2. 作成した送信元メールアドレスを確認
   - メールアドレスが正しく入力されているか
   - ステータスが「Unverified」になっているか

### 4. 認証メールを再送信

SendGridダッシュボードから認証メールを再送信できます：

1. 「Settings」→「Sender Authentication」→「Single Sender Verification」を選択
2. 未認証の送信元メールアドレスをクリック
3. 「Resend Verification Email」ボタンをクリック
4. メールボックスを確認（スパムフォルダも含む）

### 5. メールアドレスのドメインを確認

一部のメールアドレス（特に無料メールサービス）では、認証メールが届かない場合があります。

**推奨されるメールアドレス:**
- 独自ドメインのメールアドレス（例: `noreply@score-ai.net`）
- 企業用メールアドレス

**問題が発生しやすいメールアドレス:**
- 無料メールサービスのアドレス（Gmail、Yahoo、Outlookなど）
- 一時的なメールアドレス

### 6. 代替手段: Domain Authentication（推奨）

Single Sender Verificationで問題が発生する場合、Domain Authenticationを使用することを推奨します。

**Domain Authenticationの利点:**
- ドメイン全体が認証されるため、複数のメールアドレスを使用可能
- より信頼性が高い
- 認証メールが不要（DNSレコードで認証）

**Domain Authenticationの設定手順:**

1. SendGridダッシュボードにログイン
   - https://app.sendgrid.com/
2. 「Settings」→「Sender Authentication」→「Authenticate Your Domain」を選択
3. 「Authenticate Domain」をクリック
4. ドメイン名を入力（例: `score-ai.net`）
5. DNSプロバイダーを選択
6. SendGridが提供するCNAMEレコードをDNSに追加
   - 通常、3つのCNAMEレコードが提供されます
   - DNS設定に追加するまで数時間〜24時間かかる場合があります
7. 「Verify」をクリックして認証を完了

**DNSレコードの追加例:**

```
Type: CNAME
Name: em1234.score-ai.net
Value: u1234567.wl123.sendgrid.net

Type: CNAME
Name: s1._domainkey.score-ai.net
Value: s1.domainkey.u1234567.wl123.sendgrid.net

Type: CNAME
Name: s2._domainkey.score-ai.net
Value: s2.domainkey.u1234567.wl123.sendgrid.net
```

### 7. SendGridサポートに問い合わせ

上記の方法で解決しない場合、SendGridサポートに問い合わせることができます。

1. SendGridダッシュボードの「Support」をクリック
2. 「Contact Support」を選択
3. 問題の詳細を説明

## 現在の設定確認

現在の送信元メールアドレス設定を確認するには：

```bash
# Dockerコンテナ内で実行
docker exec -it django python3 check_sendgrid_config.py
```

または、`score/local_settings.py`を確認：

```python
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@score-ai.net')
```

## 推奨される対応

1. **まず試すこと:**
   - スパムフォルダを確認
   - SendGridダッシュボードから認証メールを再送信
   - SendGridの「Activity」で送信状態を確認

2. **それでも解決しない場合:**
   - Domain Authenticationの設定を検討（推奨）
   - 別のメールアドレスで試す
   - SendGridサポートに問い合わせ

3. **本番環境の場合:**
   - Domain Authenticationを使用することを強く推奨
   - Single Sender Verificationは開発・テスト環境向け

## 参考リンク

- SendGrid Sender Authentication: https://sendgrid.com/docs/for-developers/sending-email/sender-identity/
- Domain Authentication設定: https://sendgrid.com/docs/for-developers/sending-email/sender-identity/#domain-authentication
- Single Sender Verification: https://sendgrid.com/docs/for-developers/sending-email/sender-identity/#single-sender-verification
