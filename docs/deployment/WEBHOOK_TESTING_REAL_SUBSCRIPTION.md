# 実際のサブスクリプションでWebhookをテストする方法

## 問題

`stripe trigger`はテスト用のフィクスチャデータを使用するため、実際のサブスクリプションIDと一致しない可能性があります。

## 解決策

### 方法1: Stripe Dashboardで実際にプランを変更（推奨）

1. [Stripe Dashboard（テストモード）](https://dashboard.stripe.com/test/subscriptions)
2. 実際のサブスクリプションを選択
3. 「Actions」→「Update subscription」をクリック
4. プランを変更
5. ログを確認: `tail -f logs/django.log | grep -i webhook`

### 方法2: Stripe CLIで実際のサブスクリプションIDを指定

```bash
# 実際のサブスクリプションIDを取得
python manage.py shell
```

シェル内で実行：
```python
from scoreai.models import FirmSubscription
subscription = FirmSubscription.objects.first()
print(f"Stripe Subscription ID: {subscription.stripe_subscription_id}")
```

その後、Stripe CLIで実際のサブスクリプションを更新：

```bash
# 実際のサブスクリプションを更新
stripe subscriptions update sub_XXXXX --items[0][price]=price_YYYYY

# または、Stripe Dashboardでプランを変更
```

### 方法3: Stripe DashboardからWebhookイベントを再送信

1. [Stripe Dashboard（テストモード）](https://dashboard.stripe.com/test/webhooks)
2. エンドポイントを選択
3. 「Events」タブで`customer.subscription.updated`イベントを選択
4. 「Resend」ボタンをクリック
5. ログを確認

---

## 確認手順

### Step 1: 実際のサブスクリプションIDを確認

```bash
python manage.py shell
```

```python
from scoreai.models import FirmSubscription, Firm
from scoreai.models import UserFirm
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()  # テストユーザー

# UserFirmからFirmを取得
user_firm = UserFirm.objects.filter(user=user, is_selected=True).first()
if user_firm:
    firm = user_firm.firm
    try:
        subscription = firm.subscription
        print(f"Firm: {firm.name}")
        print(f"Stripe Subscription ID: {subscription.stripe_subscription_id}")
        print(f"Current Plan: {subscription.plan.name}")
        print(f"Stripe Price ID: {subscription.stripe_price_id}")
    except FirmSubscription.DoesNotExist:
        print("サブスクリプションが見つかりません。")
else:
    print("Firmが見つかりません。")
```

### Step 2: Stripe Dashboardでプランを変更

1. [Stripe Dashboard（テストモード）](https://dashboard.stripe.com/test/subscriptions)
2. 上記で取得したSubscription IDを検索
3. サブスクリプションを選択
4. 「Actions」→「Update subscription」をクリック
5. プランを変更（例: Free → Starter）
6. 「Update subscription」をクリック

### Step 3: ログを確認

```bash
tail -f logs/django.log | grep -i "webhook\|subscription\|stripe"
```

以下のログが表示されるはずです：
```
INFO ... === Webhook endpoint called ===
INFO ... Webhook event received: customer.subscription.updated
INFO ... Processing subscription.updated event
INFO ... Handling subscription.updated for: sub_...
INFO ... Found subscription: ... (Plan: ...)
INFO ... Plan changed for subscription ...: ... -> ...
```

---

## トラブルシューティング

### Webhookが届かない場合

1. **Stripe DashboardでWebhookイベントを確認**
   - イベントが記録されているか
   - レスポンスコードが200か

2. **WebhookエンドポイントのURLを確認**
   - ローカル: `http://localhost:8000/stripe/webhook/`
   - テスト環境: `https://your-test-app.herokuapp.com/stripe/webhook/`

3. **Webhookシークレットを確認**
   ```bash
   echo $STRIPE_WEBHOOK_SECRET
   ```

### プランが見つからない場合

ログに`Plan not found for price_id: ...`が表示される場合：

```python
# Djangoシェルで確認
from scoreai.models import FirmPlan

for plan in FirmPlan.objects.all():
    print(f"{plan.name}:")
    print(f"  月額Price ID: {plan.stripe_price_id_monthly}")
    print(f"  年額Price ID: {plan.stripe_price_id_yearly}")
```

Stripe Dashboardで設定されているPrice IDと一致しているか確認してください。

---

## 手動でプランを更新する方法（緊急時）

Webhookが動作しない場合の一時的な対処：

```bash
python manage.py shell
```

```python
from scoreai.models import FirmSubscription, FirmPlan, Firm
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

# Firmを指定（実際のFirm IDに置き換え）
firm_id = "your-firm-id"
firm = Firm.objects.get(id=firm_id)

# Stripeのサブスクリプションを取得
try:
    subscription = firm.subscription
    if subscription.stripe_subscription_id:
        stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
        
        # Price IDを取得
        price_id = stripe_sub.items.data[0].price.id
        print(f"Stripe Price ID: {price_id}")
        
        # プランを特定
        new_plan = FirmPlan.objects.filter(
            stripe_price_id_monthly=price_id
        ).first() or FirmPlan.objects.filter(
            stripe_price_id_yearly=price_id
        ).first()
        
        if new_plan:
            old_plan = subscription.plan
            subscription.plan = new_plan
            subscription.stripe_price_id = price_id
            subscription.status = stripe_sub.status
            subscription.save()
            print(f"✅ プランを更新しました: {old_plan.name} -> {new_plan.name}")
        else:
            print(f"❌ プランが見つかりません。Price ID: {price_id}")
            print("\n利用可能なプラン:")
            for plan in FirmPlan.objects.all():
                print(f"  {plan.name}:")
                print(f"    月額Price ID: {plan.stripe_price_id_monthly}")
                print(f"    年額Price ID: {plan.stripe_price_id_yearly}")
except FirmSubscription.DoesNotExist:
    print("❌ サブスクリプションが見つかりません。")
```


