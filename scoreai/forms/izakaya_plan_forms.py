"""
居酒屋出店計画のフォーム
"""
from django import forms
from ..models import IzakayaPlan
from ..services.izakaya_plan_service import IzakayaPlanService


class IzakayaPlanForm(forms.ModelForm):
    """居酒屋出店計画のフォーム"""
    
    # カスタムフィールド（営業曜日チェックボックス）
    lunch_operating_days_widget = forms.MultipleChoiceField(
        choices=[
            ('monday', '月曜日'),
            ('tuesday', '火曜日'),
            ('wednesday', '水曜日'),
            ('thursday', '木曜日'),
            ('friday', '金曜日'),
            ('saturday', '土曜日'),
            ('sunday', '日曜日'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label='昼の営業曜日'
    )
    
    dinner_operating_days_widget = forms.MultipleChoiceField(
        choices=[
            ('monday', '月曜日'),
            ('tuesday', '火曜日'),
            ('wednesday', '水曜日'),
            ('thursday', '木曜日'),
            ('friday', '金曜日'),
            ('saturday', '土曜日'),
            ('sunday', '日曜日'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label='夜の営業曜日'
    )
    
    class Meta:
        model = IzakayaPlan
        fields = [
            # 基本情報
            'store_concept', 'number_of_seats', 'target_customer',
            # 昼の営業時間帯
            'lunch_start_time', 'lunch_end_time', 'lunch_price_per_customer',
            'lunch_cost_rate', 'lunch_monthly_coefficients',
            # 夜の営業時間帯
            'dinner_start_time', 'dinner_end_time', 'dinner_price_per_customer',
            'dinner_cost_rate', 'dinner_monthly_coefficients',
            # 投資情報
            'initial_investment', 'monthly_rent',
            # 人件費
            'number_of_staff', 'staff_monthly_salary',
            'part_time_hours_per_month', 'part_time_hourly_wage',
            # 追加経費項目
            'monthly_utilities', 'monthly_supplies', 'monthly_advertising',
            'monthly_fees', 'monthly_other_expenses',
            # その他
            'is_draft'
        ]
        widgets = {
            'store_concept': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '例: 地域密着型の居酒屋、カジュアルな雰囲気で家族連れも歓迎'
            }),
            'number_of_seats': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'target_customer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例: 20代〜40代の会社員、家族連れ'
            }),
            # 昼の営業時間帯
            'lunch_start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'lunch_end_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'lunch_price_per_customer': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 100
            }),
            'lunch_cost_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 100,
                'step': 0.1
            }),
            'lunch_monthly_coefficients': forms.HiddenInput(),  # JavaScriptで処理
            # 夜の営業時間帯
            'dinner_start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'dinner_end_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'dinner_price_per_customer': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 100
            }),
            'dinner_cost_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 100,
                'step': 0.1
            }),
            'dinner_monthly_coefficients': forms.HiddenInput(),  # JavaScriptで処理
            # 投資情報
            'initial_investment': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 10000
            }),
            'monthly_rent': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 1000
            }),
            # 人件費
            'number_of_staff': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'staff_monthly_salary': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 1000
            }),
            'part_time_hours_per_month': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'part_time_hourly_wage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 10
            }),
            # 追加経費項目
            'monthly_utilities': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 1000
            }),
            'monthly_supplies': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 1000
            }),
            'monthly_advertising': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 1000
            }),
            'monthly_fees': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 1000
            }),
            'monthly_other_expenses': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 1000
            }),
            'is_draft': forms.HiddenInput(),
        }
        labels = {
            'store_concept': '店のコンセプト',
            'number_of_seats': '席数',
            'target_customer': 'ターゲット顧客',
            'lunch_start_time': '昼の営業開始時間',
            'lunch_end_time': '昼の営業終了時間',
            'lunch_price_per_customer': '昼の客単価（円）',
            'lunch_cost_rate': '昼の原価率（%）',
            'lunch_monthly_coefficients': '昼の月毎指数',
            'dinner_start_time': '夜の営業開始時間',
            'dinner_end_time': '夜の営業終了時間',
            'dinner_price_per_customer': '夜の客単価（円）',
            'dinner_cost_rate': '夜の原価率（%）',
            'dinner_monthly_coefficients': '夜の月毎指数',
            'initial_investment': '初期投資額（円）',
            'monthly_rent': '月額家賃（円）',
            'number_of_staff': '社員人数',
            'staff_monthly_salary': '社員月給（円）',
            'part_time_hours_per_month': 'アルバイト時間数/月',
            'part_time_hourly_wage': 'アルバイト時給（円）',
            'monthly_utilities': '光熱費（円/月）',
            'monthly_supplies': '消耗品費（円/月）',
            'monthly_advertising': '広告宣伝費（円/月）',
            'monthly_fees': '手数料（円/月）',
            'monthly_other_expenses': 'その他販管費（円/月）',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 営業曜日の初期値を設定
        if self.instance.pk:
            self.fields['lunch_operating_days_widget'].initial = self.instance.lunch_operating_days or []
            self.fields['dinner_operating_days_widget'].initial = self.instance.dinner_operating_days or []
        else:
            self.fields['lunch_operating_days_widget'].initial = []
            self.fields['dinner_operating_days_widget'].initial = []
        
        # 月毎指数のデフォルト値を設定
        if not self.instance.pk or not self.instance.lunch_monthly_coefficients:
            self.initial['lunch_monthly_coefficients'] = IzakayaPlanService.get_default_monthly_coefficients()
        if not self.instance.pk or not self.instance.dinner_monthly_coefficients:
            self.initial['dinner_monthly_coefficients'] = IzakayaPlanService.get_default_monthly_coefficients()
    
    def clean(self):
        cleaned_data = super().clean()
        
        # 営業曜日をJSONFieldに変換
        lunch_days = cleaned_data.get('lunch_operating_days_widget', [])
        dinner_days = cleaned_data.get('dinner_operating_days_widget', [])
        
        cleaned_data['lunch_operating_days'] = lunch_days
        cleaned_data['dinner_operating_days'] = dinner_days
        
        # 時間の検証
        lunch_start = cleaned_data.get('lunch_start_time')
        lunch_end = cleaned_data.get('lunch_end_time')
        dinner_start = cleaned_data.get('dinner_start_time')
        dinner_end = cleaned_data.get('dinner_end_time')
        
        if lunch_start and lunch_end and lunch_start >= lunch_end:
            # 終了時間が開始時間より前の場合は翌日とみなす（エラーにしない）
            pass
        
        if dinner_start and dinner_end and dinner_start >= dinner_end:
            # 終了時間が開始時間より前の場合は翌日とみなす（エラーにしない）
            pass
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # 営業曜日を保存
        instance.lunch_operating_days = self.cleaned_data.get('lunch_operating_days_widget', [])
        instance.dinner_operating_days = self.cleaned_data.get('dinner_operating_days_widget', [])
        
        if commit:
            instance.save()
        
        return instance
