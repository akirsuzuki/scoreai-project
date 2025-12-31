from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
from .models import (
    Company,
    IndustryClassification,
    IndustrySubClassification,
    FiscalSummary_Year,
    FiscalSummary_Month,
    Debt,
    Stakeholder_name,
    StockEvent,
    StockEventLine,
    MeetingMinutes,
    AIConsultationType,
    AIConsultationScript,
    UserAIConsultationScript,
    Firm,
)
from django_select2.forms import Select2Widget
from django.contrib.auth import get_user_model


User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label='メールアドレス')
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("このメールアドレスは既に使用されています。")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = field.label


class UserProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError("このメールアドレスは既に使用されています。")
        return email

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'fiscal_month', 'industry_classification', 'industry_subclassification', 'company_size', 'api_key', 'api_provider']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'fiscal_month': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 12,
            }),
            'industry_classification': forms.Select(attrs={'class': 'form-control'}),
            'industry_subclassification': forms.Select(attrs={'class': 'form-control'}),
            'company_size': forms.Select(attrs={'class': 'form-control'}),
            'api_key': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'password',
                'placeholder': 'APIキーを入力（上限超過時に使用）'
            }),
            'api_provider': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': '会社名',
            'fiscal_month': '決算月',
            'industry_classification': '業種分類',
            'industry_subclassification': '業種小分類',
            'company_size': '企業規模',
            'api_key': 'APIキー',
            'api_provider': 'APIプロバイダー',
        }
        help_texts = {
            'api_key': '上限超過時に使用するAPIキー（Company Userのみ使用可能）',
            'api_provider': 'APIキーのプロバイダーを選択',
        }


    def __init__(self, *args, **kwargs):
        super(CompanyForm, self).__init__(*args, **kwargs)
        # 必須項目を指定
        self.fields['name'].required = True
        self.fields['fiscal_month'].required = True
        self.fields['industry_classification'].required = True
        self.fields['industry_subclassification'].required = True
        self.fields['company_size'].required = True


class IndustryBenchmarkImportForm(forms.Form):
    industry_classification = forms.ModelChoiceField(
        queryset=IndustryClassification.objects.all(),
        label='業種分類',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    file = forms.FileField(label='CSVファイル', widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'}))


class FiscalSummary_YearForm(forms.ModelForm):
    class Meta:
        model = FiscalSummary_Year
        fields = '__all__'
        exclude = ['company']


class FiscalSummary_MonthForm(forms.ModelForm):
    class Meta:
        model = FiscalSummary_Month
        fields = '__all__'
        exclude = ['company']


class MoneyForwardCsvUploadForm_Month(forms.Form):
    fiscal_year = forms.ModelChoiceField(
        queryset=FiscalSummary_Year.objects.none(),
        label='年度',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    file = forms.FileField(label='CSVファイル', widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'}))

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)

        if company:
            self.fields['fiscal_year'].queryset = FiscalSummary_Year.objects.filter(company=company)


class OcrUploadForm(forms.Form):
    document_type = forms.ChoiceField(
        label='書類タイプ',
        choices=[
            ('financial_statement', '決算書'),
            ('loan_contract', '金銭消費貸借契約書'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='アップロードする書類の種類を選択してください。'
    )
    file_type = forms.ChoiceField(
        label='ファイルタイプ',
        choices=[
            ('auto', '自動判定'),
            ('pdf', 'PDF'),
            ('image', '画像（PNG/JPEG/GIF/BMP）'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='auto',
        help_text='ファイルタイプを指定するか、自動判定を選択してください。'
    )
    file = forms.FileField(
        label='ファイル',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.png,.jpg,.jpeg,.gif,.bmp'}),
        help_text='PDFまたは画像ファイルをアップロードしてください。'
    )
    fiscal_year = forms.ModelChoiceField(
        queryset=FiscalSummary_Year.objects.none(),
        label='年度',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='決算書の場合は年度を選択してください（任意）。'
    )

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)

        if company:
            self.fields['fiscal_year'].queryset = FiscalSummary_Year.objects.filter(company=company)


class MoneyForwardCsvUploadForm_Year(forms.Form):
    fiscal_year = forms.ModelChoiceField(
        queryset=FiscalSummary_Year.objects.none(),
        label='年度',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    file = forms.FileField(label='CSVファイル', widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'}))

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)

        if company:
            self.fields['fiscal_year'].queryset = FiscalSummary_Year.objects.filter(company=company)



class DebtForm(forms.ModelForm):
    issue_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label='実行日')
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label='返済開始')
    reschedule_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label='リスケ日', required=False)
    class Meta:
        model = Debt
        fields = ['financial_institution', 'principal', 'issue_date', 'start_date', 'interest_rate', 'monthly_repayment', 'secured_type', 'is_securedby_management', 'adjusted_amount_first', 'is_collateraled', 'adjusted_amount_last','is_rescheduled', 'reschedule_date', 'reschedule_balance', 'memo_short', 'memo_long', 'is_nodisplay', 'document_url', 'document_url2', 'document_url3', 'document_url_c1', 'document_url_c2', 'document_url_c3']
        widgets = {
            'financial_institution': Select2Widget,
            'is_rescheduled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_nodisplay': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_securedby_management': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_collateraled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_form_fields()

    def setup_form_fields(self):
        self.fields['financial_institution'].widget.attrs.update({'class': 'form-control select2'})
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'


class Stakeholder_nameForm(forms.ModelForm):
    class Meta:
        model = Stakeholder_name
        fields = '__all__'
        exclude = ['company']


class StockEventForm(forms.ModelForm):
    class Meta:
        model = StockEvent
        fields = '__all__'
        exclude = ['company']


class StockEventLineForm(forms.ModelForm):
    class Meta:
        model = StockEventLine
        fields = '__all__'
        exclude = ['stock_event']


class CsvUploadForm(forms.Form):
    file = forms.FileField(label='CSVファイル', widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'}))


class ChatForm(forms.Form):
    message = forms.CharField(
        label='メッセージ',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        max_length=1000
    )


class MeetingMinutesForm(forms.ModelForm):
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 15}),
        help_text='Markdown形式で記述できます。見出し、リスト、太字、コードブロックなどが使用できます。'
    )
    class Meta:
        model = MeetingMinutes
        fields = ['company', 'created_by', 'meeting_date', 'notes']
        widgets = {
            'meeting_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            # 'notes' widget is overridden by the CharField above
        }


class IndustryClassificationImportForm(forms.Form):
    file = forms.FileField(label='CSVファイル', widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'}))


class IndustrySubClassificationImportForm(forms.Form):
    industry_classification = forms.ModelChoiceField(
        queryset=IndustryClassification.objects.all(),
        label='業種分類',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    file = forms.FileField(label='CSVファイル', widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'}))


class FirmSettingsForm(forms.ModelForm):
    """Firm設定フォーム"""
    class Meta:
        model = Firm
        fields = ['name', 'api_key', 'api_provider']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'api_key': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'password',
                'placeholder': 'APIキーを入力（上限超過時に使用）'
            }),
            'api_provider': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Firm名',
            'api_key': 'APIキー',
            'api_provider': 'APIプロバイダー',
        }
        help_texts = {
            'api_key': '上限超過時に使用するAPIキー',
            'api_provider': 'APIキーのプロバイダーを選択',
        }


class AIConsultationScriptForm(forms.ModelForm):
    """AIスクリプトフォーム（システム用）"""
    class Meta:
        model = AIConsultationScript
        fields = ['consultation_type', 'name', 'system_instruction', 'default_prompt_template', 'is_default', 'is_active']
        widgets = {
            'consultation_type': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'system_instruction': forms.Textarea(attrs={'rows': 10, 'class': 'form-control'}),
            'default_prompt_template': forms.Textarea(attrs={'rows': 15, 'class': 'form-control'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['consultation_type'].queryset = AIConsultationType.objects.filter(is_active=True).order_by('order')
        self.fields['system_instruction'].help_text = 'AIの役割や振る舞いを定義するシステムプロンプト'
        self.fields['default_prompt_template'].help_text = 'プロンプトテンプレート。利用可能な変数: {user_message}（ユーザーの質問）, {company_name}（会社名）, {industry}（業種）, {size}（規模）, {fiscal_summary}（決算書データ・JSON）, {debt_info}（借入情報・JSON）, {monthly_data}（月次推移データ・JSON）。使用例はフォーム下部を参照してください。'


class UserAIConsultationScriptForm(forms.ModelForm):
    """AIスクリプトフォーム（ユーザー用）"""
    class Meta:
        model = UserAIConsultationScript
        fields = ['consultation_type', 'name', 'system_instruction', 'prompt_template', 'is_default', 'is_active']
        widgets = {
            'consultation_type': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'system_instruction': forms.Textarea(attrs={'rows': 10, 'class': 'form-control'}),
            'prompt_template': forms.Textarea(attrs={'rows': 15, 'class': 'form-control'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['consultation_type'].queryset = AIConsultationType.objects.filter(is_active=True).order_by('order')
        self.fields['system_instruction'].help_text = 'AIの役割や振る舞いを定義するシステムプロンプト'
        self.fields['prompt_template'].help_text = 'プロンプトテンプレート。利用可能な変数: {user_message}（ユーザーの質問）, {company_name}（会社名）, {industry}（業種）, {size}（規模）, {fiscal_summary}（決算書データ・JSON）, {debt_info}（借入情報・JSON）, {monthly_data}（月次推移データ・JSON）。使用例はフォーム下部を参照してください。'


class CloudStorageSettingForm(forms.ModelForm):
    """クラウドストレージ設定フォーム"""
    class Meta:
        from .models import CloudStorageSetting
        model = CloudStorageSetting
        fields = ['storage_type']
        widgets = {
            'storage_type': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['storage_type'].choices = [
            ('', '選択してください'),
            ('google_drive', 'Google Drive'),
            ('box', 'Box'),
            ('dropbox', 'Dropbox'),
            ('onedrive', 'OneDrive'),
        ]


class FirmMemberInviteForm(forms.Form):
    """Firmメンバー招待フォーム"""
    email = forms.EmailField(
        label='メールアドレス',
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        help_text='招待するユーザーのメールアドレスを入力してください。'
    )
    is_owner = forms.BooleanField(
        label='オーナー権限を付与',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='チェックすると、オーナー権限を付与します。'
    )


class MeetingMinutesAIGenerateForm(forms.Form):
    """AI議事録生成フォーム"""
    
    MEETING_TYPE_CHOICES = [
        ('shareholders_meeting', '株主総会'),
        ('board_of_directors', '取締役会'),
        ('management_committee', '経営会議 / 執行役員会'),
    ]
    
    MEETING_CATEGORY_CHOICES = [
        ('regular', '定時'),
        ('extraordinary', '臨時'),
    ]
    
    # 株主総会向け議題
    SHAREHOLDERS_AGENDA_CHOICES = [
        ('financial_approval', '決算承認: 計算書類および事業報告の承認'),
        ('officer_election', '役員選任: 取締役・監査役の選任（任期満了や増員）'),
        ('surplus_disposition', '剰余金処分: 配当の決定'),
        ('articles_amendment', '定款変更: 商号変更や事業目的の追加'),
    ]
    
    # 取締役会向け議題
    BOARD_AGENDA_CHOICES = [
        ('representative_director', '代表取締役の選定: 役職の決定'),
        ('asset_disposition', '重要な財産の処分: 資産の売却や多額の借入'),
        ('meeting_convening', '招集決定: 株主総会の開催日時・場所の決定'),
        ('new_shares', '新株発行: 資金調達（増資）に関する決定'),
    ]
    
    # 経営会議向け議題（汎用的な議題）
    MANAGEMENT_AGENDA_CHOICES = [
        ('business_strategy', '事業戦略の検討'),
        ('budget_approval', '予算の承認'),
        ('organization_change', '組織変更の決定'),
        ('other', 'その他'),
    ]
    
    meeting_type = forms.ChoiceField(
        label='会議体',
        choices=MEETING_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='議事録を作成する会議の種類を選択してください。'
    )
    
    meeting_category = forms.ChoiceField(
        label='開催種別',
        choices=MEETING_CATEGORY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='定例で行われるものか、臨時で開催されるものかを選択してください。'
    )
    
    agenda = forms.ChoiceField(
        label='主な議題（決議事項）',
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='会議の主な議題を選択してください。'
    )
    
    additional_info = forms.CharField(
        label='追加情報（任意）',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': '会社名、開催日、その他の詳細情報があれば入力してください。'
        }),
        help_text='会社名、開催日、その他の詳細情報があれば入力してください。'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 初期状態では株主総会の議題を設定
        self.fields['agenda'].choices = self.SHAREHOLDERS_AGENDA_CHOICES
        
        # POSTデータがある場合、会議体に応じて議題の選択肢を更新
        if self.data:
            meeting_type = self.data.get('meeting_type')
            if meeting_type:
                if meeting_type == 'shareholders_meeting':
                    self.fields['agenda'].choices = self.SHAREHOLDERS_AGENDA_CHOICES
                elif meeting_type == 'board_of_directors':
                    self.fields['agenda'].choices = self.BOARD_AGENDA_CHOICES
                elif meeting_type == 'management_committee':
                    self.fields['agenda'].choices = self.MANAGEMENT_AGENDA_CHOICES
    
    def clean(self):
        cleaned_data = super().clean()
        meeting_type = cleaned_data.get('meeting_type')
        agenda = cleaned_data.get('agenda')
        
        # 会議体に応じて議題の選択肢を更新
        if meeting_type == 'shareholders_meeting':
            self.fields['agenda'].choices = self.SHAREHOLDERS_AGENDA_CHOICES
            # 選択された議題が有効かチェック
            valid_choices = [choice[0] for choice in self.SHAREHOLDERS_AGENDA_CHOICES]
            if agenda and agenda not in valid_choices:
                raise forms.ValidationError({
                    'agenda': f'正しく選択してください。{agenda} は候補にありません。'
                })
        elif meeting_type == 'board_of_directors':
            self.fields['agenda'].choices = self.BOARD_AGENDA_CHOICES
            valid_choices = [choice[0] for choice in self.BOARD_AGENDA_CHOICES]
            if agenda and agenda not in valid_choices:
                raise forms.ValidationError({
                    'agenda': f'正しく選択してください。{agenda} は候補にありません。'
                })
        elif meeting_type == 'management_committee':
            self.fields['agenda'].choices = self.MANAGEMENT_AGENDA_CHOICES
            valid_choices = [choice[0] for choice in self.MANAGEMENT_AGENDA_CHOICES]
            if agenda and agenda not in valid_choices:
                raise forms.ValidationError({
                    'agenda': f'正しく選択してください。{agenda} は候補にありません。'
                })
        
        return cleaned_data
