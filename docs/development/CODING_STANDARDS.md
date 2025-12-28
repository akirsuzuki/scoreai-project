# SCORE AI プロジェクト コーディング規約・ベストプラクティス

## 目次
1. [基本方針](#基本方針)
2. [コーディングスタイル](#コーディングスタイル)
3. [Djangoベストプラクティス](#djangoベストプラクティス)
4. [コード構造](#コード構造)
5. [型ヒントとドキュメンテーション](#型ヒントとドキュメンテーション)
6. [エラーハンドリング](#エラーハンドリング)
7. [データベースとクエリ](#データベースとクエリ)
8. [セキュリティ](#セキュリティ)
9. [テスト](#テスト)
10. [Git運用](#git運用)
11. [コードレビュー](#コードレビュー)

---

## 基本方針

### 原則
- **可読性第一**: コードは書くよりも読まれる時間の方が長い
- **保守性重視**: 将来の変更を考慮した設計
- **一貫性**: プロジェクト全体で統一されたスタイル
- **シンプルさ**: 過度に複雑な実装を避ける
- **DRY原則**: 重複コードを避ける

### 目標
- 新規メンバーがコードを理解しやすい
- バグの発生を最小限に抑える
- リファクタリングが容易
- テストが書きやすい

---

## コーディングスタイル

### Pythonスタイルガイド

#### PEP 8準拠
- インデント: スペース4つ（タブ禁止）
- 行の長さ: 最大100文字（コメントは80文字推奨）
- 命名規則:
  - クラス名: `PascalCase` (例: `DebtCreateView`)
  - 関数・変数名: `snake_case` (例: `get_debt_list`)
  - 定数: `UPPER_SNAKE_CASE` (例: `MAX_RETRY_COUNT`)
  - プライベート: 先頭に `_` (例: `_internal_method`)

#### インポート順序
```python
# 1. 標準ライブラリ
import csv
import json
from datetime import datetime
from typing import List, Dict, Optional

# 2. サードパーティライブラリ
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin

# 3. ローカルアプリケーション
from .models import Debt, Company
from .forms import DebtForm
from .mixins import SelectedCompanyMixin
```

#### 空行の使い方
- クラス定義の前後: 2行
- 関数定義の前後: 2行
- 論理的なブロックの間: 1行
- インポートグループの間: 1行

#### 文字列
- 通常の文字列: シングルクォート `'text'`
- 文字列内にシングルクォート: ダブルクォート `"It's"`
- 複数行: トリプルクォート `"""text"""`

### Django固有のスタイル

#### モデル
```python
class Debt(models.Model):
    """借入情報を管理するモデル"""
    
    # フィールド定義
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        verbose_name="会社"
    )
    principal = models.IntegerField(
        "借入元本",
        help_text="単位：円"
    )
    
    class Meta:
        verbose_name = '借入'
        verbose_name_plural = '借入'
        indexes = [
            models.Index(fields=['company', 'is_nodisplay']),
        ]
        ordering = ['-issue_date']
    
    def __str__(self):
        return f"{self.company.name} - ¥{self.principal:,}"
```

#### ビュー
- クラスベースビューを優先（関数ベースビューは最小限）
- Mixinを活用して共通処理を分離
- 1つのビュークラスは200行以内を目安

```python
class DebtCreateView(LoginRequiredMixin, SelectedCompanyMixin, CreateView):
    """借入情報作成ビュー"""
    
    model = Debt
    form_class = DebtForm
    template_name = 'scoreai/debt_form.html'
    success_url = reverse_lazy('debts_all')
    
    def form_valid(self, form):
        """フォームバリデーション成功時の処理"""
        form.instance.company = self.this_company
        messages.success(self.request, '借入情報を登録しました。')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = '借入情報登録'
        return context
```

#### フォーム
```python
class DebtForm(forms.ModelForm):
    """借入情報フォーム"""
    
    class Meta:
        model = Debt
        fields = ['financial_institution', 'principal', 'issue_date']
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # フィールドのカスタマイズ
    
    def clean_principal(self):
        """借入元本のバリデーション"""
        principal = self.cleaned_data['principal']
        if principal <= 0:
            raise forms.ValidationError("借入元本は正の数でなければなりません。")
        return principal
```

---

## Djangoベストプラクティス

### プロジェクト構造
```
scoreai/
├── models.py          # モデル定義
├── views/             # ビュー（機能別に分割）
│   ├── __init__.py
│   ├── debt_views.py
│   ├── fiscal_views.py
│   └── user_views.py
├── forms.py           # フォーム定義
├── mixins.py          # カスタムMixin
├── services/          # ビジネスロジック
│   ├── __init__.py
│   ├── debt_service.py
│   └── fiscal_service.py
├── utils/             # ユーティリティ関数
│   ├── __init__.py
│   └── helpers.py
└── tests/             # テスト
    ├── test_models.py
    ├── test_views.py
    └── test_services.py
```

### Mixinの活用
```python
# mixins.py
class SelectedCompanyMixin:
    """選択された会社を取得するMixin"""
    
    def dispatch(self, request, *args, **kwargs):
        self.this_company = self.get_selected_company()
        if not self.this_company:
            raise PermissionDenied("会社が選択されていません。")
        return super().dispatch(request, *args, **kwargs)
    
    def get_selected_company(self):
        """選択された会社を取得"""
        user_company = UserCompany.objects.filter(
            user=self.request.user,
            is_selected=True
        ).select_related('company').first()
        return user_company.company if user_company else None
```

### サービス層の導入
ビジネスロジックはビューから分離し、サービス層に配置

```python
# services/debt_service.py
from typing import List, Dict, Tuple
from decimal import Decimal

class DebtService:
    """借入関連のビジネスロジック"""
    
    @staticmethod
    def get_debt_list_with_totals(company: Company) -> Tuple[List[Dict], Dict]:
        """
        借入リストと集計情報を取得
        
        Args:
            company: 対象会社
            
        Returns:
            (借入リスト, 集計情報の辞書)
        """
        debts = Debt.objects.filter(
            company=company
        ).select_related(
            'financial_institution',
            'secured_type',
            'company'
        ).prefetch_related('company__fiscal_summary_years')
        
        debt_list = []
        totals = {
            'total_monthly_repayment': 0,
            'total_balances_monthly': [0] * 12,
        }
        
        for debt in debts:
            if debt.is_nodisplay or debt.remaining_months < 1:
                continue
            
            debt_data = {
                'id': debt.id,
                'principal': debt.principal,
                'balances_monthly': debt.balances_monthly,
                # ...
            }
            debt_list.append(debt_data)
            totals['total_monthly_repayment'] += debt.monthly_repayment
        
        return debt_list, totals
```

---

## コード構造

### ファイルサイズの目安
- モデルファイル: 500行以内
- ビューファイル: 200行以内（機能別に分割）
- サービスファイル: 300行以内
- ユーティリティファイル: 200行以内

### 関数・メソッドのサイズ
- 1つの関数: 50行以内を目安
- 複雑な処理は複数の関数に分割

### クラスの設計
- 単一責任の原則: 1つのクラスは1つの責任のみ
- 継承よりもコンポジションを優先
- Mixinは共通処理の共有に使用

---

## 型ヒントとドキュメンテーション

### 型ヒント
すべての関数・メソッドに型ヒントを付与

```python
from typing import List, Dict, Optional, Tuple
from django.db.models import QuerySet

def get_debt_list(
    company: Company,
    include_archived: bool = False
) -> Tuple[List[Dict[str, any]], Dict[str, any]]:
    """
    借入リストを取得
    
    Args:
        company: 対象会社
        include_archived: アーカイブ済みを含めるか
        
    Returns:
        (借入リスト, 集計情報)
    """
    pass
```

### Docstring
Google形式のdocstringを使用

```python
def calculate_weighted_average(
    debts: List[Debt],
    months: int = 12
) -> List[Decimal]:
    """
    加重平均金利を計算
    
    各月の残高に基づいて加重平均金利を計算します。
    
    Args:
        debts: 借入オブジェクトのリスト
        months: 計算対象月数（デフォルト: 12）
        
    Returns:
        各月の加重平均金利のリスト
        
    Raises:
        ValueError: debtsが空の場合
        
    Example:
        >>> debts = Debt.objects.filter(company=company)
        >>> rates = calculate_weighted_average(debts)
        >>> print(rates[0])
        2.5
    """
    if not debts:
        raise ValueError("借入リストが空です。")
    # ...
```

### コメント
- **Why（なぜ）**を説明するコメントを書く
- **What（何を）**はコードが説明する
- 複雑なロジックには説明を追加

```python
# 良い例: なぜこの処理が必要か説明
# リスケ済みの借入は残高計算が異なるため、別処理が必要
if debt.is_rescheduled:
    balance = calculate_rescheduled_balance(debt)
else:
    balance = calculate_normal_balance(debt)

# 悪い例: コードの内容を繰り返すだけ
# リスケ済みかどうかチェック
if debt.is_rescheduled:
    # リスケ済みの場合
    balance = calculate_rescheduled_balance(debt)
```

---

## エラーハンドリング

### 例外処理の原則
1. 具体的な例外をキャッチ
2. ユーザーフレンドリーなメッセージ
3. ログに詳細を記録
4. 適切なHTTPステータスコードを返す

### 実装例

```python
from django.core.exceptions import ValidationError, PermissionDenied
from django.http import Http404
import logging

logger = logging.getLogger(__name__)

class DebtCreateView(LoginRequiredMixin, SelectedCompanyMixin, CreateView):
    def form_valid(self, form):
        try:
            form.instance.company = self.this_company
            return super().form_valid(form)
        except ValidationError as e:
            logger.warning(
                f"Validation error in DebtCreateView: {e}",
                extra={'user': self.request.user.id, 'company': self.this_company.id}
            )
            messages.error(self.request, '入力内容に誤りがあります。確認してください。')
            return self.form_invalid(form)
        except Exception as e:
            logger.error(
                f"Unexpected error in DebtCreateView: {e}",
                exc_info=True,
                extra={'user': self.request.user.id}
            )
            messages.error(
                self.request,
                'システムエラーが発生しました。管理者にお問い合わせください。'
            )
            return self.form_invalid(form)
```

### カスタム例外
```python
# exceptions.py
class DebtCalculationError(Exception):
    """借入計算エラー"""
    pass

class CompanyNotFoundError(Exception):
    """会社が見つからないエラー"""
    pass
```

### バリデーション
- モデルレベル: `clean()` メソッド
- フォームレベル: `clean_<field>()` メソッド
- ビジネスロジック: サービス層で検証

```python
# models.py
class Debt(models.Model):
    def clean(self):
        super().clean()
        if self.issue_date and self.start_date:
            if self.issue_date > self.start_date:
                raise ValidationError({
                    'start_date': '返済開始日は実行日以降でなければなりません。'
                })
```

---

## データベースとクエリ

### クエリ最適化

#### select_related / prefetch_related
関連オブジェクトは必ず事前取得

```python
# 悪い例: N+1問題
debts = Debt.objects.filter(company=company)
for debt in debts:
    print(debt.financial_institution.name)  # 各ループでクエリ

# 良い例
debts = Debt.objects.filter(company=company).select_related(
    'financial_institution',
    'secured_type',
    'company'
)
for debt in debts:
    print(debt.financial_institution.name)  # クエリなし
```

#### バルク操作
複数のオブジェクトを一度に処理

```python
# 悪い例
for debt in debts:
    debt.is_nodisplay = True
    debt.save()  # 各ループでクエリ

# 良い例
Debt.objects.filter(id__in=[d.id for d in debts]).update(is_nodisplay=True)
```

#### インデックス
頻繁に検索されるフィールドにインデックスを設定

```python
class Debt(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['company', 'is_nodisplay']),
            models.Index(fields=['financial_institution']),
        ]
```

### トランザクション
データ整合性が重要な処理はトランザクション内で実行

```python
from django.db import transaction

@transaction.atomic
def import_csv_data(csv_file, company):
    """CSVデータのインポート（トランザクション内）"""
    try:
        # インポート処理
        pass
    except Exception as e:
        # エラー時は自動的にロールバック
        logger.error(f"CSV import failed: {e}")
        raise
```

### クエリの評価タイミング
必要になるまでクエリを評価しない

```python
# 良い例: 遅延評価
debts = Debt.objects.filter(company=company)
if some_condition:
    debts = debts.filter(is_nodisplay=False)
# ここで初めてクエリが実行される
debt_list = list(debts)
```

---

## セキュリティ

### 認証・認可
- すべてのビューで `LoginRequiredMixin` を使用
- オブジェクトレベルの権限チェックを実装

```python
class DebtUpdateView(LoginRequiredMixin, SelectedCompanyMixin, UpdateView):
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # 選択された会社のデータか確認
        if obj.company != self.this_company:
            raise PermissionDenied("このデータにアクセスする権限がありません。")
        return obj
```

### CSRF対策
- フォームには必ず `{% csrf_token %}`
- APIエンドポイントには適切な認証を実装
- `csrf_exempt` は最小限に

### XSS対策
- ユーザー入力は必ずエスケープ
- `|safe` フィルタは慎重に使用
- Content Security Policy (CSP) の設定

### SQLインジェクション対策
- ORMを徹底使用（生SQLは避ける）
- パラメータ化クエリを使用

```python
# 悪い例（絶対にしない）
query = f"SELECT * FROM debt WHERE company_id = {company_id}"

# 良い例
Debt.objects.filter(company_id=company_id)
```

### パスワード管理
- パスワードはハッシュ化（Djangoが自動処理）
- パスワードポリシーの設定
- セッション管理の適切な設定

### ログ管理
- 機密情報はログに出力しない
- セキュリティイベントは必ずログに記録

```python
logger.warning(
    "Failed login attempt",
    extra={
        'username': username,
        'ip_address': request.META.get('REMOTE_ADDR'),
        # パスワードは絶対にログに出力しない
    }
)
```

---

## テスト

### テストの原則
- テスト可能なコードを書く
- 1つのテストは1つのことをテスト
- テスト名は明確に（何をテストしているか分かる）

### テスト構造
```python
# tests/test_debt_service.py
from django.test import TestCase
from scoreai.models import Company, Debt
from scoreai.services.debt_service import DebtService

class DebtServiceTestCase(TestCase):
    """DebtServiceのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.company = Company.objects.create(
            name="テスト会社",
            fiscal_month=3
        )
    
    def test_get_debt_list_with_totals(self):
        """借入リスト取得のテスト"""
        # Arrange
        debt = Debt.objects.create(
            company=self.company,
            principal=1000000,
            # ...
        )
        
        # Act
        debt_list, totals = DebtService.get_debt_list_with_totals(self.company)
        
        # Assert
        self.assertEqual(len(debt_list), 1)
        self.assertEqual(totals['total_monthly_repayment'], debt.monthly_repayment)
    
    def test_get_debt_list_empty_company(self):
        """借入がない会社の場合"""
        debt_list, totals = DebtService.get_debt_list_with_totals(self.company)
        self.assertEqual(len(debt_list), 0)
```

### テストカバレッジ
- 目標: 80%以上
- 重要なビジネスロジック: 100%
- ビュー: 主要なパスのみ

### テストの種類
1. **ユニットテスト**: 個別の関数・メソッド
2. **統合テスト**: 複数コンポーネントの連携
3. **機能テスト**: エンドツーエンドの動作

---

## Git運用

### ブランチ戦略
- `main`: 本番環境用（保護）
- `develop`: 開発用
- `feature/機能名`: 機能追加
- `fix/バグ名`: バグ修正
- `refactor/リファクタリング名`: リファクタリング

### コミットメッセージ
Conventional Commits形式を推奨

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type:**
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント
- `style`: コードスタイル（フォーマットなど）
- `refactor`: リファクタリング
- `test`: テスト追加・修正
- `chore`: その他（ビルド、設定など）

**例:**
```
feat(debt): 借入一覧に検索機能を追加

- 金融機関名での検索を実装
- 検索結果のハイライト表示

Closes #123
```

### コミットの粒度
- 1つのコミットは1つの変更
- 関連する変更はまとめる
- 大きな変更は複数のコミットに分割

---

## コードレビュー

### レビューの観点

#### 機能性
- [ ] 要件を満たしているか
- [ ] エッジケースに対応しているか
- [ ] エラーハンドリングが適切か

#### コード品質
- [ ] 命名が適切か
- [ ] 重複コードがないか
- [ ] 複雑すぎないか（循環的複雑度）
- [ ] 型ヒントが付いているか
- [ ] docstringが書かれているか

#### パフォーマンス
- [ ] N+1問題がないか
- [ ] 不要なクエリがないか
- [ ] インデックスが適切か

#### セキュリティ
- [ ] 認証・認可が適切か
- [ ] XSS対策がされているか
- [ ] SQLインジェクション対策がされているか
- [ ] 機密情報が漏洩しないか

#### テスト
- [ ] テストが書かれているか
- [ ] テストが通るか
- [ ] カバレッジが十分か

### レビューコメントの書き方
- 建設的で具体的なフィードバック
- 理由を説明
- 改善案を提示

```
良い例:
"この部分でN+1問題が発生する可能性があります。
select_related('financial_institution')を追加することで
解決できます。"

悪い例:
"これは良くない"
```

### 承認基準
- 最低1名の承認が必要
- セキュリティ関連は2名の承認
- テストがすべて通ること
- コードスタイルチェックが通ること

---

## 補足: よくある問題と対処法

### 問題1: views.pyが大きすぎる
**対処法:**
- 機能別にファイルを分割
- ビジネスロジックをサービス層に移動

### 問題2: N+1クエリ問題
**対処法:**
- `select_related()` / `prefetch_related()` を使用
- Django Debug Toolbarで検出

### 問題3: 重複コード
**対処法:**
- 共通処理を関数・クラスに抽出
- Mixinを活用

### 問題4: エラーメッセージが分かりにくい
**対処法:**
- ユーザー向けメッセージを明確に
- 解決方法を提示

### 問題5: テストが書けない
**対処法:**
- テスト可能な設計にする
- 依存関係を注入可能にする

---

## 参考資料

### 公式ドキュメント
- [Django Documentation](https://docs.djangoproject.com/)
- [PEP 8 -- Style Guide for Python Code](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

### ツール
- **Linting**: `flake8`, `pylint`, `black` (フォーマッター)
- **型チェック**: `mypy`
- **テスト**: `pytest`, `pytest-django`
- **カバレッジ**: `coverage.py`

### 設定例

#### .flake8
```ini
[flake8]
max-line-length = 100
exclude = migrations,venv,__pycache__
ignore = E203, E266, E501, W503
```

#### pyproject.toml (black)
```toml
[tool.black]
line-length = 100
target-version = ['py39']
include = '\.pyi?$'
```

---

## 更新履歴

- 2024-XX-XX: 初版作成

---

**注意**: このドキュメントは継続的に更新されます。疑問点や改善案があれば、チームで議論して更新してください。

