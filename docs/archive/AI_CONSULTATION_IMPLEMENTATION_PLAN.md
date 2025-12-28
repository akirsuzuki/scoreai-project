# AI相談機能実装計画

## 概要
顧客の決算データを基に、財務・補助金・税務・法律などの相談に対応できるAI機能を実装します。
システム管理者がスクリプトを管理し、ユーザーも自分専用のスクリプトをカスタマイズできる機能を提供します。

## データモデル設計

### 1. 相談タイプ（AIConsultationType）
```python
class AIConsultationType(models.Model):
    """相談タイプ（財務、補助金・助成金、税務、法律など）"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    name = models.CharField(max_length=50, unique=True)  # "財務相談"
    icon = models.CharField(max_length=20)  # "💰"
    description = models.TextField()  # 相談タイプの説明
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)  # 表示順序
    color = models.CharField(max_length=7, default="#007bff")  # カードの色
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'AI相談タイプ'
        verbose_name_plural = 'AI相談タイプ'
    
    def __str__(self):
        return self.name
```

### 2. システム用AIスクリプト（AIConsultationScript）
```python
class AIConsultationScript(models.Model):
    """AI相談スクリプト（システム全体用・管理者が編集）"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    consultation_type = models.ForeignKey(
        AIConsultationType,
        on_delete=models.CASCADE,
        related_name='system_scripts'
    )
    name = models.CharField(max_length=100)  # スクリプト名
    system_instruction = models.TextField()  # システムプロンプト
    default_prompt_template = models.TextField()  # デフォルトプロンプトテンプレート
    is_default = models.BooleanField(default=True)  # デフォルトスクリプトか
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'AI相談スクリプト（システム）'
        verbose_name_plural = 'AI相談スクリプト（システム）'
        unique_together = [['consultation_type', 'is_default']]
    
    def __str__(self):
        return f"{self.consultation_type.name} - {self.name}"
```

### 3. ユーザー用AIスクリプト（UserAIConsultationScript）
```python
class UserAIConsultationScript(models.Model):
    """ユーザー独自のAI相談スクリプト"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ai_scripts'
    )
    consultation_type = models.ForeignKey(
        AIConsultationType,
        on_delete=models.CASCADE,
        related_name='user_scripts'
    )
    name = models.CharField(max_length=100)  # スクリプト名
    system_instruction = models.TextField()  # システムプロンプト
    prompt_template = models.TextField()  # プロンプトテンプレート
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)  # このタイプのデフォルトか
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'AI相談スクリプト（ユーザー）'
        verbose_name_plural = 'AI相談スクリプト（ユーザー）'
        unique_together = [['user', 'consultation_type', 'is_default']]
    
    def __str__(self):
        return f"{self.user.username} - {self.consultation_type.name} - {self.name}"
```

### 4. 相談履歴（AIConsultationHistory）
```python
class AIConsultationHistory(models.Model):
    """AI相談の履歴"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='consultation_histories')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='consultation_histories')
    consultation_type = models.ForeignKey(AIConsultationType, on_delete=models.CASCADE)
    user_message = models.TextField()  # ユーザーの質問
    ai_response = models.TextField()  # AIの応答
    script_used = models.ForeignKey(
        AIConsultationScript,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )  # 使用したスクリプト（システム用）
    user_script_used = models.ForeignKey(
        UserAIConsultationScript,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )  # 使用したスクリプト（ユーザー用）
    data_snapshot = models.JSONField(default=dict)  # 相談時に使用したデータのスナップショット
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'AI相談履歴'
        verbose_name_plural = 'AI相談履歴'
    
    def __str__(self):
        return f"{self.user.username} - {self.consultation_type.name} - {self.created_at}"
```

## プロンプトテンプレート設計

### テンプレート変数
- `{user_message}`: ユーザーの質問
- `{company_name}`: 会社名
- `{fiscal_summary}`: 決算書データ（JSON形式）
- `{debt_info}`: 借入情報（JSON形式）
- `{company_info}`: 会社情報（業種、規模など）
- `{monthly_data}`: 月次推移データ（JSON形式）

### 例：財務相談のテンプレート
```
あなたは経験豊富な財務アドバイザーです。
以下の会社の財務データを分析し、ユーザーの質問に対して具体的で実践的なアドバイスを提供してください。

【会社情報】
会社名: {company_name}
業種: {company_info.industry}
規模: {company_info.size}

【決算書データ】
{fiscal_summary}

【借入情報】
{debt_info}

【月次推移データ】
{monthly_data}

【ユーザーの質問】
{user_message}

上記の情報を基に、以下の点を考慮して回答してください：
1. 財務状況の分析
2. 具体的な改善提案
3. 優先順位の高いアクション
4. リスク要因の指摘

回答は日本語で、専門的すぎない言葉で説明してください。
```

## 実装ステップ

### Phase 1: データモデルとマイグレーション
1. `AIConsultationType`モデルの作成
2. `AIConsultationScript`モデルの作成
3. `UserAIConsultationScript`モデルの作成
4. `AIConsultationHistory`モデルの作成
5. マイグレーションの実行
6. 初期データの投入（相談タイプの作成）

### Phase 2: データ収集機能
1. 相談タイプ別のデータ収集関数の実装
2. プロンプトテンプレートの構築機能
3. データスナップショット機能

### Phase 3: AI相談機能の実装
1. 相談タイプ選択画面
2. 相談画面（チャット形式）
3. AI応答生成機能
4. 相談履歴の保存

### Phase 4: スクリプト管理機能
1. 管理者用スクリプト編集画面
2. ユーザー用スクリプト編集画面
3. スクリプトのプレビュー機能

### Phase 5: UI/UX改善
1. サイドバーメニューの再構成
2. AI相談センターのデザイン
3. 相談カードのデザイン
4. チャットUIの改善

## 相談タイプ別のデータ収集

### 財務相談
```python
def get_financial_consultation_data(company: Company) -> dict:
    """財務相談に必要なデータを収集"""
    # 最新の決算データ
    latest_fiscal = FiscalSummary_Year.objects.filter(
        company=company,
        is_draft=False
    ).order_by('-year').first()
    
    # 借入情報
    debts = Debt.objects.filter(
        company=company,
        is_nodisplay=False
    ).select_related('financial_institution', 'secured_type')
    
    # 月次推移データ（直近12ヶ月）
    monthly_data = FiscalSummary_Month.objects.filter(
        fiscal_summary_year__company=company
    ).order_by('-fiscal_summary_year__year', '-period')[:12]
    
    return {
        'fiscal_summary': latest_fiscal.to_dict() if latest_fiscal else {},
        'debt_info': [debt.to_dict() for debt in debts],
        'monthly_data': [m.to_dict() for m in monthly_data],
        'company_info': {
            'name': company.name,
            'industry': company.industry_classification.name if company.industry_classification else None,
            'size': company.get_company_size_display(),
        }
    }
```

### 補助金・助成金相談
```python
def get_subsidy_consultation_data(company: Company) -> dict:
    """補助金・助成金相談に必要なデータを収集"""
    # 会社情報
    # 決算データ（売上、従業員数など）
    # 業種情報
    
    return {
        'company_info': {
            'name': company.name,
            'industry': company.industry_classification.name if company.industry_classification else None,
            'size': company.get_company_size_display(),
            'location': company.location if hasattr(company, 'location') else None,
        },
        'financial_data': {
            'sales': latest_fiscal.sales if latest_fiscal else None,
            'employees': company.employees if hasattr(company, 'employees') else None,
        }
    }
```

## URL設計

```python
# AI相談関連
path('ai-consultation/', views.AIConsultationCenterView.as_view(), name='ai_consultation_center'),
path('ai-consultation/<str:consultation_type_id>/', views.AIConsultationView.as_view(), name='ai_consultation'),
path('ai-consultation/history/', views.AIConsultationHistoryView.as_view(), name='ai_consultation_history'),

# スクリプト管理（管理者用）
path('admin/ai-scripts/', views.AdminAIScriptListView.as_view(), name='admin_ai_script_list'),
path('admin/ai-scripts/create/', views.AdminAIScriptCreateView.as_view(), name='admin_ai_script_create'),
path('admin/ai-scripts/<str:script_id>/edit/', views.AdminAIScriptUpdateView.as_view(), name='admin_ai_script_edit'),

# スクリプト管理（ユーザー用）
path('settings/my-scripts/', views.UserAIScriptListView.as_view(), name='user_ai_script_list'),
path('settings/my-scripts/create/', views.UserAIScriptCreateView.as_view(), name='user_ai_script_create'),
path('settings/my-scripts/<str:script_id>/edit/', views.UserAIScriptUpdateView.as_view(), name='user_ai_script_edit'),
```

## ビュー設計

### AI相談センター
```python
class AIConsultationCenterView(SelectedCompanyMixin, TemplateView):
    """AI相談センターのトップページ"""
    template_name = 'scoreai/ai_consultation_center.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        consultation_types = AIConsultationType.objects.filter(is_active=True).order_by('order')
        context['consultation_types'] = consultation_types
        return context
```

### AI相談画面
```python
class AIConsultationView(SelectedCompanyMixin, View):
    """AI相談画面（チャット形式）"""
    
    def get(self, request, consultation_type_id):
        consultation_type = get_object_or_404(
            AIConsultationType,
            id=consultation_type_id,
            is_active=True
        )
        # 相談履歴を取得
        histories = AIConsultationHistory.objects.filter(
            user=request.user,
            company=self.this_company,
            consultation_type=consultation_type
        ).order_by('-created_at')[:10]
        
        return render(request, 'scoreai/ai_consultation.html', {
            'consultation_type': consultation_type,
            'histories': histories,
        })
    
    def post(self, request, consultation_type_id):
        consultation_type = get_object_or_404(
            AIConsultationType,
            id=consultation_type_id,
            is_active=True
        )
        user_message = request.POST.get('message', '')
        
        # データを収集
        data = get_consultation_data(consultation_type, self.this_company)
        
        # スクリプトを取得（ユーザー用 → システム用の順）
        user_script = UserAIConsultationScript.objects.filter(
            user=request.user,
            consultation_type=consultation_type,
            is_active=True,
            is_default=True
        ).first()
        
        if user_script:
            script = user_script
        else:
            script = AIConsultationScript.objects.filter(
                consultation_type=consultation_type,
                is_active=True,
                is_default=True
            ).first()
        
        # プロンプトを構築
        prompt, system_instruction = build_consultation_prompt(
            consultation_type,
            user_message,
            data,
            user_script if user_script else None
        )
        
        # AI応答を生成
        try:
            ai_response = get_gemini_response(
                prompt,
                system_instruction=system_instruction
            )
            
            # 履歴を保存
            history = AIConsultationHistory.objects.create(
                user=request.user,
                company=self.this_company,
                consultation_type=consultation_type,
                user_message=user_message,
                ai_response=ai_response,
                script_used=script if not user_script else None,
                user_script_used=user_script if user_script else None,
                data_snapshot=data
            )
            
            return JsonResponse({
                'success': True,
                'response': ai_response,
                'history_id': history.id
            })
        except Exception as e:
            logger.error(f"AI consultation error: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'AI応答の生成中にエラーが発生しました。'
            }, status=500)
```

## フォーム設計

### スクリプト編集フォーム
```python
class AIConsultationScriptForm(forms.ModelForm):
    class Meta:
        model = AIConsultationScript
        fields = ['name', 'system_instruction', 'default_prompt_template', 'is_default', 'is_active']
        widgets = {
            'system_instruction': forms.Textarea(attrs={'rows': 10, 'class': 'form-control'}),
            'default_prompt_template': forms.Textarea(attrs={'rows': 15, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['system_instruction'].help_text = 'AIの役割や振る舞いを定義するシステムプロンプト'
        self.fields['default_prompt_template'].help_text = 'プロンプトテンプレート。{user_message}, {company_name}, {fiscal_summary}などの変数が使用できます。'
```

## 次のステップ

1. データモデルの実装
2. マイグレーションの作成
3. 初期データの投入
4. ビューとテンプレートの実装
5. スクリプト管理機能の実装

