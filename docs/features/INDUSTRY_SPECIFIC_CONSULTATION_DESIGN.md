# 業界別専門相談室 設計提案書

## 1. 概要

現在の汎用AI相談室に加えて、業界別の専門相談室を追加し、より具体的で実践的なアドバイスや書類作成を可能にする。

### 1.1 目的
- 業界特有の課題に対応した専門的な相談機能を提供
- 銀行提出用の書類（事業計画書、収支計画書など）を自動生成
- 初期投資回収期間などの重要な指標を自動計算

### 1.2 第一弾：外食業界「居酒屋出店計画作成」

## 2. ユーザーフロー設計

### 2.1 トップページからの誘導

```
AI相談センター
├── 汎用相談室（既存）
└── 業界別相談室（新規）
    ├── 外食業界
    │   ├── 居酒屋出店計画作成 ⭐（第一弾）
    │   ├── カフェ出店計画作成（将来）
    │   └── レストラン出店計画作成（将来）
    ├── 小売業界（将来）
    └── 製造業界（将来）
```

### 2.2 詳細フロー

#### ステップ1: 業界選択画面
- **URL**: `/ai-consultation/industry/`
- **表示内容**:
  - 業界別カテゴリー一覧（カード形式）
  - 各業界のアイコンと説明
  - 「外食業界」をクリック

#### ステップ2: 外食業界メニュー
- **URL**: `/ai-consultation/industry/food-service/`
- **表示内容**:
  - 「居酒屋出店計画作成」カード
  - 機能説明：「初期投資回収期間を計算し、銀行提出用の事業計画書を作成」
  - 「始める」ボタン

#### ステップ3: 居酒屋出店計画フォーム
- **URL**: `/ai-consultation/industry/food-service/izakaya-plan/create/`
- **表示内容**: 入力フォーム（後述）

#### ステップ4: 計算結果・プレビュー画面
- **URL**: `/ai-consultation/industry/food-service/izakaya-plan/preview/<plan_id>/`
- **表示内容**:
  - 計算結果サマリー
  - 初期投資回収期間
  - 月次収支予測グラフ
  - 銀行提出用書類のプレビュー

#### ステップ5: 書類生成・ダウンロード
- **URL**: `/ai-consultation/industry/food-service/izakaya-plan/<plan_id>/export/`
- **出力形式**:
  - PDF（銀行提出用）
  - Excel（編集可能版）

## 3. データモデル設計

### 3.1 新規モデル

```python
# models.py

class IndustryCategory(models.Model):
    """業界カテゴリー"""
    id = ULIDField(primary_key=True)
    name = models.CharField(max_length=100)  # 例: "外食業界"
    description = models.TextField()
    icon = models.CharField(max_length=50)  # アイコン名（Font Awesome等）
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class IndustryConsultationType(models.Model):
    """業界別相談タイプ"""
    id = ULIDField(primary_key=True)
    industry_category = models.ForeignKey(IndustryCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)  # 例: "居酒屋出店計画作成"
    description = models.TextField()
    template_type = models.CharField(
        max_length=50,
        choices=[
            ('izakaya_plan', '居酒屋出店計画'),
            ('cafe_plan', 'カフェ出店計画'),
            # 将来拡張用
        ]
    )
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class IzakayaPlan(models.Model):
    """居酒屋出店計画データ"""
    id = ULIDField(primary_key=True)
    # 必須: 選択中のCompanyを保持（SelectedCompanyMixinと連携）
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='izakaya_plans')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='izakaya_plans')
    
    # 基本情報
    store_concept = models.CharField(max_length=200)  # 店のコンセプト
    number_of_seats = models.IntegerField()  # 席数
    opening_hours_start = models.TimeField()  # 営業開始時間
    opening_hours_end = models.TimeField()  # 営業終了時間
    target_customer = models.CharField(max_length=200)  # ターゲット
    average_price_per_customer = models.DecimalField(max_digits=10, decimal_places=0)  # 客単価（円）
    
    # 投資情報
    initial_investment = models.DecimalField(max_digits=12, decimal_places=0)  # 初期投資額（円）
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=0)  # 月額家賃（円）
    
    # 人件費
    number_of_staff = models.IntegerField()  # 社員人数
    staff_monthly_salary = models.DecimalField(max_digits=10, decimal_places=0)  # 社員月給（円）
    part_time_hours_per_month = models.IntegerField()  # アルバイト時間数/月
    part_time_hourly_wage = models.DecimalField(max_digits=8, decimal_places=2)  # アルバイト時給（円）
    
    # 売上係数（JSON形式で保存）
    # 例: {"monday": 0.8, "tuesday": 0.9, ..., "holiday_eve": 1.5}
    sales_coefficients = models.JSONField(default=dict)
    
    # 計算結果（自動計算）
    monthly_revenue = models.DecimalField(max_digits=12, decimal_places=0, null=True)  # 月間売上
    monthly_cost = models.DecimalField(max_digits=12, decimal_places=0, null=True)  # 月間経費
    monthly_profit = models.DecimalField(max_digits=12, decimal_places=0, null=True)  # 月間利益
    payback_period_months = models.IntegerField(null=True)  # 回収期間（月）
    payback_period_years = models.IntegerField(null=True)  # 回収期間（年）
    
    # メタ情報
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_draft = models.BooleanField(default=True)  # 下書きかどうか
    
    class Meta:
        ordering = ['-created_at']
```

### 3.2 計算ロジック

```python
# services/izakaya_plan_service.py

class IzakayaPlanService:
    @staticmethod
    def calculate_monthly_revenue(plan: IzakayaPlan) -> Decimal:
        """
        月間売上を計算
        
        計算式:
        月間売上 = 客単価 × 席数 × 回転率 × 営業日数 × 平均係数
        
        回転率 = 営業時間 / 平均滞在時間
        """
        # 営業時間の計算（時間）
        opening_duration = (
            datetime.combine(date.today(), plan.opening_hours_end) -
            datetime.combine(date.today(), plan.opening_hours_start)
        ).total_seconds() / 3600
        
        # 平均滞在時間（仮に2.5時間とする、将来的には設定可能にする）
        average_stay_hours = 2.5
        
        # 回転率 = 営業時間 / 平均滞在時間
        turnover_rate = opening_duration / average_stay_hours
        
        # 営業日数の計算（月間）
        # 曜日別係数の平均を計算
        coefficients = plan.sales_coefficients
        avg_coefficient = sum(coefficients.values()) / len(coefficients)
        
        # 月間営業日数（仮に30日とする）
        monthly_operating_days = 30
        
        # 月間売上計算
        monthly_revenue = (
            plan.average_price_per_customer *
            plan.number_of_seats *
            turnover_rate *
            monthly_operating_days *
            avg_coefficient
        )
        
        return Decimal(str(monthly_revenue))
    
    @staticmethod
    def calculate_monthly_cost(plan: IzakayaPlan) -> Decimal:
        """
        月間経費を計算
        
        経費 = 家賃 + 人件費 + その他経費（売上の30%を仮定）
        """
        # 人件費
        staff_cost = plan.number_of_staff * plan.staff_monthly_salary
        part_time_cost = plan.part_time_hours_per_month * plan.part_time_hourly_wage
        total_labor_cost = staff_cost + part_time_cost
        
        # その他経費（売上の30%を仮定：食材費、光熱費、その他）
        monthly_revenue = IzakayaPlanService.calculate_monthly_revenue(plan)
        other_costs = monthly_revenue * Decimal('0.3')
        
        # 月間経費
        monthly_cost = plan.monthly_rent + total_labor_cost + other_costs
        
        return Decimal(str(monthly_cost))
    
    @staticmethod
    def calculate_payback_period(plan: IzakayaPlan) -> Tuple[int, int]:
        """
        初期投資回収期間を計算
        
        Returns:
            (年, 月) のタプル
        """
        monthly_revenue = IzakayaPlanService.calculate_monthly_revenue(plan)
        monthly_cost = IzakayaPlanService.calculate_monthly_cost(plan)
        monthly_profit = monthly_revenue - monthly_cost
        
        if monthly_profit <= 0:
            return (999, 999)  # 回収不可能
        
        payback_months = plan.initial_investment / monthly_profit
        payback_years = int(payback_months // 12)
        payback_months_remainder = int(payback_months % 12)
        
        return (payback_years, payback_months_remainder)
    
    @staticmethod
    def calculate_all(plan: IzakayaPlan) -> IzakayaPlan:
        """
        すべての計算を実行してplanを更新
        
        Args:
            plan: IzakayaPlanインスタンス（companyが設定されている必要がある）
        
        Returns:
            更新されたIzakayaPlanインスタンス
        
        Raises:
            ValueError: Companyが設定されていない場合
        """
        # Companyが設定されていることを確認
        if not plan.company:
            raise ValueError("Company must be set for IzakayaPlan")
        
        plan.monthly_revenue = IzakayaPlanService.calculate_monthly_revenue(plan)
        plan.monthly_cost = IzakayaPlanService.calculate_monthly_cost(plan)
        plan.monthly_profit = plan.monthly_revenue - plan.monthly_cost
        
        years, months = IzakayaPlanService.calculate_payback_period(plan)
        plan.payback_period_years = years
        plan.payback_period_months = months
        
        plan.save()
        return plan
```

## 4. UI/UX設計

### 4.1 入力フォーム（ステップ3）

#### セクション1: 基本情報
- 店のコンセプト（テキストエリア、200文字）
- 席数（数値入力）
- 営業時間（開始時間・終了時間の時間選択）
- ターゲット顧客（テキスト入力）
- 客単価（数値入力、円単位）

#### セクション2: 投資情報
- 初期投資額（数値入力、円単位）
  - 内訳入力フォーム（内装、設備、備品など）
- 月額家賃（数値入力、円単位）

#### セクション3: 人件費
- 社員人数（数値入力）
- 社員月給（数値入力、円単位）
- アルバイト時間数/月（数値入力）
- アルバイト時給（数値入力、円単位）

#### セクション4: 売上係数設定
- 曜日別・祝前日別の売上係数を設定
- デフォルト値:
  - 月曜: 0.8
  - 火曜: 0.9
  - 水曜: 0.9
  - 木曜: 1.0
  - 金曜: 1.2
  - 土曜: 1.3
  - 日曜: 1.1
  - 祝前日: 1.5

#### UI要素
- プログレスバー（4セクション中、現在のセクションを表示）
- 「次へ」ボタン（各セクション）
- 「戻る」ボタン（2セクション目以降）
- 「保存して下書き」ボタン（全セクション）
- 「計算してプレビュー」ボタン（最終セクション）

### 4.2 プレビュー画面（ステップ4）

#### 結果サマリーカード
- 初期投資回収期間: **X年Yヶ月**
- 月間売上: **XXX万円**
- 月間経費: **XXX万円**
- 月間利益: **XXX万円**

#### グラフ表示
- 月次収支予測グラフ（12ヶ月分）
  - 売上（棒グラフ）
  - 経費（棒グラフ）
  - 利益（折れ線グラフ）
- 累積利益グラフ（回収期間を可視化）

#### 銀行提出用書類プレビュー
- PDFプレビュー（iframeまたは埋め込み）
- 「PDFダウンロード」ボタン
- 「Excelダウンロード」ボタン

### 4.3 書類テンプレート

#### PDF出力内容
1. **表紙**
   - 事業計画書
   - 会社名
   - 作成日

2. **事業概要**
   - 店のコンセプト
   - ターゲット顧客
   - 営業時間・席数

3. **投資計画**
   - 初期投資額の内訳
   - 月額固定費（家賃、人件費）

4. **収支計画**
   - 月次収支表（12ヶ月分）
   - 年次収支表（3年分）

5. **回収期間分析**
   - 初期投資回収期間
   - 累積利益グラフ

6. **リスク分析**
   - 想定リスクと対策

## 5. 実装フェーズ

### フェーズ1: 基盤構築（1-2週間）
- [ ] `IndustryCategory`モデル作成
- [ ] `IndustryConsultationType`モデル作成
- [ ] `IzakayaPlan`モデル作成
  - [ ] `Company`との関連を必須で設定（`null=False`, `blank=False`）
  - [ ] `related_name='izakaya_plans'`を設定
  - [ ] `SelectedCompanyMixin`との連携を確認
  - [ ] ビューで選択中のCompanyを自動設定するロジックを実装
- [ ] マイグレーション実行

### フェーズ2: 計算ロジック実装（1週間）
- [ ] `IzakayaPlanService`クラス実装
- [ ] 計算ロジックのテスト作成
- [ ] 計算結果の検証

### フェーズ3: UI実装（2週間）
- [ ] 業界選択画面
- [ ] 外食業界メニュー画面
- [ ] 入力フォーム（4セクション）
- [ ] プレビュー画面
- [ ] グラフ表示

### フェーズ4: 書類生成機能（1-2週間）
- [ ] PDF生成（reportlab使用）
- [ ] Excel生成（openpyxl使用）
- [ ] テンプレート作成

### フェーズ5: 統合・テスト（1週間）
- [ ] 既存AI相談室との統合
- [ ] エラーハンドリング
- [ ] ユーザーテスト

## 6. 技術的な考慮事項

### 6.1 既存システムとの統合
- `AIConsultationType`と`IndustryConsultationType`を統合するか、別管理にするか
- 推奨: 別管理（業界別は特殊なフォームと計算ロジックが必要なため）

### 6.1.1 Companyとの関連「
- **重要**: すべての事業計画関連モデル（`IzakayaPlan`など）は、必ず選択中の`Company`を保持する
- `SelectedCompanyMixin`を使用して、ビューで選択中のCompanyを取得
- `company`フィールドは必須（`null=False`, `blank=False`）
- ユーザーは選択中のCompanyのデータのみアクセス可能
- 将来的に他の業界の計画モデル（`CafePlan`、`RestaurantPlan`など）も同様に`Company`を必須で持つ

### 6.2 データ保存
- 下書き機能を実装（途中保存可能）
- 履歴管理（過去の計画を参照可能）

### 6.3 拡張性
- 他の業界（カフェ、レストラン等）への拡張を考慮した設計
- テンプレートタイプを`template_type`で管理

### 6.4 パフォーマンス
- 計算処理は非同期化を検討（将来的に）
- 現時点では同期処理で問題なし

## 7. ビュー実装の注意事項

### 7.1 SelectedCompanyMixinの使用

すべてのビューで`SelectedCompanyMixin`を使用し、選択中のCompanyを取得：

```python
from ..mixins import SelectedCompanyMixin

class IzakayaPlanCreateView(SelectedCompanyMixin, CreateView):
    model = IzakayaPlan
    template_name = 'scoreai/izakaya_plan_form.html'
    
    def form_valid(self, form):
        # 選択中のCompanyを自動設定
        form.instance.company = self.this_company
        form.instance.user = self.request.user
        return super().form_valid(form)
    
    def get_queryset(self):
        # 選択中のCompanyのデータのみ取得
        return IzakayaPlan.objects.filter(company=self.this_company)
```

### 7.2 データアクセス制御

- ユーザーは選択中のCompanyのデータのみアクセス可能
- 他のCompanyのデータにアクセスしようとした場合は403エラー
- クエリセットは常に`company=self.this_company`でフィルタリング

## 8. 次のステップ

1. **設計レビュー**: この設計書をレビューして承認
2. **データモデル実装**: フェーズ1から開始
3. **プロトタイプ作成**: 最小限の機能で動作確認
4. **ユーザーテスト**: 実際のユーザーでテスト
5. **改善・拡張**: フィードバックを反映

## 9. 将来の拡張

- 他の業界への展開（カフェ、レストラン、小売、製造など）
- AIによる最適化提案（「この条件なら回収期間が短縮できます」など）
- 複数シナリオの比較機能
- 銀行への直接提出機能（API連携）

