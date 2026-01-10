"""
居酒屋出店計画のフォーム
"""
from django import forms
from scoreai.models import IzakayaPlan
from scoreai.services.izakaya_plan_service import IzakayaPlanService


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
            'lunch_start_time', 'lunch_end_time', 'lunch_price_per_customer', 'lunch_customer_count',
            'lunch_cost_rate', 'lunch_monthly_coefficients',
            # 夜の営業時間帯
            'dinner_24hours', 'dinner_start_time', 'dinner_end_time', 'dinner_price_per_customer', 'dinner_customer_count',
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
                'type': 'time',
                'id': 'id_lunch_start_time'
            }),
            'lunch_end_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
                'id': 'id_lunch_end_time'
            }),
            'lunch_customer_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 1
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
            'dinner_24hours': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_dinner_24hours'
            }),
            'dinner_start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
                'id': 'id_dinner_start_time'
            }),
            'dinner_end_time': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'text',
                'id': 'id_dinner_end_time',
                'placeholder': '例: 28:00（翌日4時）',
                'pattern': '^([0-1]?[0-9]|2[0-8]):[0-5][0-9]$'
            }),
            'dinner_customer_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 1
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
            'lunch_customer_count': '昼の客数（人/日）',
            'lunch_cost_rate': '昼の原価率（%）',
            'lunch_monthly_coefficients': '昼の月毎指数',
            'dinner_24hours': '24時間営業',
            'dinner_start_time': '夜の営業開始時間',
            'dinner_end_time': '夜の営業終了時間',
            'dinner_price_per_customer': '夜の客単価（円）',
            'dinner_customer_count': '夜の客数（人/日）',
            'dinner_cost_rate': '夜の原価率（%）',
            'dinner_monthly_coefficients': '夜の月毎指数',
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
    
    def clean_dinner_end_time(self):
        """夜の終了時間のバリデーション（28時表記対応）"""
        end_time = self.cleaned_data.get('dinner_end_time')
        dinner_24hours = self.cleaned_data.get('dinner_24hours', False)
        
        # 24時間営業の場合は時間入力不要
        if dinner_24hours:
            return None
        
        # 文字列の場合は28時表記を処理
        if end_time:
            # "HH:MM"形式をパース
            try:
                parts = end_time.split(':')
                if len(parts) == 2:
                    hour = int(parts[0])
                    minute = int(parts[1])
                    # 28時まで許可
                    if hour < 0 or hour > 28:
                        raise forms.ValidationError('終了時間は0時から28時（翌日4時）まで入力可能です。')
                    if minute < 0 or minute >= 60:
                        raise forms.ValidationError('分は0から59まで入力可能です。')
                    # 文字列のまま保存（28時表記対応）
                    return end_time
            except (ValueError, IndexError):
                raise forms.ValidationError('時間の形式が正しくありません。例: 28:00')
        
        return end_time
    
    def clean(self):
        cleaned_data = super().clean()
        
        # 営業曜日をJSONFieldに変換
        lunch_days = cleaned_data.get('lunch_operating_days_widget', [])
        dinner_days = cleaned_data.get('dinner_operating_days_widget', [])
        
        cleaned_data['lunch_operating_days'] = lunch_days
        cleaned_data['dinner_operating_days'] = dinner_days
        
        # 24時間営業の場合は時間入力をクリア（参考情報なので必須ではない）
        dinner_24hours = cleaned_data.get('dinner_24hours', False)
        
        if dinner_24hours:
            # 24時間営業の場合は全曜日として扱う
            cleaned_data['dinner_operating_days'] = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        # 時間の検証（24時間営業でない場合のみ）
        if not lunch_24hours:
            lunch_start = cleaned_data.get('lunch_start_time')
            lunch_end = cleaned_data.get('lunch_end_time')
            if lunch_start and lunch_end and lunch_start >= lunch_end:
                # 終了時間が開始時間より前の場合は翌日とみなす（エラーにしない）
                pass
        
        if not dinner_24hours:
            dinner_start = cleaned_data.get('dinner_start_time')
            dinner_end = cleaned_data.get('dinner_end_time')
            if dinner_start and dinner_end:
                # 28時表記の場合は文字列なので、timeオブジェクトとの比較はスキップ
                if isinstance(dinner_end, time) and dinner_start >= dinner_end:
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
