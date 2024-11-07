from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
from .models import *
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
        fields = ['name', 'fiscal_month', 'industry_classification', 'industry_subclassification', 'company_size']
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
        }
        labels = {
            'name': '会社名',
            'fiscal_month': '決算月',
            'industry_classification': '業種分類',
            'industry_subclassification': '業種小分類',
            'company_size': '企業規模',
        }


    def __init__(self, *args, **kwargs):
        super(CompanyForm, self).__init__(*args, **kwargs)
        # 必須項目を指定
        self.fields['name'].required = True
        self.fields['fiscal_month'].required = True
        self.fields['industry_classification'].required = True
        self.fields['industry_subclassification'].required = True
        self.fields['company_size'].required = True

        self.fields['industry_classification'].queryset = IndustryClassification.objects.all()
        self.fields['industry_subclassification'].queryset = IndustrySubClassification.objects.none()

        if 'industry_classification' in self.data:
            try:
                industry_classification_id = int(self.data.get('industry_classification'))
                self.fields['industry_subclassification'].queryset = IndustrySubClassification.objects.filter(industry_classification_id=industry_classification_id).order_by('name')
            except (ValueError, TypeError):
                pass  # invalid input; empty queryset
        elif self.instance.pk and self.instance.industry_classification:
            industry_classification = self.instance.industry_classification
            self.fields['industry_subclassification'].queryset = IndustrySubClassification.objects.filter(industry_classification=industry_classification).order_by('name')
            self.fields['industry_subclassification'].initial = self.instance.industry_subclassification


class IndustryBenchmarkImportForm(forms.Form):
    csv_file = forms.FileField(label='CSVファイルを選択してください')


class FiscalSummary_YearForm(forms.ModelForm):
    class Meta:
        model = FiscalSummary_Year
        exclude = ['id', 'company', 'version', 'score_sales_growth_rate', 'score_operating_profit_margin', 'score_labor_productivity', 'score_EBITDA_interest_bearing_debt_ratio', 'score_operating_working_capital_turnover_period', 'score_equity_ratio']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        # インスタンスが存在する場合（更新の場合）のみ、yearフィールドを読み取り専用にする
        if self.instance.pk:
            self.fields['year'].widget.attrs['readonly'] = True

        if 'financial_statement_notes' in self.fields:
            self.fields['financial_statement_notes'].widget.attrs['rows'] = 3


class FiscalSummary_MonthForm(forms.ModelForm):
    class Meta:
        model = FiscalSummary_Month
        fields = ['fiscal_summary_year', 'period', 'sales', 'gross_profit', 'operating_profit', 'ordinary_profit']
        widgets = {
            'fiscal_summary_year': forms.Select(attrs={'class': 'form-control', 'id': 'FiscalSummary_Year'}),
            'period': forms.NumberInput(attrs={
                'class': 'form-control',
                    'min': 1,
                    'max': 13,
                    'placeholder': '1-13'
                }),
            'sales': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'gross_profit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'operating_profit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ordinary_profit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
        labels = {
            'fiscal_summary_year': '年度',
            'period': '月度',
            'sales': '売上高（千円）',
            'gross_profit': '粗利益（千円）',
            'operating_profit': '営業利益（千円）',
            'ordinary_profit': '経常利益（千円）',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Set the initial value to the existing fiscal_summary_year
            self.fields['fiscal_summary_year'].initial = self.instance.fiscal_summary_year
            # Make the field readonly to prevent changes
            self.fields['fiscal_summary_year'].widget.attrs['readonly'] = True
            # Optionally, add a hidden input to retain the value during form submission
            self.fields['fiscal_summary_year'].widget = forms.HiddenInput()
    
    def clean_fiscal_summary_year(self):
        if self.instance.pk:
            # Ensure the original value is maintained
            return self.instance.fiscal_summary_year
        return self.cleaned_data['fiscal_summary_year']

    def clean(self):
        cleaned_data = super().clean()
        fiscal_summary_year = self.cleaned_data.get('fiscal_summary_year')
        period = cleaned_data.get('period')

        if fiscal_summary_year and period:
            existing = FiscalSummary_Month.objects.filter(
                fiscal_summary_year=fiscal_summary_year, 
                period=period
            )
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError("この年度と月度の組み合わせは既に存在します。")

        return cleaned_data

class DebtForm(forms.ModelForm):
    issue_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label='実行日')
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label='返済開始')
    reschedule_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label='リスケ日', required=False)
    class Meta:
        model = Debt
        fields = ['financial_institution', 'principal', 'issue_date', 'start_date', 'interest_rate', 'monthly_repayment', 'secured_type', 'adjusted_amount_first', 'adjusted_amount_last','is_rescheduled', 'reschedule_date', 'reschedule_balance', 'memo_short', 'memo_long', 'is_nodisplay']
        widgets = {
            'financial_institution': Select2Widget,
            'is_rescheduled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_nodisplay': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
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
        fields = ['name', 'is_representative', 'is_board_member', 'is_related_person', 'is_employee', 'memo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_representative': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_board_member': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_related_person': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_employee': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'memo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'name': '株主名',
            'is_representative': '代表取締役',
            'is_board_member': '取締役',
            'is_related_person': '代表者の家族',
            'is_employee': '従業員',
            'memo': '備考',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class StockEventForm(forms.ModelForm):
    class Meta:
        model = StockEvent
        fields = ['fiscal_summary_year', 'event_date', 'event_type', 'memo']
        widgets = {
            'fiscal_summary_year': forms.Select(attrs={'class': 'form-control'}),
            'event_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
        labels = {
            'fiscal_summary_year': '年度',
            'event_date': '発行日',
            'event_type': '発行種別',
            'memo': '備考',
        }


class StockEventLineForm(forms.ModelForm):
    class Meta:
        model = StockEventLine
        fields = ['stakeholder', 'share_quantity', 'share_type', 'acquisition_price', 'memo']

##########################################################################
###                   CSVアップロード機能                                ###
##########################################################################

class CsvUploadForm(forms.Form):
    csv_file = forms.FileField(label='Select a CSV file')



##########################################################################
###                    検証中 OPEN AI 財務アドバイス機能                    ###
##########################################################################

# class ChatForm(forms.Form):
#     message = forms.CharField(label='Message', widget=forms.Textarea(attrs={'rows': 3, 'cols': 40}))

class ChatForm(forms.Form):
    message = forms.CharField(
        label='相談内容', 
        widget=forms.Textarea(attrs={
            'rows': 3, 
            'cols': 40,
            'class': 'form-control'  # form-control クラスを追加
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'


class MeetingMinutesForm(forms.ModelForm):
    class Meta:
        model = MeetingMinutes
        fields = ['company', 'created_by', 'meeting_date', 'notes']
        widgets = {
            'meeting_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 20}),
        }

class IndustryClassificationImportForm(forms.Form):
    csv_file = forms.FileField(label='CSVファイルを選択してください')

class IndustrySubClassificationImportForm(forms.Form):
    csv_file = forms.FileField(label='CSVファイルを選択してください')