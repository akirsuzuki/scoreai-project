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

# OCR views
from .ocr_views import ImportFiscalSummaryFromOcrView

# views.pyから必要な関数とビューを再エクスポート（循環インポートを避けるため、遅延インポート）
# 注意: views.pyがviews/__init__.pyをインポートしないようにする必要がある
def _import_views_py():
    """views.pyから必要な関数とビューをインポート（遅延インポート）"""
    import sys
    import importlib.util
    from pathlib import Path
    
    # views.pyのパスを取得
    views_py_path = Path(__file__).parent.parent / 'views.py'
    
    # views.pyをモジュールとして読み込む
    spec = importlib.util.spec_from_file_location("scoreai.views_py", views_py_path)
    views_py_module = importlib.util.module_from_spec(spec)
    sys.modules["scoreai.views_py"] = views_py_module
    spec.loader.exec_module(views_py_module)
    
    return views_py_module

# 遅延インポートを実行
_views_py = _import_views_py()

# views.pyから必要な関数とビューを再エクスポート
add_client = _views_py.add_client
remove_client = _views_py.remove_client
download_fiscal_summary_year_csv = _views_py.download_fiscal_summary_year_csv
download_fiscal_summary_month_csv = _views_py.download_fiscal_summary_month_csv
download_financial_institutions_csv = _views_py.download_financial_institutions_csv

# views.pyから必要なビューを再エクスポート
FiscalSummary_YearCreateView = _views_py.FiscalSummary_YearCreateView
FiscalSummary_YearUpdateView = _views_py.FiscalSummary_YearUpdateView
FiscalSummary_YearDeleteView = _views_py.FiscalSummary_YearDeleteView
FiscalSummary_YearDetailView = _views_py.FiscalSummary_YearDetailView
LatestFiscalSummaryYearDetailView = _views_py.LatestFiscalSummaryYearDetailView
FiscalSummary_YearListView = _views_py.FiscalSummary_YearListView
ImportFiscalSummary_Year = _views_py.ImportFiscalSummary_Year
ImportFiscalSummary_Year_FromMoneyforward = _views_py.ImportFiscalSummary_Year_FromMoneyforward
FiscalSummary_MonthCreateView = _views_py.FiscalSummary_MonthCreateView
FiscalSummary_MonthUpdateView = _views_py.FiscalSummary_MonthUpdateView
FiscalSummary_MonthDeleteView = _views_py.FiscalSummary_MonthDeleteView
FiscalSummary_MonthDetailView = _views_py.FiscalSummary_MonthDetailView
FiscalSummary_MonthListView = _views_py.FiscalSummary_MonthListView
ImportFiscalSummary_Month = _views_py.ImportFiscalSummary_Month
ImportFiscalSummary_Month_FromMoneyforward = _views_py.ImportFiscalSummary_Month_FromMoneyforward
DebtCreateView = _views_py.DebtCreateView
DebtsAllListView = _views_py.DebtsAllListView
DebtsByBankListView = _views_py.DebtsByBankListView
DebtsBySecuredTypeListView = _views_py.DebtsBySecuredTypeListView
DebtsArchivedListView = _views_py.DebtsArchivedListView
DebtDetailView = _views_py.DebtDetailView
DebtUpdateView = _views_py.DebtUpdateView
DebtDeleteView = _views_py.DebtDeleteView
Stakeholder_nameCreateView = _views_py.Stakeholder_nameCreateView
Stakeholder_nameUpdateView = _views_py.Stakeholder_nameUpdateView
Stakeholder_nameListView = _views_py.Stakeholder_nameListView
Stakeholder_nameDeleteView = _views_py.Stakeholder_nameDeleteView
Stakeholder_nameDetailView = _views_py.Stakeholder_nameDetailView
StockEventCreateView = _views_py.StockEventCreateView
StockEventUpdateView = _views_py.StockEventUpdateView
StockEventListView = _views_py.StockEventListView
StockEventDetailView = _views_py.StockEventDetailView
StockEventDeleteView = _views_py.StockEventDeleteView
StockEventLineCreateView = _views_py.StockEventLineCreateView
StockEventLineUpdateView = _views_py.StockEventLineUpdateView
MeetingMinutesCreateView = _views_py.MeetingMinutesCreateView
MeetingMinutesUpdateView = _views_py.MeetingMinutesUpdateView
MeetingMinutesListView = _views_py.MeetingMinutesListView
MeetingMinutesDetailView = _views_py.MeetingMinutesDetailView
MeetingMinutesDeleteView = _views_py.MeetingMinutesDeleteView
AboutView = _views_py.AboutView
NewsListView = _views_py.NewsListView
CompanyProfileView = _views_py.CompanyProfileView
HelpView = _views_py.HelpView
ManualView = _views_py.ManualView
TermsOfServiceView = _views_py.TermsOfServiceView
PrivacyPolicyView = _views_py.PrivacyPolicyView
LegalNoticeView = _views_py.LegalNoticeView
SecurityPolicyView = _views_py.SecurityPolicyView
ClientsList = _views_py.ClientsList
ImportFinancialInstitutionView = _views_py.ImportFinancialInstitutionView
SampleView = _views_py.SampleView
ImportIndustryClassificationView = _views_py.ImportIndustryClassificationView
IndustryClassificationListView = _views_py.IndustryClassificationListView
ImportIndustrySubClassificationView = _views_py.ImportIndustrySubClassificationView
IndustrySubClassificationListView = _views_py.IndustrySubClassificationListView
ImportIndustryBenchmarkView = _views_py.ImportIndustryBenchmarkView
IndustryBenchmarkListView = _views_py.IndustryBenchmarkListView

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
    # OCR
    'ImportFiscalSummaryFromOcrView',
]

