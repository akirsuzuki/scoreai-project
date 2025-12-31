# 500エラーの詳細デバッグ手順

## 現在の状況

ログから確認できること：
- `/ai-consultation/` にGETリクエスト
- 500エラーが発生
- レスポンスサイズが145バイト（エラーページ）

## 詳細なエラーログを確認

### 1. Djangoのエラートレースバックを確認

```bash
# より詳細なログを確認（エラーの詳細が表示される）
heroku logs --tail --app your-app-name | grep -A 50 "ERROR\|Traceback\|Exception"

# または、すべてのログを確認
heroku logs --tail -n 200 --app your-app-name
```

### 2. よくある原因の確認

#### 原因1: SelectedCompanyMixinのエラー

`AIConsultationCenterView`は`SelectedCompanyMixin`を使用しているため、ユーザーが会社を選択していない場合にエラーが発生します。

**確認方法**:
```bash
heroku run python manage.py shell --app your-app-name
```

シェル内で実行：
```python
from scoreai.models import User, UserCompany, UserFirm
from django.contrib.auth import get_user_model

User = get_user_model()
# テストユーザーを確認
users = User.objects.all()
for user in users:
    print(f"User: {user.email}")
    user_company = UserCompany.objects.filter(user=user, is_selected=True).first()
    user_firm = UserFirm.objects.filter(user=user, is_selected=True).first()
    print(f"  Selected Company: {user_company}")
    print(f"  Selected Firm: {user_firm}")
```

**解決策**:
- ユーザーがログインしていることを確認
- ユーザーに会社を選択させる
- 管理者が`UserCompany`と`UserFirm`を設定する

#### 原因2: AIConsultationTypeが存在しない

**確認方法**:
```bash
heroku run python manage.py shell --app your-app-name
```

シェル内で実行：
```python
from scoreai.models import AIConsultationType
print(f"AIConsultationType count: {AIConsultationType.objects.count()}")
print(f"Active types: {AIConsultationType.objects.filter(is_active=True).count()}")
```

**解決策**:
```bash
# 初期データを投入
heroku run python manage.py init_ai_consultation_data --app your-app-name
```

#### 原因3: 環境変数が設定されていない

**確認方法**:
```bash
heroku config --app your-app-name
```

特に以下を確認：
- `SECRET_KEY`
- `GEMINI_API_KEY`
- `DEBUG`

**解決策**:
```bash
heroku config:set SECRET_KEY="your-secret-key" --app your-app-name
heroku config:set GEMINI_API_KEY="your-gemini-api-key" --app your-app-name
heroku config:set DEBUG="False" --app your-app-name
heroku restart --app your-app-name
```

#### 原因4: マイグレーションが実行されていない

**確認方法**:
```bash
heroku run python manage.py showmigrations --app your-app-name
```

未適用のマイグレーションがないか確認。

**解決策**:
```bash
heroku run python manage.py migrate --app your-app-name
```

---

## デバッグ用の一時的な修正

エラーの詳細を確認するため、一時的にDEBUGを有効にすることができます（**セキュリティ上の注意が必要**）：

```bash
# DEBUGを一時的に有効にする
heroku config:set DEBUG="True" --app your-app-name
heroku restart --app your-app-name

# エラーを確認後、必ずFalseに戻す
heroku config:set DEBUG="False" --app your-app-name
heroku restart --app your-app-name
```

---

## 段階的な確認手順

### Step 1: 詳細なログを確認
```bash
heroku logs --tail -n 500 --app your-app-name
```

### Step 2: データベースの状態を確認
```bash
heroku run python manage.py shell --app your-app-name
```

```python
# すべてのモデルの状態を確認
from scoreai.models import (
    AIConsultationType,
    UserCompany,
    UserFirm,
    Company,
    Firm
)

print("=== AIConsultationType ===")
print(f"Total: {AIConsultationType.objects.count()}")
print(f"Active: {AIConsultationType.objects.filter(is_active=True).count()}")

print("\n=== UserCompany ===")
print(f"Total: {UserCompany.objects.count()}")
print(f"Selected: {UserCompany.objects.filter(is_selected=True).count()}")

print("\n=== UserFirm ===")
print(f"Total: {UserFirm.objects.count()}")
print(f"Selected: {UserFirm.objects.filter(is_selected=True).count()}")
```

### Step 3: 環境変数を確認
```bash
heroku config --app your-app-name
```

### Step 4: マイグレーションを確認
```bash
heroku run python manage.py showmigrations --app your-app-name
```

### Step 5: マイグレーションを実行（必要に応じて）
```bash
heroku run python manage.py migrate --app your-app-name
```

### Step 6: 初期データを投入（必要に応じて）
```bash
heroku run python manage.py init_ai_consultation_data --app your-app-name
```

---

## 最も可能性の高い原因

`/ai-consultation/`で500エラーが発生する場合、最も可能性が高いのは：

1. **ユーザーが会社を選択していない** - `SelectedCompanyMixin`が`this_company`を取得できない
2. **AIConsultationTypeが存在しない** - 初期データが投入されていない
3. **環境変数が設定されていない** - `GEMINI_API_KEY`など

まずは**詳細なログを確認**して、エラーメッセージを特定してください。


