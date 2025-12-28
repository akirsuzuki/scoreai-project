from django.contrib import admin
from .models import (
    User,
    Company,
    UserCompany,
    Firm,
    UserFirm,
    FirmCompany,
    FinancialInstitution,
    SecuredType,
    Debt,
    MeetingMinutes,
    Blog,
    BlogCategory,
    FiscalSummary_Year,
    FiscalSummary_Month,
    Stakeholder_name,
    StockEvent,
    StockEventLine,
    IndustryClassification,
    IndustrySubClassification,
    IndustryIndicator,
    IndustryBenchmark,
    TechnicalTerm,
    Help,
    AIConsultationType,
    AIConsultationScript,
    UserAIConsultationScript,
    AIConsultationHistory,
    CloudStorageSetting,
    DocumentFolder,
    UploadedDocument,
)
from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.utils.safestring import mark_safe

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_financial_consultant', 'is_company_user', 'is_manager')
    list_display_links = ('username', 'email')
    search_fields = ('username', 'email')
    list_filter = ('is_financial_consultant', 'is_company_user', 'is_manager')

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'id')
    list_display_links = ('name',)
    ordering = ('name',)


@admin.register(UserCompany)
class UserCompanyAdmin(admin.ModelAdmin):
    list_display = ('company', 'user', 'is_selected', 'active', 'is_owner', 'as_consultant')
    list_display_links = ('company', 'user')
    search_fields = ('company__name', 'user__username', 'as_consultant')
    list_filter = ('company', 'as_consultant')
    ordering = ('company',)


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = ('company', 'financial_institution', 'principal', 'secured_type', 'remaining_months','reschedule_date')
    list_display_links = ('company',)
    search_fields = ('company__name', 'financial_institution__name')
    list_filter = ('company', 'start_date', 'issue_date')
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
    search_fields = ('firm__name','user__username')
    list_filter = ('firm__name',)
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

@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    """ブログカテゴリー管理"""
    list_display = ('name', 'slug', 'order', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('order', 'name')


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    """ブログ管理"""
    list_display = ('title', 'post_date', 'written_by', 'is_draft', 'created_at')
    list_filter = ('is_draft', 'post_date', 'categories', 'created_at')
    search_fields = ('title', 'article')
    filter_horizontal = ('categories',)
    date_hierarchy = 'post_date'
    fieldsets = (
        ('基本情報', {
            'fields': ('title', 'post_date', 'article', 'written_by', 'is_draft')
        }),
        ('カテゴリー', {
            'fields': ('categories',)
        }),
    )

admin.site.register(SecuredType)

@admin.register(MeetingMinutes)
class MeetingMinutesAdmin(admin.ModelAdmin):
    list_display = ('company', 'meeting_date', 'created_by')
    list_display_links = ('meeting_date',)
    search_fields = ('company__name', 'created_by__username')
    list_filter = ('company', 'meeting_date')
    ordering = ('meeting_date',)

@admin.register(Stakeholder_name)
class Stakeholder_nameAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'is_representative', 'is_board_member', 'is_related_person', 'is_employee', 'memo')
    list_display_links = ('name',)
    search_fields = ('name', 'company__name')
    list_filter = ('company',)
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

@admin.register(Help)
class HelpAdmin(admin.ModelAdmin):
    list_display = ('title', 'category')
    list_display_links = ('title', 'category')
    ordering = ('category', 'title')


@admin.register(AIConsultationType)
class AIConsultationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'is_active', 'order')
    list_display_links = ('name',)
    list_filter = ('is_active',)
    ordering = ('order', 'name')


@admin.register(AIConsultationScript)
class AIConsultationScriptAdmin(admin.ModelAdmin):
    list_display = ('name', 'consultation_type', 'is_default', 'is_active', 'created_by', 'updated_at')
    list_display_links = ('name',)
    list_filter = ('consultation_type', 'is_default', 'is_active')
    search_fields = ('name', 'consultation_type__name')
    ordering = ('consultation_type', 'is_default', 'name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(UserAIConsultationScript)
class UserAIConsultationScriptAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'consultation_type', 'is_default', 'is_active', 'updated_at')
    list_display_links = ('name',)
    list_filter = ('consultation_type', 'is_default', 'is_active')
    search_fields = ('name', 'user__username', 'consultation_type__name')
    ordering = ('user', 'consultation_type', 'is_default', 'name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AIConsultationHistory)
class AIConsultationHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'consultation_type', 'created_at')
    list_display_links = ('created_at',)
    list_filter = ('consultation_type', 'created_at')
    search_fields = ('user__username', 'company__name', 'consultation_type__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(CloudStorageSetting)
class CloudStorageSettingAdmin(admin.ModelAdmin):
    list_display = ('user', 'storage_type', 'is_active', 'created_at', 'updated_at')
    list_display_links = ('user',)
    list_filter = ('storage_type', 'is_active', 'created_at')
    search_fields = ('user__username', 'user__email')
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('基本情報', {
            'fields': ('user', 'storage_type', 'is_active')
        }),
        ('認証情報', {
            'fields': ('access_token', 'refresh_token', 'token_expires_at'),
            'classes': ('collapse',)
        }),
        ('フォルダ設定', {
            'fields': ('root_folder_id',)
        }),
        ('タイムスタンプ', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(DocumentFolder)
class DocumentFolderAdmin(admin.ModelAdmin):
    list_display = ('name', 'folder_type', 'subfolder_type', 'order', 'is_active')
    list_display_links = ('name',)
    list_filter = ('folder_type', 'subfolder_type', 'is_active')
    search_fields = ('name',)
    ordering = ('folder_type', 'order', 'subfolder_type')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    list_display = ('company', 'document_type', 'stored_filename', 'storage_type', 'is_ocr_processed', 'is_data_saved', 'created_at')
    list_display_links = ('stored_filename',)
    list_filter = ('document_type', 'storage_type', 'is_ocr_processed', 'is_data_saved', 'created_at')
    search_fields = ('company__name', 'stored_filename', 'original_filename', 'user__username')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'ocr_processed_at')
    fieldsets = (
        ('基本情報', {
            'fields': ('user', 'company', 'document_type', 'subfolder_type')
        }),
        ('ファイル情報', {
            'fields': ('original_filename', 'stored_filename', 'storage_type', 'file_id', 'folder_id', 'file_url', 'file_size', 'mime_type')
        }),
        ('処理状態', {
            'fields': ('is_ocr_processed', 'ocr_processed_at', 'is_data_saved', 'saved_to_model', 'saved_record_id')
        }),
        ('メタデータ', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('タイムスタンプ', {
            'fields': ('created_at', 'updated_at')
        }),
    )