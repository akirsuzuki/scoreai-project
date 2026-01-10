"""
居酒屋出店計画のフォーム
"""
from django import forms
from scoreai.models import IzakayaPlan
from scoreai.services.izakaya_plan_service import IzakayaPlanService


class IzakayaPlanForm(forms.ModelForm):
    """居酒屋出店計画のフォーム"""
    
    class Meta:
        model = IzakayaPlan
        fields = [
            'store_concept', 'number_of_seats', 'opening_hours_start', 'opening_hours_end',
            'target_customer', 'average_price_per_customer',
            'initial_investment', 'monthly_rent',
            'number_of_staff', 'staff_monthly_salary',
            'part_time_hours_per_month', 'part_time_hourly_wage',
            'sales_coefficients', 'is_draft'
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
            'opening_hours_start': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'opening_hours_end': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'target_customer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例: 20代〜40代の会社員、家族連れ'
            }),
            'average_price_per_customer': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 100
            }),
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
            'is_draft': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 売上係数のデフォルト値を設定
        if not self.instance.pk or not self.instance.sales_coefficients:
            self.initial['sales_coefficients'] = IzakayaPlanService.get_default_sales_coefficients()
    
    def clean(self):
        cleaned_data = super().clean()
        opening_hours_start = cleaned_data.get('opening_hours_start')
        opening_hours_end = cleaned_data.get('opening_hours_end')
        
        if opening_hours_start and opening_hours_end:
            if opening_hours_start >= opening_hours_end:
                # 終了時間が開始時間より前の場合は翌日とみなす（エラーにしない）
                pass
        
        return cleaned_data

