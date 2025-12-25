"""
Views package for scoreai app

すべてのビューをここからエクスポートします。
"""
# Index views
from .index_views import IndexView

# Auth views
from .auth_views import (
    LoginView,
    ScoreLogoutView,
    UserCreateView,
    UserProfileView,
    UserProfileUpdateView,
)

# Company views
from .company_views import (
    CompanyDetailView,
    CompanyUpdateView,
    load_industry_subclassifications,
)

# Utils
from .utils import (
    get_finance_score,
    calculate_total_monthly_summaries,
    get_benchmark_index,
    get_last_day_of_next_month,
    get_monthly_summaries,
    get_debt_list,
    get_debt_list_byAny,
    get_debt_list_byBankAndSecuredType,
    get_YearlyFiscalSummary,
    get_yearly_summaries,
)

# Helper views
from .helper_views import select_company, chat_view

# 既存のviews.pyから直接インポート（後で分割予定）
# 注意: 循環インポートを避けるため、相対インポートを使用
from .. import views as views_module

# views.pyから必要なビューをインポート
try:
    from ..views import (
    # FiscalSummary Year
    FiscalSummary_YearCreateView,
    FiscalSummary_YearUpdateView,
    FiscalSummary_YearDeleteView,
    FiscalSummary_YearDetailView,
    LatestFiscalSummaryYearDetailView,
    FiscalSummary_YearListView,
    ImportFiscalSummary_Year,
    ImportFiscalSummary_Year_FromMoneyforward,
    download_fiscal_summary_year_csv,
    # FiscalSummary Month
    FiscalSummary_MonthCreateView,
    FiscalSummary_MonthUpdateView,
    FiscalSummary_MonthDeleteView,
    FiscalSummary_MonthDetailView,
    FiscalSummary_MonthListView,
    ImportFiscalSummary_Month,
    ImportFiscalSummary_Month_FromMoneyforward,
    download_fiscal_summary_month_csv,
    # Debt
    DebtCreateView,
    DebtDetailView,
    DebtUpdateView,
    DebtDeleteView,
    DebtsAllListView,
    DebtsByBankListView,
    DebtsBySecuredTypeListView,
    DebtsArchivedListView,
    # MeetingMinutes
    MeetingMinutesCreateView,
    MeetingMinutesUpdateView,
    MeetingMinutesListView,
    MeetingMinutesDetailView,
    MeetingMinutesDeleteView,
    # Stakeholder_name
    Stakeholder_nameCreateView,
    Stakeholder_nameUpdateView,
    Stakeholder_nameListView,
    Stakeholder_nameDeleteView,
    Stakeholder_nameDetailView,
    # StockEvent
    StockEventCreateView,
    StockEventUpdateView,
    StockEventListView,
    StockEventDetailView,
    StockEventDeleteView,
    StockEventLineCreateView,
    StockEventLineUpdateView,
    # Import
    ImportFinancialInstitutionView,
    download_financial_institutions_csv,
    ImportIndustryClassificationView,
    IndustryClassificationListView,
    ImportIndustrySubClassificationView,
    IndustrySubClassificationListView,
    ImportIndustryBenchmarkView,
    IndustryBenchmarkListView,
    # Firm
    ClientsList,
    add_client,
    remove_client,
    # Static
    AboutView,
    NewsListView,
    CompanyProfileView,
    HelpView,
    ManualView,
    TermsOfServiceView,
    PrivacyPolicyView,
    LegalNoticeView,
    SecurityPolicyView,
    SampleView,
)
except ImportError:
    # 分割が完了していない場合は空のリスト
    pass

__all__ = [
    # Index
    'IndexView',
    # Auth
    'LoginView',
    'ScoreLogoutView',
    'UserCreateView',
    'UserProfileView',
    'UserProfileUpdateView',
    # Company
    'CompanyDetailView',
    'CompanyUpdateView',
    'load_industry_subclassifications',
    # Utils
    'get_finance_score',
    'calculate_total_monthly_summaries',
    'get_benchmark_index',
    'get_last_day_of_next_month',
    'get_monthly_summaries',
    'get_debt_list',
    'get_debt_list_byAny',
    'get_debt_list_byBankAndSecuredType',
    'get_YearlyFiscalSummary',
    'get_yearly_summaries',
    # FiscalSummary Year
    'FiscalSummary_YearCreateView',
    'FiscalSummary_YearUpdateView',
    'FiscalSummary_YearDeleteView',
    'FiscalSummary_YearDetailView',
    'LatestFiscalSummaryYearDetailView',
    'FiscalSummary_YearListView',
    'ImportFiscalSummary_Year',
    'ImportFiscalSummary_Year_FromMoneyforward',
    'download_fiscal_summary_year_csv',
    # FiscalSummary Month
    'FiscalSummary_MonthCreateView',
    'FiscalSummary_MonthUpdateView',
    'FiscalSummary_MonthDeleteView',
    'FiscalSummary_MonthDetailView',
    'FiscalSummary_MonthListView',
    'ImportFiscalSummary_Month',
    'ImportFiscalSummary_Month_FromMoneyforward',
    'download_fiscal_summary_month_csv',
    # Debt
    'DebtCreateView',
    'DebtDetailView',
    'DebtUpdateView',
    'DebtDeleteView',
    'DebtsAllListView',
    'DebtsByBankListView',
    'DebtsBySecuredTypeListView',
    'DebtsArchivedListView',
    # MeetingMinutes
    'MeetingMinutesCreateView',
    'MeetingMinutesUpdateView',
    'MeetingMinutesListView',
    'MeetingMinutesDetailView',
    'MeetingMinutesDeleteView',
    # Stakeholder_name
    'Stakeholder_nameCreateView',
    'Stakeholder_nameUpdateView',
    'Stakeholder_nameListView',
    'Stakeholder_nameDeleteView',
    'Stakeholder_nameDetailView',
    # StockEvent
    'StockEventCreateView',
    'StockEventUpdateView',
    'StockEventListView',
    'StockEventDetailView',
    'StockEventDeleteView',
    'StockEventLineCreateView',
    'StockEventLineUpdateView',
    # Import
    'ImportFinancialInstitutionView',
    'download_financial_institutions_csv',
    'ImportIndustryClassificationView',
    'IndustryClassificationListView',
    'ImportIndustrySubClassificationView',
    'IndustrySubClassificationListView',
    'ImportIndustryBenchmarkView',
    'IndustryBenchmarkListView',
    # Firm
    'ClientsList',
    'add_client',
    'remove_client',
    # Static
    'AboutView',
    'NewsListView',
    'CompanyProfileView',
    'HelpView',
    'ManualView',
    'TermsOfServiceView',
    'PrivacyPolicyView',
    'LegalNoticeView',
    'SecurityPolicyView',
    'SampleView',
    # Helper functions
    'select_company',
    'chat_view',
]

