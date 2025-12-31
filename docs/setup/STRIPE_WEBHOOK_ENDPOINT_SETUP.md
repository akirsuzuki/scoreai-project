# Stripe Webhookエンドポイント設定ガイド

## 概要

Stripeでは、**テストモード**と**本番モード**で別々のWebhookエンドポイントを設定する必要があります。

## 設定手順

### 1. テストモード（サンドボックス）のWebhook設定

1. [Stripe Dashboard（テストモード）](https://dashboard.stripe.com/test/webhooks)
   - ページの背景が**グレー**になっていることを確認（テストモードの表示）
   - 右上に「Test mode」と表示されていることを確認

2. 「Developers」→「Webhooks」を選択

3. 既存のエンドポイントを確認
   - テスト環境のURLが設定されているか確認
   - 例: `http://localhost:8000/stripe/webhook/`（ローカル開発）
   - 例: `https://your-test-app.herokuapp.com/stripe/webhook/`（テスト環境）

4. エンドポイントが存在しない、または間違っている場合：
   - 「Add endpoint」をクリック
   - 「Endpoint URL」にテスト環境のURLを入力
   - 例: `https://your-test-app.herokuapp.com/stripe/webhook/`

5. イベントを選択
   - 「Select events」をクリック
   - 以下のイベントを選択：
     - `customer.subscription.created`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.payment_succeeded`
     - `invoice.payment_failed`

6. 「Add endpoint」をクリック

7. **Webhook signing secret**をコピー
   - エンドポイントをクリック
   - 「Signing secret」セクションの「Reveal」をクリック
   - シークレットをコピー（例: `whsec_...`）

8. テスト環境の環境変数に設定
   ```bash
   # ローカル環境（local_settings.py）
   STRIPE_WEBHOOK_SECRET = 'whsec_...'  # テストモードのシークレット
   
   # Herokuテスト環境
   heroku config:set STRIPE_WEBHOOK_SECRET=whsec_... --app your-test-app
   ```

---

### 2. 本番モードのWebhook設定

1. [Stripe Dashboard（本番モード）](https://dashboard.stripe.com/webhooks)
   - ページの背景が**白**になっていることを確認（本番モードの表示）
   - 右上に「Test mode」が表示されていないことを確認

2. 「Developers」→「Webhooks」を選択

3. 「Add endpoint」をクリック

4. 「Endpoint URL」に本番環境のURLを入力
   - 例: `https://score-ai.net/stripe/webhook/`
   - **重要**: テスト環境のURLとは異なるURLを設定

5. イベントを選択
   - 「Select events」をクリック
   - 以下のイベントを選択：
     - `customer.subscription.created`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.payment_succeeded`
     - `invoice.payment_failed`

6. 「Add endpoint」をクリック

7. **Webhook signing secret**をコピー
   - エンドポイントをクリック
   - 「Signing secret」セクションの「Reveal」をクリック
   - シークレットをコピー（例: `whsec_...`）
   - **重要**: テストモードのシークレットとは異なります

8. 本番環境の環境変数に設定
   ```bash
   # Heroku本番環境
   heroku config:set STRIPE_WEBHOOK_SECRET=whsec_... --app score-ai
   ```

---

## 確認事項

### テストモードと本番モードの切り替え

Stripe Dashboardの右上で「Test mode」のトグルを切り替えることで、テストモードと本番モードを切り替えられます。

- **テストモード**: 背景がグレー、右上に「Test mode」表示
- **本番モード**: 背景が白、「Test mode」表示なし

### Webhookエンドポイントの確認

#### テストモード
- URL: `https://your-test-app.herokuapp.com/stripe/webhook/`
- Signing secret: テストモード用の`whsec_...`

#### 本番モード
- URL: `https://score-ai.net/stripe/webhook/`
- Signing secret: 本番モード用の`whsec_...`

### 環境変数の確認

```bash
# テスト環境
heroku config --app your-test-app | grep STRIPE

# 本番環境
heroku config --app score-ai | grep STRIPE
```

以下の環境変数が設定されていることを確認：
- `STRIPE_PUBLISHABLE_KEY`（テスト/本番で異なる）
- `STRIPE_SECRET_KEY`（テスト/本番で異なる）
- `STRIPE_WEBHOOK_SECRET`（テスト/本番で異なる）

---

## トラブルシューティング

### 問題1: Webhookが届かない

**原因**: WebhookエンドポイントのURLが間違っている

**解決策**:
1. Stripe DashboardでエンドポイントのURLを確認
2. 実際のアプリケーションのURLと一致しているか確認
3. 必要に応じてエンドポイントを削除して再作成

### 問題2: Webhook signature verification failed

**原因**: `STRIPE_WEBHOOK_SECRET`が間違っている、またはテスト/本番で混同している

**解決策**:
1. Stripe Dashboardで正しいSigning secretを確認
2. 環境変数を更新
3. アプリケーションを再起動

### 問題3: テストモードと本番モードで同じWebhookが使われている

**原因**: Webhookエンドポイントが1つしか設定されていない

**解決策**:
1. テストモードと本番モードで**別々のエンドポイント**を設定
2. それぞれ異なるURLとSigning secretを使用

---

## 設定チェックリスト

### テストモード（サンドボックス）
- [ ] Stripe Dashboard（テストモード）でWebhookエンドポイントが設定されている
- [ ] エンドポイントURLがテスト環境のURLを指している
- [ ] 必要なイベントが選択されている
- [ ] Webhook signing secretがコピーされている
- [ ] テスト環境の環境変数に`STRIPE_WEBHOOK_SECRET`が設定されている

### 本番モード
- [ ] Stripe Dashboard（本番モード）でWebhookエンドポイントが設定されている
- [ ] エンドポイントURLが本番環境のURLを指している
- [ ] 必要なイベントが選択されている
- [ ] Webhook signing secretがコピーされている
- [ ] 本番環境の環境変数に`STRIPE_WEBHOOK_SECRET`が設定されている

---

## 参考リンク

- [Stripe Webhooks Documentation](https://stripe.com/docs/webhooks)
- [Stripe Webhook Testing](https://stripe.com/docs/webhooks/test)
- [Stripe CLI](https://stripe.com/docs/stripe-cli)


