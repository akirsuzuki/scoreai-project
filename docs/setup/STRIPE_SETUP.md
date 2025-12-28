# Stripe設定ガイド

## 概要

SCORE AIでは、Stripeを使用してFirm向けプランの課金処理を行います。

## 必要な設定

### 1. Stripeアカウントの作成

1. [Stripe Dashboard](https://dashboard.stripe.com/)にアクセス
2. アカウントを作成（まだの場合）
3. テストモードと本番モードを切り替え可能

### 2. APIキーの取得

#### テストモード（開発環境用）

1. Stripe Dashboardで「テストモード」を選択
2. 「開発者」→「APIキー」に移動
3. 以下のキーをコピー：
   - **公開可能キー（Publishable key）**: `pk_test_...`
   - **シークレットキー（Secret key）**: `sk_test_...`

#### 本番モード（本番環境用）

1. Stripe Dashboardで「本番モード」を選択
2. 「開発者」→「APIキー」に移動
3. 以下のキーをコピー：
   - **公開可能キー（Publishable key）**: `pk_live_...`
   - **シークレットキー（Secret key）**: `sk_live_...`

### 3. ローカル環境での設定

`score/local_settings.py`に以下を追加：

```python
# Stripe設定（開発環境用）
STRIPE_PUBLIC_KEY = 'pk_test_...'  # テストモードの公開可能キー
STRIPE_SECRET_KEY = 'sk_test_...'  # テストモードのシークレットキー
STRIPE_WEBHOOK_SECRET = ''  # Webhook設定時に追加
```

### 4. 本番環境での設定

環境変数として設定：

```bash
STRIPE_PUBLIC_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### 5. 価格（Price）の作成

Stripe Dashboardで各プランの価格を作成する必要があります：

1. 「製品」→「価格」→「価格を追加」をクリック
2. 各プランごとに価格を作成：

#### Freeプラン
- 料金: 0円（無料）
- 価格ID: 不要（無料プランのため）

#### Starterプラン
- 月額: 9,800円
- 年額: 98,000円（2ヶ月分無料）
- 価格IDをコピーして`FirmPlan`モデルの`stripe_price_id_monthly`と`stripe_price_id_yearly`に設定

#### Professionalプラン
- 月額: 29,800円
- 年額: 298,000円（2ヶ月分無料）
- 価格IDをコピーして`FirmPlan`モデルの`stripe_price_id_monthly`と`stripe_price_id_yearly`に設定

#### Enterpriseプラン
- 月額: 79,800円（基本料金）
- 年額: 798,000円（2ヶ月分無料）
- 追加Company料金（10社ごと）:
  - 11-20社: 15,000円/月
  - 21-30社: 14,000円/月
  - 31-40社: 13,000円/月
  - 41-50社: 12,000円/月
  - 51社以上: 10,000円/月（10社ごと）
- 価格IDをコピーして`FirmPlan`モデルの`stripe_price_id_monthly`と`stripe_price_id_yearly`に設定

### 6. Webhookの設定

Stripe Webhookを使用して、支払い状況の変更をリアルタイムで受け取ります。

1. Stripe Dashboardで「開発者」→「Webhook」に移動
2. 「エンドポイントを追加」をクリック
3. エンドポイントURLを設定: `https://yourdomain.com/stripe/webhook/`
4. 以下のイベントを選択：
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
   - `customer.subscription.trial_will_end`
5. Webhookシークレットをコピーして`STRIPE_WEBHOOK_SECRET`に設定

## 実装時の注意事項

### セキュリティ

- **シークレットキーは絶対に公開しない**: GitHubにコミットしない、`.gitignore`に追加済み
- **Webhookシークレットの検証**: すべてのWebhookリクエストでシークレットを検証
- **HTTPS必須**: 本番環境ではHTTPSを使用

### テスト

- テストモードで十分にテストしてから本番モードに切り替え
- テストカード番号を使用して決済フローをテスト
  - 成功: `4242 4242 4242 4242`
  - 3Dセキュア: `4000 0025 0000 3155`
  - 失敗: `4000 0000 0000 9995`

## 参考リンク

- [Stripe公式ドキュメント](https://stripe.com/docs)
- [Stripe Python SDK](https://stripe.com/docs/api/python)
- [Stripe Webhook](https://stripe.com/docs/webhooks)

