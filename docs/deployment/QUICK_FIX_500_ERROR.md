# 500エラーの迅速な修正手順

## 現在の状況

`/ai-consultation/`で500エラーが発生しています。ログに詳細なエラーメッセージが表示されていないため、以下を順番に確認してください。

## 即座に実行すべき確認コマンド

### 1. データベースの状態を確認

```bash
heroku run python manage.py shell --app your-app-name
```

シェル内で実行：
```python
# AIConsultationTypeの確認
from scoreai.models import AIConsultationType
print(f"AIConsultationType count: {AIConsultationType.objects.count()}")
print(f"Active types: {AIConsultationType.objects.filter(is_active=True).count()}")

# ユーザーの選択状態を確認
from scoreai.models import UserCompany, UserFirm
from django.contrib.auth import get_user_model

User = get_user_model()
for user in User.objects.all():
    user_company = UserCompany.objects.filter(user=user, is_selected=True).first()
    user_firm = UserFirm.objects.filter(user=user, is_selected=True).first()
    print(f"\nUser: {user.email}")
    print(f"  Selected Company: {user_company}")
    print(f"  Selected Firm: {user_firm}")
```

### 2. マイグレーションを確認・実行

```bash
# 未適用のマイグレーションを確認
heroku run python manage.py showmigrations --app your-app-name

# マイグレーションを実行
heroku run python manage.py migrate --app your-app-name
```

### 3. 初期データを投入

```bash
# AIConsultationTypeの初期データを投入
heroku run python manage.py init_ai_consultation_data --app your-app-name
```

### 4. ログ設定を更新（エラーログを表示）

ログ設定を更新して、エラーの詳細を標準出力に表示するようにしました。変更をデプロイしてください：

```bash
git add score/settings.py
git commit -m "ログ設定を更新してHerokuでエラーログを表示"
git push heroku main
```

### 5. アプリを再起動

```bash
heroku restart --app your-app-name
```

### 6. 再度ログを確認

```bash
heroku logs --tail --app your-app-name
```

今度は詳細なエラーメッセージが表示されるはずです。

---

## 最も可能性の高い原因と解決策

### 原因1: ユーザーが会社を選択していない

**症状**: `選択された会社がありません。`というエラー

**解決策**:
1. 管理者が`UserCompany`と`UserFirm`を設定する
2. または、ユーザーがログイン後に会社を選択する

**確認方法**:
```bash
heroku run python manage.py shell --app your-app-name
```

```python
from scoreai.models import UserCompany, UserFirm, User, Company, Firm
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()  # テストユーザー

# 会社とFirmが存在するか確認
companies = Company.objects.all()
firms = Firm.objects.all()

print(f"Companies: {companies.count()}")
print(f"Firms: {firms.count()}")

# ユーザーに会社とFirmを設定（存在する場合）
if companies.exists() and firms.exists():
    company = companies.first()
    firm = firms.first()
    
    # UserCompanyを作成/更新
    user_company, created = UserCompany.objects.get_or_create(
        user=user,
        company=company,
        defaults={'is_selected': True}
    )
    if not created:
        user_company.is_selected = True
        user_company.save()
    
    # 他のUserCompanyを非選択にする
    UserCompany.objects.filter(user=user).exclude(id=user_company.id).update(is_selected=False)
    
    # UserFirmを作成/更新
    user_firm, created = UserFirm.objects.get_or_create(
        user=user,
        firm=firm,
        defaults={'is_selected': True}
    )
    if not created:
        user_firm.is_selected = True
        user_firm.save()
    
    # 他のUserFirmを非選択にする
    UserFirm.objects.filter(user=user).exclude(id=user_firm.id).update(is_selected=False)
    
    print("設定完了")
```

### 原因2: AIConsultationTypeが存在しない

**解決策**:
```bash
heroku run python manage.py init_ai_consultation_data --app your-app-name
```

### 原因3: 環境変数が設定されていない

**確認**:
```bash
heroku config --app your-app-name
```

**解決策**:
```bash
heroku config:set SECRET_KEY="your-secret-key" --app your-app-name
heroku config:set GEMINI_API_KEY="your-gemini-api-key" --app your-app-name
heroku config:set DEBUG="False" --app your-app-name
heroku restart --app your-app-name
```

---

## デバッグモードを一時的に有効にする（最後の手段）

エラーの詳細を確認するため、一時的にDEBUGを有効にすることができます：

```bash
# DEBUGを一時的に有効にする
heroku config:set DEBUG="True" --app your-app-name
heroku restart --app your-app-name

# エラーを確認後、必ずFalseに戻す
heroku config:set DEBUG="False" --app your-app-name
heroku restart --app your-app-name
```

**注意**: DEBUG=Trueは本番環境ではセキュリティリスクがあるため、確認後は必ずFalseに戻してください。

---

## 次のステップ

1. ログ設定を更新してデプロイ
2. データベースの状態を確認
3. マイグレーションと初期データを投入
4. 再度ログを確認してエラーメッセージを特定
5. エラーメッセージに基づいて修正


