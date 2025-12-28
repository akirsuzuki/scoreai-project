# Stripe価格IDの設定方法

## 前提条件

- Stripe Dashboardで各プランの価格（Price）を作成済み
- 各価格の価格ID（`price_...`で始まる）を取得済み

## 方法1: Django管理画面から設定（推奨）

### 手順

1. **ローカルサーバーを起動**（まだ起動していない場合）:
   ```bash
   docker compose up
   ```

2. **管理画面にアクセス**:
   - URL: `http://localhost:8000/admin/`
   - 管理者アカウントでログイン

3. **Firm Plansを開く**:
   - 左メニューから「Firm Plans」をクリック

4. **各プランを編集**:
   
   #### Starterプラン
   - 「Starterプラン」をクリック
   - `Stripe月額価格ID` フィールドに月額価格IDを入力（例: `price_xxxxx`）
   - `Stripe年額価格ID` フィールドに年額価格IDを入力（例: `price_yyyyy`）
   - 「保存」をクリック
   
   #### Professionalプラン
   - 「Professionalプラン」をクリック
   - 同様に月額・年額価格IDを入力
   - 「保存」をクリック
   
   #### Enterpriseプラン
   - 「Enterpriseプラン」をクリック
   - 同様に月額・年額価格IDを入力
   - 「保存」をクリック

## 方法2: Djangoシェルから設定

### 手順

1. **Djangoシェルを起動**:
   ```bash
   docker compose exec django python manage.py shell
   ```

2. **以下のPythonコードを実行**:

```python
from scoreai.models import FirmPlan

# Starterプラン
starter = FirmPlan.objects.get(plan_type='starter')
starter.stripe_price_id_monthly = 'price_xxxxx'  # 月額価格IDを入力
starter.stripe_price_id_yearly = 'price_yyyyy'  # 年額価格IDを入力
starter.save()
print(f"Starterプラン: 月額={starter.stripe_price_id_monthly}, 年額={starter.stripe_price_id_yearly}")

# Professionalプラン
professional = FirmPlan.objects.get(plan_type='professional')
professional.stripe_price_id_monthly = 'price_xxxxx'  # 月額価格IDを入力
professional.stripe_price_id_yearly = 'price_yyyyy'  # 年額価格IDを入力
professional.save()
print(f"Professionalプラン: 月額={professional.stripe_price_id_monthly}, 年額={professional.stripe_price_id_yearly}")

# Enterpriseプラン
enterprise = FirmPlan.objects.get(plan_type='enterprise')
enterprise.stripe_price_id_monthly = 'price_xxxxx'  # 月額価格IDを入力
enterprise.stripe_price_id_yearly = 'price_yyyyy'  # 年額価格IDを入力
enterprise.save()
print(f"Enterpriseプラン: 月額={enterprise.stripe_price_id_monthly}, 年額={enterprise.stripe_price_id_yearly}")

# 確認
print("\n=== 設定確認 ===")
for plan in FirmPlan.objects.filter(plan_type__in=['starter', 'professional', 'enterprise']):
    print(f"{plan.name}:")
    print(f"  月額: {plan.stripe_price_id_monthly or '未設定'}")
    print(f"  年額: {plan.stripe_price_id_yearly or '未設定'}")
```

3. **シェルを終了**:
   ```python
   exit()
   ```

## 方法3: 一括設定スクリプト

価格IDを一度に設定したい場合は、以下のスクリプトを使用できます。

### 手順

1. **価格IDを準備**:
   以下の形式で価格IDをメモしてください：
   ```
   Starter月額: price_xxxxx
   Starter年額: price_yyyyy
   Professional月額: price_aaaaa
   Professional年額: price_bbbbb
   Enterprise月額: price_ccccc
   Enterprise年額: price_ddddd
   ```

2. **Djangoシェルで実行**:
   ```bash
   docker compose exec django python manage.py shell
   ```

3. **以下のコードを実行**（価格IDを実際の値に置き換えてください）:

```python
from scoreai.models import FirmPlan

# 価格IDを辞書で定義
price_ids = {
    'starter': {
        'monthly': 'price_xxxxx',  # Starter月額価格ID
        'yearly': 'price_yyyyy',   # Starter年額価格ID
    },
    'professional': {
        'monthly': 'price_aaaaa',  # Professional月額価格ID
        'yearly': 'price_bbbbb',   # Professional年額価格ID
    },
    'enterprise': {
        'monthly': 'price_ccccc',   # Enterprise月額価格ID
        'yearly': 'price_ddddd',    # Enterprise年額価格ID
    },
}

# 一括設定
for plan_type, prices in price_ids.items():
    try:
        plan = FirmPlan.objects.get(plan_type=plan_type)
        plan.stripe_price_id_monthly = prices['monthly']
        plan.stripe_price_id_yearly = prices['yearly']
        plan.save()
        print(f"✓ {plan.name}: 設定完了")
        print(f"  月額: {prices['monthly']}")
        print(f"  年額: {prices['yearly']}")
    except FirmPlan.DoesNotExist:
        print(f"✗ {plan_type}: プランが見つかりません")

# 最終確認
print("\n=== 最終確認 ===")
for plan in FirmPlan.objects.filter(plan_type__in=['starter', 'professional', 'enterprise']):
    print(f"{plan.name}:")
    print(f"  月額: {plan.stripe_price_id_monthly or '未設定'}")
    print(f"  年額: {plan.stripe_price_id_yearly or '未設定'}")
```

## 設定確認

設定が正しく完了したか確認するには：

```bash
docker compose exec django python manage.py shell
```

```python
from scoreai.models import FirmPlan

for plan in FirmPlan.objects.filter(plan_type__in=['starter', 'professional', 'enterprise']):
    print(f"{plan.name}:")
    print(f"  月額価格ID: {plan.stripe_price_id_monthly or '未設定'}")
    print(f"  年額価格ID: {plan.stripe_price_id_yearly or '未設定'}")
    print()
```

## トラブルシューティング

### プランが見つからない

**エラー**: `FirmPlan matching query does not exist`

**対処法**:
1. プランが作成されているか確認:
   ```python
   from scoreai.models import FirmPlan
   FirmPlan.objects.all()
   ```
2. プランが存在しない場合は、管理コマンドで作成:
   ```bash
   docker compose exec django python manage.py init_firm_plans
   ```

### 価格IDが正しく設定されない

**対処法**:
1. 価格IDが`price_`で始まることを確認
2. Stripe Dashboardで価格が正しく作成されているか確認
3. テストモードの価格IDを使用していることを確認（本番モードの価格IDは使用しない）

## 次のステップ

価格IDの設定が完了したら：

1. **プラン一覧ページで確認**:
   - `http://localhost:8000/plans/<firm_id>/` にアクセス
   - 各プランの料金が正しく表示されることを確認

2. **テスト決済を実行**:
   - プラン詳細ページから「このプランに登録」をクリック
   - Stripe Checkout画面が表示されることを確認

