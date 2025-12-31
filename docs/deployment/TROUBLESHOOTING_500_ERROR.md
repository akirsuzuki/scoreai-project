# Heroku本番環境での500エラー トラブルシューティングガイド

## エラーログの確認方法

### 1. Heroku CLIでログを確認（推奨）

```bash
# リアルタイムでログを確認
heroku logs --tail --app your-app-name

# 最新100行のログを確認
heroku logs -n 100 --app your-app-name

# エラーのみを確認
heroku logs --tail --app your-app-name | grep -i error
```

### 2. Heroku Dashboardでログを確認

1. [Heroku Dashboard](https://dashboard.heroku.com/)にログイン
2. アプリを選択
3. 「More」→「View logs」をクリック

---

## よくある原因と解決策

### 1. 環境変数が設定されていない

**症状**: `GEMINI_API_KEY`や`SECRET_KEY`などの環境変数が設定されていない

**確認方法**:
```bash
heroku config --app your-app-name
```

**解決策**:
```bash
# 必要な環境変数を設定
heroku config:set SECRET_KEY="your-secret-key" --app your-app-name
heroku config:set GEMINI_API_KEY="your-gemini-api-key" --app your-app-name
heroku config:set DEBUG="False" --app your-app-name

# 設定後、アプリを再起動
heroku restart --app your-app-name
```

### 2. データベースマイグレーションが実行されていない

**症状**: `AIConsultationType`などのモデルがデータベースに存在しない

**確認方法**:
```bash
# Djangoシェルで確認
heroku run python manage.py shell --app your-app-name
>>> from scoreai.models import AIConsultationType
>>> AIConsultationType.objects.count()
```

**解決策**:
```bash
# マイグレーションを実行
heroku run python manage.py migrate --app your-app-name

# 初期データを投入（必要な場合）
heroku run python manage.py init_ai_consultation_data --app your-app-name
```

### 3. SelectedCompanyMixinのエラー

**症状**: `選択された会社がありません。`や`選択されたFirmがありません。`などのエラー

**原因**: ユーザーが会社を選択していない、または`UserCompany`や`UserFirm`が設定されていない

**解決策**:
- ユーザーがログインしていることを確認
- ユーザーに会社を選択させる
- 管理者が`UserCompany`と`UserFirm`を設定する

### 4. 静的ファイルが収集されていない

**症状**: CSSやJavaScriptファイルが読み込まれない

**解決策**:
```bash
# 静的ファイルを収集
heroku run python manage.py collectstatic --noinput --app your-app-name
```

### 5. 依存関係の問題

**症状**: `ModuleNotFoundError`や`ImportError`

**確認方法**:
```bash
# requirements.txtが最新か確認
git diff requirements.txt

# 依存関係を再インストール
heroku run pip install -r requirements.txt --app your-app-name
```

### 6. GEMINI_API_KEYのエラー

**症状**: `GEMINI_API_KEYが設定されていません。`や`404 models/... is not found`

**解決策**:
```bash
# 環境変数を確認
heroku config:get GEMINI_API_KEY --app your-app-name

# 正しいAPIキーを設定
heroku config:set GEMINI_API_KEY="AIzaSy..." --app your-app-name
heroku restart --app your-app-name
```

---

## デバッグモードを一時的に有効にする

本番環境でデバッグ情報を確認する場合（**セキュリティ上の注意が必要**）:

```bash
# DEBUGを一時的にTrueに設定
heroku config:set DEBUG="True" --app your-app-name
heroku restart --app your-app-name

# デバッグ後、必ずFalseに戻す
heroku config:set DEBUG="False" --app your-app-name
heroku restart --app your-app-name
```

---

## 段階的なデバッグ手順

### Step 1: ログを確認
```bash
heroku logs --tail --app your-app-name
```

### Step 2: 環境変数を確認
```bash
heroku config --app your-app-name
```

### Step 3: データベース接続を確認
```bash
heroku run python manage.py dbshell --app your-app-name
```

### Step 4: Djangoシェルで確認
```bash
heroku run python manage.py shell --app your-app-name
```

```python
# シェル内で実行
from scoreai.models import AIConsultationType
print(AIConsultationType.objects.count())

from django.conf import settings
print(settings.GEMINI_API_KEY)  # Noneの場合は設定されていない
```

### Step 5: マイグレーションを確認
```bash
heroku run python manage.py showmigrations --app your-app-name
```

### Step 6: 静的ファイルを確認
```bash
heroku run python manage.py collectstatic --noinput --app your-app-name
```

---

## 特定のエラーメッセージ別の対処法

### `GEMINI_API_KEYが設定されていません。`
```bash
heroku config:set GEMINI_API_KEY="your-api-key" --app your-app-name
heroku restart --app your-app-name
```

### `選択された会社がありません。`
- ユーザーがログインしていることを確認
- ユーザーに会社を選択させる
- 管理者が`UserCompany`を設定する

### `No AIConsultationType matches the given query.`
```bash
# 初期データを投入
heroku run python manage.py init_ai_consultation_data --app your-app-name
```

### `ModuleNotFoundError: No module named 'markdown'`
```bash
# requirements.txtにmarkdownが含まれているか確認
# 含まれていない場合は追加して再デプロイ
```

### `django.db.utils.OperationalError: no such table`
```bash
# マイグレーションを実行
heroku run python manage.py migrate --app your-app-name
```

---

## 緊急時の対処法

### アプリを再起動
```bash
heroku restart --app your-app-name
```

### すべての環境変数を再確認
```bash
heroku config --app your-app-name
```

### 最新のコミットを確認
```bash
git log -1
```

### ロールバック（必要に応じて）
```bash
# 以前のリリースに戻す
heroku releases --app your-app-name
heroku rollback v123 --app your-app-name
```

---

## 予防策

### 1. デプロイ前のチェックリスト

- [ ] 環境変数がすべて設定されている
- [ ] マイグレーションが実行されている
- [ ] 静的ファイルが収集されている
- [ ] 初期データが投入されている
- [ ] `DEBUG=False`が設定されている
- [ ] `SECRET_KEY`が本番用に設定されている

### 2. デプロイ後の確認

```bash
# アプリの状態を確認
heroku ps --app your-app-name

# ログを確認
heroku logs --tail --app your-app-name

# 環境変数を確認
heroku config --app your-app-name
```

---

## 参考リンク

- [Heroku Logs](https://devcenter.heroku.com/articles/logging)
- [Heroku Config Vars](https://devcenter.heroku.com/articles/config-vars)
- [Django on Heroku](https://devcenter.heroku.com/articles/django-app-configuration)


