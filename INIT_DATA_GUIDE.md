# 初期データ投入ガイド

## 方法1: Django管理コマンドを使用（最も簡単・推奨）

### 手順

1. **Django管理コマンドを実行**
```bash
docker compose exec django python manage.py init_ai_consultation_data
```

この方法が最も簡単で確実です。TTYの問題も発生しません。

## 方法2: スクリプトファイルを使用（`-T`フラグが必要）

### 手順

1. **Dockerコンテナ内でスクリプトを実行（`-T`フラグを追加）**
```bash
docker compose exec -T django python manage.py shell < scripts/init_ai_consultation_data.py
```

**注意**: `-T`フラグを追加しないと "the input device is not a TTY" エラーが発生します。

### 実行例（方法1: 管理コマンド）
```bash
$ docker compose exec django python manage.py init_ai_consultation_data
============================================================
AI相談機能の初期データ投入を開始します...
============================================================
✓ 相談タイプを作成しました: 財務相談
✓ 相談タイプを作成しました: 補助金相談
✓ 相談タイプを作成しました: 税務相談
✓ 相談タイプを作成しました: 法律相談
✓ 財務相談のデフォルトスクリプトを作成しました
✓ 補助金相談のデフォルトスクリプトを作成しました
✓ 税務相談のデフォルトスクリプトを作成しました
✓ 法律相談のデフォルトスクリプトを作成しました
============================================================
初期データ投入が完了しました！
============================================================

作成されたデータ:
  相談タイプ: 4件
  システムスクリプト: 4件

次のステップ:
  1. サーバーを再起動: docker compose restart django
  2. AI相談センターにアクセス: http://localhost:8000/ai-consultation/
```

## 方法3: Djangoシェルを対話的に使用

### 手順

1. **Djangoシェルを起動**
```bash
docker compose exec django python manage.py shell
```

2. **スクリプトを読み込んで実行**
```python
>>> exec(open('scripts/init_ai_consultation_data.py').read())
```

### 実行例
```python
$ docker compose exec django python manage.py shell
Python 3.12.12 (main, Nov 20 2024, 15:14:05) [GCC 12.2.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
(InteractiveConsole)
>>> exec(open('scripts/init_ai_consultation_data.py').read())
============================================================
AI相談機能の初期データ投入を開始します...
============================================================
✓ 相談タイプを作成しました: 財務相談
...
>>> exit()
```

## 方法4: 手動でDjangoシェルから実行

### 手順

1. **Djangoシェルを起動**
```bash
docker compose exec django python manage.py shell
```

2. **以下のコードをコピー&ペーストして実行**

```python
from scoreai.models import AIConsultationType, AIConsultationScript, User
from django.contrib.auth import get_user_model

User = get_user_model()

# 相談タイプの作成
financial = AIConsultationType.objects.get_or_create(
    name="財務相談",
    defaults={
        'icon': "💰",
        'description': "決算書データを基に分析",
        'order': 1,
        'color': "#4CAF50",
        'is_active': True,
    }
)[0]

subsidy = AIConsultationType.objects.get_or_create(
    name="補助金相談",
    defaults={
        'icon': "💼",
        'description': "業種・規模を基に提案",
        'order': 2,
        'color': "#2196F3",
        'is_active': True,
    }
)[0]

tax = AIConsultationType.objects.get_or_create(
    name="税務相談",
    defaults={
        'icon': "📋",
        'description': "税務情報を基に提案",
        'order': 3,
        'color': "#FF9800",
        'is_active': True,
    }
)[0]

legal = AIConsultationType.objects.get_or_create(
    name="法律相談",
    defaults={
        'icon': "⚖️",
        'description': "契約・法務を基に提案",
        'order': 4,
        'color': "#9C27B0",
        'is_active': True,
    }
)[0]

# スーパーユーザーを取得
superuser = User.objects.filter(is_superuser=True).first()

# 財務相談のデフォルトスクリプト
AIConsultationScript.objects.get_or_create(
    consultation_type=financial,
    is_default=True,
    defaults={
        'name': 'デフォルト',
        'system_instruction': 'あなたは経験豊富な財務アドバイザーです。与えられた財務情報に基づいて、実践的で具体的なアドバイスを提供してください。',
        'default_prompt_template': '【会社情報】\n会社名: {company_name}\n業種: {industry}\n規模: {size}\n\n【決算書データ】\n{fiscal_summary}\n\n【借入情報】\n{debt_info}\n\n【月次推移データ】\n{monthly_data}\n\n【ユーザーの質問】\n{user_message}\n\n上記の情報を基に、具体的で実践的なアドバイスを提供してください。',
        'is_active': True,
        'created_by': superuser,
    }
)

print("初期データ投入が完了しました！")
print(f"相談タイプ: {AIConsultationType.objects.count()}件")
print(f"システムスクリプト: {AIConsultationScript.objects.count()}件")
```

## データの確認

投入後、以下のコマンドでデータを確認できます：

```bash
docker compose exec django python manage.py shell
```

```python
>>> from scoreai.models import AIConsultationType, AIConsultationScript
>>> AIConsultationType.objects.all()
<QuerySet [<AIConsultationType: 財務相談>, <AIConsultationType: 補助金相談>, ...]>
>>> AIConsultationScript.objects.all()
<QuerySet [<AIConsultationScript: 財務相談 - デフォルト>, ...]>
```

## トラブルシューティング

### エラー: "No such file or directory"
スクリプトファイルのパスが正しいか確認してください。プロジェクトのルートディレクトリから実行してください。

### エラー: "スーパーユーザーが見つかりません"
スーパーユーザーを作成してください：
```bash
docker compose exec django python manage.py createsuperuser
```

### 既存データがある場合
スクリプトは`get_or_create`を使用しているため、既存のデータは上書きされません。既存データを削除したい場合は、Django管理画面またはシェルから削除してください。

## 次のステップ

1. サーバーを再起動
```bash
docker compose restart django
```

2. AI相談センターにアクセス
```
http://localhost:8000/ai-consultation/
```

3. テスト
- 各相談タイプが表示されることを確認
- 相談画面が正常に動作することを確認
- AI応答が生成されることを確認

