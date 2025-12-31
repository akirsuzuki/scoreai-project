# Stripe Webhook トラブルシューティングガイド

## 問題: プラン変更がDjango側に反映されない

### 確認事項

#### 1. Webhookエンドポイントの設定確認

Stripe DashboardでWebhookエンドポイントが正しく設定されているか確認：

1. [Stripe Dashboard](https://dashboard.stripe.com/)にログイン
2. 「Developers」→「Webhooks」を選択
3. エンドポイントが存在するか確認
4. エンドポイントURL: `https://your-app.herokuapp.com/stripe/webhook/` または `https://score-ai.net/stripe/webhook/`

#### 2. Webhookイベントの確認

Stripe Dashboardで以下のイベントが有効になっているか確認：

- `customer.subscription.created`
- `customer.subscription.updated` ← **重要: プラン変更時に発火**
- `customer.subscription.deleted`
- `invoice.payment_succeeded`
- `invoice.payment_failed`

#### 3. Webhookシークレットの確認

```bash
# Herokuの環境変数を確認
heroku config:get STRIPE_WEBHOOK_SECRET --app your-app-name

# Stripe DashboardのWebhookエンドポイントからシークレットを取得
# 「Signing secret」をコピーしてHerokuに設定
heroku config:set STRIPE_WEBHOOK_SECRET="whsec_..." --app your-app-name
```

#### 4. Herokuのログを確認

```bash
# Webhookの受信ログを確認
heroku logs --tail --app your-app-name | grep -i webhook

# エラーログを確認
heroku logs --tail -n 500 --app your-app-name | grep -i error
```

#### 5. Stripe DashboardでWebhookイベントを確認

1. Stripe Dashboard → 「Developers」→「Webhooks」
2. エンドポイントを選択
3. 「Events」タブで最近のイベントを確認
4. `customer.subscription.updated`イベントが存在するか確認
5. イベントをクリックして詳細を確認
6. 「Response」タブでエラーレスポンスがないか確認

---

## 手動でWebhookを再送信する方法

### Stripe Dashboardから再送信

1. Stripe Dashboard → 「Developers」→「Webhooks」
2. エンドポイントを選択
3. 「Events」タブで該当のイベントを選択
4. 「Resend」ボタンをクリック

### Stripe CLIでローカルテスト（開発環境）

```bash
# Stripe CLIをインストール（未インストールの場合）
# https://stripe.com/docs/stripe-cli

# Webhookをローカルに転送
stripe listen --forward-to http://localhost:8000/stripe/webhook/

# 別のターミナルでイベントをトリガー
stripe trigger customer.subscription.updated
```

---

## 実装の修正内容

### 問題点

`_handle_subscription_updated`関数で、プラン変更時に`plan`フィールドを更新していませんでした。

### 修正内容

1. **プラン変更の検出**: `price_id`が変更された場合に新しいプランを特定
2. **プランの更新**: 新しいプランに更新
3. **ログの改善**: プラン変更をログに記録

### 修正後の動作

- Stripeでプラン変更が発生
- `customer.subscription.updated`イベントが発火
- Webhookが`_handle_subscription_updated`を呼び出し
- 新しい`price_id`からプランを特定
- `FirmSubscription.plan`を更新
- ログに記録

---

## デバッグ手順

### Step 1: Webhookが届いているか確認

```bash
heroku logs --tail --app your-app-name | grep -i "subscription.updated"
```

### Step 2: エラーがないか確認

```bash
heroku logs --tail -n 500 --app your-app-name | grep -i "error\|exception\|traceback"
```

### Step 3: Djangoシェルでサブスクリプションを確認

```bash
heroku run python manage.py shell --app your-app-name
```

シェル内で実行：
```python
from scoreai.models import FirmSubscription, Firm

# すべてのサブスクリプションを確認
for sub in FirmSubscription.objects.all():
    print(f"Firm: {sub.firm.name}")
    print(f"  Plan: {sub.plan.name} (ID: {sub.plan.id})")
    print(f"  Status: {sub.status}")
    print(f"  Stripe Subscription ID: {sub.stripe_subscription_id}")
    print(f"  Stripe Price ID: {sub.stripe_price_id}")
    print()
```

### Step 4: Stripe側のデータと比較

```python
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

# Stripeのサブスクリプションを取得
subscriptions = stripe.Subscription.list(limit=10)

for sub in subscriptions:
    print(f"Stripe Subscription ID: {sub.id}")
    print(f"  Customer: {sub.customer}")
    print(f"  Status: {sub.status}")
    if sub.items.data:
        price_id = sub.items.data[0].price.id
        print(f"  Price ID: {price_id}")
    print()
```

---

## よくある問題と解決策

### 問題1: Webhookが届いていない

**原因**:
- Webhookエンドポイントが設定されていない
- URLが間違っている
- 本番環境のURLが設定されていない

**解決策**:
1. Stripe DashboardでWebhookエンドポイントを確認
2. 正しいURLを設定: `https://score-ai.net/stripe/webhook/`
3. 必要なイベントを有効化

### 問題2: Webhookシークレットが間違っている

**原因**:
- 環境変数`STRIPE_WEBHOOK_SECRET`が設定されていない
- 古いシークレットが設定されている

**解決策**:
```bash
# Stripe Dashboardから最新のシークレットを取得
# 「Developers」→「Webhooks」→ エンドポイント → 「Signing secret」

# Herokuに設定
heroku config:set STRIPE_WEBHOOK_SECRET="whsec_..." --app your-app-name
heroku restart --app your-app-name
```

### 問題3: プランが見つからない

**原因**:
- `FirmPlan`に`stripe_price_id_monthly`または`stripe_price_id_yearly`が設定されていない
- Price IDが間違っている

**解決策**:
1. Django Adminで`FirmPlan`を確認
2. Stripe DashboardでPrice IDを確認
3. `FirmPlan`に正しいPrice IDを設定

### 問題4: サブスクリプションが見つからない

**原因**:
- `FirmSubscription.stripe_subscription_id`が設定されていない
- Stripe側のSubscription IDと一致していない

**解決策**:
1. Stripe DashboardでSubscription IDを確認
2. Django Adminで`FirmSubscription`を確認
3. 手動で`stripe_subscription_id`を設定（必要に応じて）

---

## 手動でプランを更新する方法（緊急時）

Webhookが動作しない場合の一時的な対処法：

```bash
heroku run python manage.py shell --app your-app-name
```

シェル内で実行：
```python
from scoreai.models import FirmSubscription, FirmPlan
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

# Firmを指定
firm_id = "your-firm-id"  # 実際のFirm IDに置き換え
firm = Firm.objects.get(id=firm_id)

# Stripeのサブスクリプションを取得
subscription = firm.subscription
if subscription.stripe_subscription_id:
    stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
    
    # Price IDを取得
    price_id = stripe_sub.items.data[0].price.id
    
    # プランを特定
    new_plan = FirmPlan.objects.filter(
        stripe_price_id_monthly=price_id
    ).first() or FirmPlan.objects.filter(
        stripe_price_id_yearly=price_id
    ).first()
    
    if new_plan:
        subscription.plan = new_plan
        subscription.stripe_price_id = price_id
        subscription.status = stripe_sub.status
        subscription.save()
        print(f"プランを更新しました: {new_plan.name}")
    else:
        print(f"プランが見つかりません。Price ID: {price_id}")
else:
    print("Stripe Subscription IDが設定されていません。")
```

---

## 参考リンク

- [Stripe Webhooks](https://stripe.com/docs/webhooks)
- [Stripe Webhook Events](https://stripe.com/docs/api/events/types)
- [Stripe CLI](https://stripe.com/docs/stripe-cli)


