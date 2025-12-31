# FirmPlanデータの本番環境へのインポート手順

## 概要

ローカル環境の`FirmPlan`モデルの全レコードを本番環境（Heroku）にインポートする手順です。

## 手順

### Step 1: ローカル環境でデータをエクスポート

```bash
# プロジェクトディレクトリに移動
cd /Users/akirasuzuki/Desktop/work/score/scoreai-project

# FirmPlanのデータをJSONファイルにエクスポート
python manage.py dumpdata scoreai.FirmPlan --indent 2 --output firmplan_data.json

# エクスポートされたデータを確認
cat firmplan_data.json
```

### Step 2: 本番環境の既存データを確認（オプション）

本番環境に既に`FirmPlan`のデータが存在する場合は、競合を避けるために確認してください：

```bash
heroku run python manage.py shell --app your-app-name
```

シェル内で実行：
```python
from scoreai.models import FirmPlan
print(f"既存のFirmPlan数: {FirmPlan.objects.count()}")
for plan in FirmPlan.objects.all():
    print(f"  - {plan.plan_type}: {plan.name}")
```

### Step 3: JSONファイルを本番環境にアップロード

#### 方法A: Git経由でアップロード（推奨）

```bash
# JSONファイルをGitに追加（一時的に）
git add firmplan_data.json

# コミット
git commit -m "FirmPlanデータをエクスポート"

# 本番環境にプッシュ
git push heroku main

# インポート後、JSONファイルを削除（必要に応じて）
# git rm firmplan_data.json
# git commit -m "FirmPlanデータファイルを削除"
# git push heroku main
```

#### 方法B: 直接アップロード（一時ファイルとして）

```bash
# JSONファイルの内容をコピーして、本番環境に一時ファイルとして作成
heroku run bash --app your-app-name
# シェル内で：
# cat > /tmp/firmplan_data.json << 'EOF'
# [JSONファイルの内容を貼り付け]
# EOF
```

### Step 4: 本番環境でデータをインポート

#### 方法A: Git経由でアップロードした場合

```bash
# 本番環境でloaddataを実行
heroku run python manage.py loaddata firmplan_data.json --app your-app-name
```

#### 方法B: 直接アップロードした場合

```bash
# 本番環境でloaddataを実行
heroku run python manage.py loaddata /tmp/firmplan_data.json --app your-app-name
```

### Step 5: インポート結果を確認

```bash
heroku run python manage.py shell --app your-app-name
```

シェル内で実行：
```python
from scoreai.models import FirmPlan
print(f"FirmPlan数: {FirmPlan.objects.count()}")
for plan in FirmPlan.objects.all():
    print(f"  - {plan.plan_type}: {plan.name} (ID: {plan.id})")
    print(f"    月額: ¥{plan.monthly_price}, 年額: ¥{plan.yearly_price}")
    print(f"    Stripe月額ID: {plan.stripe_price_id_monthly}")
    print(f"    Stripe年額ID: {plan.stripe_price_id_yearly}")
```

---

## 注意事項

### 1. 既存データとの競合

本番環境に既に`FirmPlan`のデータが存在する場合、以下のいずれかの方法を選択してください：

#### オプション1: 既存データを削除してからインポート

```bash
heroku run python manage.py shell --app your-app-name
```

シェル内で実行：
```python
from scoreai.models import FirmPlan
# 既存データを削除（注意：関連するFirmSubscriptionも確認が必要）
FirmPlan.objects.all().delete()
print("既存のFirmPlanデータを削除しました")
```

その後、Step 4を実行してインポートします。

#### オプション2: 既存データを保持してインポート

`loaddata`は既存のデータとIDが重複する場合は更新します。重複しない場合は新規作成します。

### 2. 関連データの確認

`FirmPlan`は`FirmSubscription`から参照されているため、既存のサブスクリプションがある場合は注意が必要です：

```bash
heroku run python manage.py shell --app your-app-name
```

シェル内で実行：
```python
from scoreai.models import FirmPlan, FirmSubscription

# 各プランが使用されているか確認
for plan in FirmPlan.objects.all():
    subscriptions = FirmSubscription.objects.filter(plan=plan)
    print(f"{plan.name}: {subscriptions.count()}件のサブスクリプション")
```

### 3. Stripe Price IDの確認

本番環境のStripe Price IDが正しく設定されているか確認してください：

```bash
heroku run python manage.py shell --app your-app-name
```

シェル内で実行：
```python
from scoreai.models import FirmPlan
for plan in FirmPlan.objects.all():
    print(f"{plan.name}:")
    print(f"  月額Price ID: {plan.stripe_price_id_monthly}")
    print(f"  年額Price ID: {plan.stripe_price_id_yearly}")
```

本番環境用のStripe Price IDが設定されていることを確認してください。

---

## トラブルシューティング

### エラー: "No such file or directory"

JSONファイルが見つからない場合：

```bash
# ファイルの場所を確認
heroku run ls -la --app your-app-name

# または、Git経由でアップロードした場合
heroku run ls -la firmplan_data.json --app your-app-name
```

### エラー: "IntegrityError: UNIQUE constraint failed"

既存のデータとIDが重複している場合：

1. 既存データを削除してからインポート
2. または、JSONファイルを編集してIDを変更（非推奨）

### エラー: "RelatedObjectDoesNotExist"

関連するモデル（例：`Firm`）が存在しない場合：

- まず、関連するモデルのデータをインポートしてください
- または、JSONファイルを編集して関連データを除外してください

---

## 完全な手順（一括実行）

```bash
# 1. ローカル環境でエクスポート
cd /Users/akirasuzuki/Desktop/work/score/scoreai-project
python manage.py dumpdata scoreai.FirmPlan --indent 2 --output firmplan_data.json

# 2. Gitに追加（一時的に）
git add firmplan_data.json
git commit -m "FirmPlanデータをエクスポート"

# 3. 本番環境にプッシュ
git push heroku main

# 4. 本番環境でインポート
heroku run python manage.py loaddata firmplan_data.json --app your-app-name

# 5. 確認
heroku run python manage.py shell --app your-app-name
# シェル内で：
# from scoreai.models import FirmPlan
# print(FirmPlan.objects.count())
```

---

## 参考

- [Django dumpdata](https://docs.djangoproject.com/en/stable/ref/django-admin/#dumpdata)
- [Django loaddata](https://docs.djangoproject.com/en/stable/ref/django-admin/#loaddata)


