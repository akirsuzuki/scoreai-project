# プランによる会社数制限の実装計画

## 現在の実装状況

### ✅ 実装済み
- `FirmPlan.max_companies`: プランごとの最大Company数が定義されている
- `FirmSubscription.total_companies_allowed`: サブスクリプションで許可される総Company数を計算するプロパティが存在
- `FirmCompany`: FirmとCompanyの関連を管理するモデルが存在

### ❌ 未実装
- Company追加時のプラン制限チェック
- プランダウングレード時の超過Company処理
- 現在のCompany数の表示・警告機能

---

## 実装アイデア

### 1. Company追加時の制限チェック

#### 実装場所
- `add_client`関数（`scoreai/views.py`）
- `FirmCompany`作成時（Admin、API、その他の作成箇所）

#### 実装内容
```python
def check_company_limit(firm: Firm) -> tuple[bool, int, int]:
    """
    FirmのCompany数制限をチェック
    
    Returns:
        (is_allowed, current_count, max_allowed)
        - is_allowed: 追加可能かどうか
        - current_count: 現在のCompany数
        - max_allowed: 最大許可数（0の場合は無制限）
    """
    from .models import FirmSubscription, FirmCompany
    
    # サブスクリプションを取得
    subscription = FirmSubscription.objects.filter(
        firm=firm,
        status__in=['trial', 'active']
    ).first()
    
    if not subscription:
        # サブスクリプションがない場合は制限なし（後方互換性）
        return True, 0, 0
    
    # 現在のアクティブなCompany数を取得
    current_count = FirmCompany.objects.filter(
        firm=firm,
        active=True
    ).count()
    
    # 最大許可数を取得
    max_allowed = subscription.total_companies_allowed
    
    # 無制限の場合は常に許可
    if max_allowed == 0:
        return True, current_count, 0
    
    # 制限チェック
    is_allowed = current_count < max_allowed
    
    return is_allowed, current_count, max_allowed
```

#### 使用例
```python
@login_required
def add_client(request, client_id):
    client = Company.objects.get(id=client_id)
    
    # Firmを取得
    from .models import UserFirm
    user_firm = UserFirm.objects.filter(
        user=request.user,
        is_selected=True
    ).first()
    
    if not user_firm:
        messages.error(request, 'Firmが選択されていません。')
        return redirect('firm_clientslist')
    
    # 制限チェック
    from .utils.plan_limits import check_company_limit
    is_allowed, current_count, max_allowed = check_company_limit(user_firm.firm)
    
    if not is_allowed:
        messages.error(
            request,
            f'プランの制限により、これ以上Companyを追加できません。'
            f'（現在: {current_count}社 / 上限: {max_allowed}社）'
            f'プランをアップグレードしてください。'
        )
        return redirect('firm_clientslist')
    
    # 既に追加されているか確認
    if UserCompany.objects.filter(user=request.user, company=client).exists():
        messages.warning(request, f'クライアント "{client.name}" は既に追加されています。')
    else:
        UserCompany.objects.create(user=request.user, company=client, as_consultant=True)
        
        # FirmCompanyも作成（存在しない場合）
        from .models import FirmCompany
        FirmCompany.objects.get_or_create(
            firm=user_firm.firm,
            company=client,
            defaults={
                'active': True,
                'start_date': timezone.now().date()
            }
        )
        
        messages.success(request, f'クライアント "{client.name}" をアサインしました。')
    
    return redirect('firm_clientslist')
```

---

### 2. プランダウングレード時の処理

#### 実装場所
- `SubscriptionManageView`（プラン変更時）
- Stripe Webhook（プラン変更イベント時）

#### 実装方針

**オプション1: 自動非アクティブ化（推奨）**
- 超過分のCompanyを自動的に`active=False`に設定
- 最新のCompanyから順に非アクティブ化
- ユーザーに通知を送信

**オプション2: 警告＋手動選択**
- プランダウングレード時に警告を表示
- ユーザーに保持するCompanyを選択させる
- 選択されなかったCompanyを非アクティブ化

**オプション3: グレース期間**
- プランダウングレード後、一定期間（例：30日）は超過Companyを保持
- 期間終了後に自動非アクティブ化
- 期間中にプランをアップグレードすれば継続

#### 推奨実装（オプション1 + オプション3のハイブリッド）

```python
def handle_plan_downgrade(firm: Firm, new_subscription: FirmSubscription):
    """
    プランダウングレード時のCompany数制限処理
    
    Args:
        firm: Firmオブジェクト
        new_subscription: 新しいサブスクリプション
    """
    from .models import FirmCompany
    from django.utils import timezone
    from datetime import timedelta
    
    # 現在のアクティブなCompany数を取得
    active_companies = FirmCompany.objects.filter(
        firm=firm,
        active=True
    ).order_by('-start_date')  # 最新のものから
    
    current_count = active_companies.count()
    max_allowed = new_subscription.total_companies_allowed
    
    # 無制限の場合は何もしない
    if max_allowed == 0:
        return
    
    # 超過している場合
    if current_count > max_allowed:
        excess_count = current_count - max_allowed
        
        # グレース期間を設定（30日）
        grace_period_end = timezone.now().date() + timedelta(days=30)
        
        # 超過分のCompanyをグレース期間付きで非アクティブ化
        for i, firm_company in enumerate(active_companies[max_allowed:]):
            firm_company.active = False
            firm_company.end_date = grace_period_end
            firm_company.save()
        
        # ユーザーに通知（メール、システム通知など）
        send_plan_downgrade_notification(
            firm=firm,
            excess_count=excess_count,
            grace_period_end=grace_period_end
        )
```

---

### 3. UI/UXの改善

#### 3.1. Company一覧ページでの表示

```html
<!-- firm_clientslist.html に追加 -->
<div class="alert alert-info">
    <strong>プラン制限:</strong>
    現在: {{ current_company_count }}社 / 上限: 
    {% if max_companies == 0 %}
        無制限
    {% else %}
        {{ max_companies }}社
    {% endif %}
    
    {% if current_company_count >= max_companies and max_companies > 0 %}
        <span class="badge bg-warning">制限に達しています</span>
    {% elif current_company_count >= max_companies|add:"-1" and max_companies > 0 %}
        <span class="badge bg-info">あと1社追加可能</span>
    {% endif %}
</div>
```

#### 3.2. プラン変更時の警告

```python
# SubscriptionManageView で実装
def post(self, request, firm_id):
    # プラン変更前のチェック
    old_subscription = self.get_object()
    new_plan = FirmPlan.objects.get(id=request.POST.get('plan_id'))
    
    # 現在のCompany数
    current_count = FirmCompany.objects.filter(
        firm=old_subscription.firm,
        active=True
    ).count()
    
    # 新しいプランの制限
    new_max = new_plan.max_companies
    
    # ダウングレードの場合
    if new_max < old_subscription.plan.max_companies and current_count > new_max:
        excess_count = current_count - new_max
        messages.warning(
            request,
            f'プランを変更すると、{excess_count}社のCompanyが非アクティブになります。'
            f'（30日間のグレース期間があります）'
        )
        # 確認画面を表示
        return render(request, 'scoreai/plan_change_confirm.html', {
            'old_plan': old_subscription.plan,
            'new_plan': new_plan,
            'excess_count': excess_count,
        })
    
    # 通常の処理
    # ...
```

---

### 4. ユーティリティ関数の作成

#### `scoreai/utils/plan_limits.py` を作成

```python
"""
プラン制限に関するユーティリティ関数
"""
from typing import Tuple
from ..models import Firm, FirmSubscription, FirmCompany


def get_current_company_count(firm: Firm) -> int:
    """Firmの現在のアクティブなCompany数を取得"""
    return FirmCompany.objects.filter(
        firm=firm,
        active=True
    ).count()


def get_max_companies_allowed(firm: Firm) -> int:
    """
    Firmが許可される最大Company数を取得
    
    Returns:
        最大許可数（0の場合は無制限）
    """
    subscription = FirmSubscription.objects.filter(
        firm=firm,
        status__in=['trial', 'active']
    ).first()
    
    if not subscription:
        return 0  # サブスクリプションがない場合は無制限
    
    return subscription.total_companies_allowed


def check_company_limit(firm: Firm) -> Tuple[bool, int, int]:
    """
    FirmのCompany数制限をチェック
    
    Returns:
        (is_allowed, current_count, max_allowed)
        - is_allowed: 追加可能かどうか
        - current_count: 現在のCompany数
        - max_allowed: 最大許可数（0の場合は無制限）
    """
    current_count = get_current_company_count(firm)
    max_allowed = get_max_companies_allowed(firm)
    
    # 無制限の場合は常に許可
    if max_allowed == 0:
        return True, current_count, 0
    
    # 制限チェック
    is_allowed = current_count < max_allowed
    
    return is_allowed, current_count, max_allowed


def can_add_company(firm: Firm) -> bool:
    """Companyを追加できるかどうかを簡易チェック"""
    is_allowed, _, _ = check_company_limit(firm)
    return is_allowed
```

---

### 5. プランダウングレード時のスムーズな処理

#### 5.1. グレース期間の実装

```python
# FirmCompanyモデルに追加（マイグレーション必要）
class FirmCompany(models.Model):
    # ... 既存のフィールド ...
    
    grace_period_end = models.DateField(
        'グレース期間終了日',
        null=True,
        blank=True,
        help_text='プランダウングレード時の一時的な保持期間'
    )
    
    def is_in_grace_period(self):
        """グレース期間中かどうか"""
        if not self.grace_period_end:
            return False
        from django.utils import timezone
        return timezone.now().date() <= self.grace_period_end
```

#### 5.2. グレース期間中のCompanyもカウントに含める

```python
def get_current_company_count(firm: Firm, include_grace_period: bool = True) -> int:
    """
    Firmの現在のCompany数を取得
    
    Args:
        firm: Firmオブジェクト
        include_grace_period: グレース期間中のCompanyも含めるか
    """
    queryset = FirmCompany.objects.filter(firm=firm)
    
    if include_grace_period:
        from django.utils import timezone
        from django.db.models import Q
        # アクティブなもの + グレース期間中のもの
        queryset = queryset.filter(
            Q(active=True) | 
            Q(active=False, grace_period_end__gte=timezone.now().date())
        )
    else:
        queryset = queryset.filter(active=True)
    
    return queryset.count()
```

#### 5.3. グレース期間終了時の自動処理

```python
# 管理コマンドを作成: scoreai/management/commands/process_grace_period_companies.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from scoreai.models import FirmCompany


class Command(BaseCommand):
    help = 'グレース期間が終了したCompanyを非アクティブ化'
    
    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # グレース期間が終了したCompanyを取得
        expired_companies = FirmCompany.objects.filter(
            active=False,
            grace_period_end__lt=today,
            grace_period_end__isnull=False
        )
        
        count = expired_companies.count()
        
        if count > 0:
            # グレース期間終了日をクリア（履歴として保持）
            expired_companies.update(grace_period_end=None)
            self.stdout.write(
                self.style.SUCCESS(
                    f'{count}件のCompanyのグレース期間を終了しました。'
                )
            )
        else:
            self.stdout.write('グレース期間終了のCompanyはありません。')
```

#### 5.4. 定期実行の設定

```python
# Heroku Scheduler または cron で実行
# 毎日1回実行: python manage.py process_grace_period_companies
```

---

## 実装の優先順位

### Phase 1: 基本機能（必須）
1. ✅ `check_company_limit`関数の作成
2. ✅ `add_client`関数に制限チェックを追加
3. ✅ UIでの現在のCompany数と制限の表示

### Phase 2: プランダウングレード対応（重要）
4. ✅ `handle_plan_downgrade`関数の作成
5. ✅ グレース期間の実装
6. ✅ プラン変更時の警告表示

### Phase 3: 自動化・運用（推奨）
7. ✅ グレース期間終了時の自動処理コマンド
8. ✅ 通知機能（メール、システム通知）
9. ✅ 管理画面での一括操作

---

## 考慮事項

### 1. 後方互換性
- サブスクリプションがないFirmは制限なしとして扱う
- 既存のCompanyはそのまま保持

### 2. データ整合性
- `FirmCompany.active=False`にしても、データは削除しない
- 履歴として保持し、プランアップグレード時に復元可能

### 3. ユーザー体験
- グレース期間により、急な制限で業務が止まらない
- 明確な警告と説明を提供
- プランアップグレードへの導線を用意

### 4. パフォーマンス
- Company数のカウントはキャッシュを検討
- 大量のCompanyがある場合の処理を最適化

---

## 次のステップ

1. **ユーティリティ関数の作成**: `scoreai/utils/plan_limits.py`
2. **`add_client`関数の修正**: 制限チェックを追加
3. **UIの改善**: Company数と制限の表示
4. **プランダウングレード処理**: グレース期間の実装
5. **テスト**: 各シナリオのテストケース作成


