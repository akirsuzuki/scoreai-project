"""
業界別相談室のAdmin設定
"""
from django.contrib import admin
from scoreai.models import IzakayaPlan


@admin.register(IzakayaPlan)
class IzakayaPlanAdmin(admin.ModelAdmin):
    list_display = ('store_concept', 'company', 'user', 'initial_investment', 'monthly_profit', 'payback_period_display', 'is_draft', 'created_at')
    list_display_links = ('store_concept',)
    list_filter = ('is_draft', 'created_at', 'company')
    search_fields = ('store_concept', 'target_customer', 'company__name', 'user__username')
    ordering = ('-created_at',)
    readonly_fields = ('monthly_revenue', 'monthly_cost', 'monthly_profit', 'payback_period_years', 'payback_period_months', 'created_at', 'updated_at')
    fieldsets = (
        ('基本情報', {
            'fields': ('company', 'user', 'industry_classification', 'store_concept', 'number_of_seats', 'target_customer')
        }),
        ('投資情報', {
            'fields': ('initial_investment', 'monthly_rent')
        }),
        ('人件費', {
            'fields': ('number_of_staff', 'staff_monthly_salary', 'part_time_hours_per_month', 'part_time_hourly_wage')
        }),
        ('売上係数', {
            'fields': ('sales_coefficients',),
            'classes': ('collapse',)
        }),
        ('計算結果', {
            'fields': ('monthly_revenue', 'monthly_cost', 'monthly_profit', 'payback_period_years', 'payback_period_months'),
            'classes': ('collapse',)
        }),
        ('その他', {
            'fields': ('is_draft', 'created_at', 'updated_at')
        }),
    )
    
    def payback_period_display(self, obj):
        """回収期間の表示"""
        if obj.payback_period_years == 999:
            return '回収不可能'
        return f'{obj.payback_period_years}年{obj.payback_period_months}ヶ月'
    payback_period_display.short_description = '回収期間'

