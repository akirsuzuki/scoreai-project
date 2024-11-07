from django.contrib import admin
from .models import *
from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.utils.safestring import mark_safe

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email')


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'id')
    list_display_links = ('name',)
    ordering = ('name',)


@admin.register(UserCompany)
class UserCompanyAdmin(admin.ModelAdmin):
    list_display = ('company', 'user', 'is_selected', 'active', 'is_owner')
    list_display_links = ('company', 'user')
    ordering = ('company',)


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = ('company', 'financial_institution', 'principal', 'secured_type', 'remaining_months','reschedule_date')
    list_display_links = ('company',)
    ordering = ('company',)


@admin.register(Firm)
class FirmAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner')
    list_display_links = ('name',)
    ordering = ('name',)


@admin.register(UserFirm)
class UserFirmAdmin(admin.ModelAdmin):
    list_display = ('firm', 'user', 'is_selected', 'active', 'is_owner')
    list_display_links = ('firm', 'user')
    ordering = ('firm',)


@admin.register(FirmCompany)
class FirmCompanyAdmin(admin.ModelAdmin):
    list_display = ('firm', 'company', 'active', 'start_date', 'end_date')
    list_display_links = ('firm', 'company')
    list_filter = ('active', 'start_date', 'end_date')
    search_fields = ('firm__name', 'company__name')
    ordering = ('firm', 'company')


class FiscalSummary_MonthInline(admin.TabularInline):
    model = FiscalSummary_Month
    extra = 0


@admin.register(FiscalSummary_Year)
class FiscalSummary_YearAdmin(admin.ModelAdmin):
    list_display = ('id', 'company', 'year', 'version')
    list_filter = ('year', 'company')
    search_fields = ('company__name', 'company__code', 'year')
    
    fieldsets = (
        ('基本情報', {
            'fields': ('company', 'year', 'version')
        }),
        ('BS情報', {
            'fields': (
                'cash_and_deposits', 'total_current_assets', 'total_tangible_fixed_assets',
                'total_fixed_assets', 'total_assets', 'short_term_loans_payable',
                'total_current_liabilities', 'long_term_loans_payable', 'total_liabilities',
                'capital_stock', 'retained_earnings', 'total_net_assets'
            )
        }),
        ('PL情報', {
            'fields': (
                'depreciation_expense', 'other_amortization_expense', 'directors_compensation',
                'payroll_expense', 'non_operating_amortization_expense',
                'income_taxes'
            )
        }),
        ('税務情報', {
            'fields': ('tax_loss_carryforward', 'number_of_employees_EOY', 'issued_shares_EOY')
        }),
        ('決算留意事項', {
            'fields': ('financial_statement_notes',)
        }),
        ('指標スコア', {
            'fields': ('score_sales_growth_rate', 'score_operating_profit_margin', 'score_labor_productivity', 'score_EBITDA_interest_bearing_debt_ratio', 'score_operating_working_capital_turnover_period', 'score_equity_ratio')
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # 編集時
            return ('company', 'year')
        return ()  # 新規作成時は読み取り専用フィールドなし


@admin.register(FiscalSummary_Month)
class FiscalSummary_MonthAdmin(admin.ModelAdmin):
    list_display = ('fiscal_summary_year', 'period', 'sales', 'gross_profit', 'operating_profit', 'ordinary_profit')
    list_display_links = ('fiscal_summary_year', 'period')
    list_filter = ('fiscal_summary_year__year', 'fiscal_summary_year__company', 'period')
    search_fields = ('fiscal_summary_year__company__name', 'fiscal_summary_year__year')
    ordering = ('-fiscal_summary_year__year', 'fiscal_summary_year__company', 'period')

@admin.register(FinancialInstitution)
class FinancialInstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'JBAcode', 'bank_category')
    list_filter = ('bank_category',)
    search_fields = ('name', 'short_name', 'JBAcode')
    ordering = ('name',)

    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'short_name')
        }),
        ('詳細情報', {
            'fields': ('JBAcode', 'bank_category')
        }),
    )

admin.site.register(Blog)

admin.site.register(SecuredType)

@admin.register(MeetingMinutes)
class MeetingMinutesAdmin(admin.ModelAdmin):
    list_display = ('company', 'meeting_date', 'created_by')
    list_display_links = ('meeting_date',)
    ordering = ('meeting_date',)

@admin.register(Stakeholder_name)
class Stakeholder_nameAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'is_representative', 'is_board_member', 'is_related_person', 'is_employee', 'memo')
    list_display_links = ('name',)
    ordering = ('name',)

@admin.register(StockEvent)
class StockEventAdmin(admin.ModelAdmin):
    list_display = ('fiscal_summary_year', 'name', 'event_date', 'event_type')
    list_display_links = ('fiscal_summary_year', 'name')
    ordering = ('fiscal_summary_year', 'name')

@admin.register(StockEventLine)
class StockEventLineAdmin(admin.ModelAdmin):
    list_display = ('stock_event', 'stakeholder', 'share_quantity', 'share_type', 'acquisition_price')
    list_display_links = ('stock_event', 'stakeholder')
    ordering = ('stock_event', 'stakeholder')


@admin.register(IndustryClassification)
class IndustryClassificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'memo')
    list_display_links = ('name',)
    ordering = ('name',)


@admin.register(IndustrySubClassification)
class IndustrySubClassificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'industry_classification', 'memo')
    list_display_links = ('name',)
    ordering = ('name',)

@admin.register(IndustryIndicator)
class IndustryIndicatorAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'memo')
    list_display_links = ('name',)
    ordering = ('id',)

@admin.register(IndustryBenchmark)
class IndustryBenchmarkAdmin(admin.ModelAdmin):
    list_display = ('year', 'industry_classification', 'industry_subclassification', 'company_size', 'indicator', 'median', 'standard_deviation', 'range_iv', 'range_iii', 'range_ii', 'range_i')
    list_filter = ('year', 'industry_classification', 'industry_subclassification', 'company_size')

@admin.register(TechnicalTerm)
class TechnicalTermAdmin(admin.ModelAdmin):
    list_display = ('name', 'description1', 'description2', 'description3')
    list_display_links = ('name',)
    ordering = ('name',)

