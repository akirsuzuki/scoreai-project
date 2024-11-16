from django.urls import path
from . import views
from .views import *


urlpatterns = [
    path("", IndexView.as_view(), name="index"),
    path('user_create/', UserCreateView.as_view(), name='user_create'),
    path("login/", LoginView.as_view(), name="login"),
    path('logout/', ScoreLogoutView.as_view(), name='logout'),
    path('user_profile/', UserProfileView.as_view(), name='user_profile'),
    path('user_profile_update/', UserProfileUpdateView.as_view(), name='user_profile_update'),
    path('select_company/<str:this_company>/', views.select_company, name='select_company'),
    path('company/<str:id>/', CompanyDetailView.as_view(), name='company_detail'),
    path('company/<str:id>/update/', CompanyUpdateView.as_view(), name='company_update'),
    path('ajax/load-industry-subclassifications/', views.load_industry_subclassifications, name='ajax_load_industry_subclassifications'),
    path('import_industry_benchmark/', ImportIndustryBenchmarkView.as_view(), name='import_industry_benchmark'),
    path('industry_benchmark_list/', IndustryBenchmarkListView.as_view(), name='industry_benchmark_list'),
    path('fiscal_summary_year/', FiscalSummary_YearListView.as_view(), name='fiscal_summary_year_list'),
    path('fiscal_summary_year/recent/', FiscalSummary_YearListRecentView.as_view(), name='fiscal_summary_year_list_recent'),
    path('fiscal_summary_year/create/', FiscalSummary_YearCreateView.as_view(), name='fiscal_summary_year_create'),
    path('fiscal_summary_year/<str:pk>/update/', FiscalSummary_YearUpdateView.as_view(), name='fiscal_summary_year_update'),
    path('fiscal_summary_year/<str:pk>/detail/', FiscalSummary_YearDetailView.as_view(), name='fiscal_summary_year_detail'),
    path('fiscal_summary_year/<str:pk>/delete/', FiscalSummary_YearDeleteView.as_view(), name='fiscal_summary_year_delete'),
    path('fiscal_summary_month/', FiscalSummary_MonthListView.as_view(), name='fiscal_summary_month_list'),
    path('fiscal_summary_month/create/', FiscalSummary_MonthCreateView.as_view(), name='fiscal_summary_month_create'),
    path('fiscal_summary_month/<str:pk>/update/', FiscalSummary_MonthUpdateView.as_view(), name='fiscal_summary_month_update'),
    path('fiscal_summary_month/<str:pk>/detail/', FiscalSummary_MonthDetailView.as_view(), name='fiscal_summary_month_detail'),
    path('fiscal_summary_month/<str:pk>/delete/', FiscalSummary_MonthDeleteView.as_view(), name='fiscal_summary_month_delete'),
    # path('fiscal_summary_year/<int:pk>/csv_download/', views.download_fiscal_summary_year_csv, name='download_fiscal_summary_year_csv'),
    path('download_fiscal_summary_year_csv/<str:param>/', views.download_fiscal_summary_year_csv, name='download_fiscal_summary_year_csv_param'),
    path('download_fiscal_summary_month_csv/<str:param>/', views.download_fiscal_summary_month_csv, name='download_fiscal_summary_month_csv_param'),
    path('import_fiscal_summary_month/', ImportFiscalSummary_Month.as_view(), name='import_fiscal_summary_month'),
    path('import_fiscal_summary_month_MF/', ImportFiscalSummary_Month_FromMoneyforward.as_view(), name='import_fiscal_summary_month_MF'),
    path('import_fiscal_summary_year/', ImportFiscalSummary_Year.as_view(), name='import_fiscal_summary_year'),
    # 追加
    path('get-monthly-totals/', FiscalSummary_YearCreateView.as_view(http_method_names=['get']), name='get_monthly_totals'),
    path('debt/create/', DebtCreateView.as_view(), name='debt_create'),
    path('debts_all/', DebtsAllListView.as_view(), name='debts_all'),
    path('debts_byBank/', DebtsByBankListView.as_view(), name='debts_byBank'),
    path('debts_bySecuredType/', DebtsBySecuredTypeListView.as_view(), name='debts_bySecuredType'),
    path('debts_archived/', DebtsArchivedListView.as_view(), name='debts_archived'),
    path('debt/<str:pk>/', DebtDetailView.as_view(), name='debt_detail'),
    path('debt/<str:pk>/update/', DebtUpdateView.as_view(), name='debt_update'),
    path('debt/<str:pk>/delete/', DebtDeleteView.as_view(), name='debt_delete'),
    path('stakeholder_name/create/', Stakeholder_nameCreateView.as_view(), name='stakeholder_name_create'),
    path('stakeholder_name/<str:pk>/update/', Stakeholder_nameUpdateView.as_view(), name='stakeholder_name_update'),
    path('stakeholder_name/<str:pk>/delete/', Stakeholder_nameDeleteView.as_view(), name='stakeholder_name_delete'),
    path('stakeholder_name/list/', Stakeholder_nameListView.as_view(), name='stakeholder_name_list'),
    path('stakeholder_name/<str:pk>/', Stakeholder_nameDetailView.as_view(), name='stakeholder_name_detail'),
    path('stock_event/create/', StockEventCreateView.as_view(), name='stock_event_create'),
    path('stock_event/<str:pk>/update/', StockEventUpdateView.as_view(), name='stock_event_update'),
    path('stock_event/<str:pk>/delete/', StockEventDeleteView.as_view(), name='stock_event_delete'),
    path('stock_event_list/', StockEventListView.as_view(), name='stock_event_list'),
    path('stock_event/<str:pk>/', StockEventDetailView.as_view(), name='stock_event_detail'),
    path('stockevent/<int:pk>/', views.StockEventDetailView.as_view(), name='stock_event_detail'),
    path('stockevent/<int:stock_event_pk>/line/add/', views.StockEventLineCreateView.as_view(), name='stockeventline_create'),
    path('stockeventline/<int:pk>/edit/', views.StockEventLineUpdateView.as_view(), name='stockeventline_update'),
    path('meeting_minutes/create/', MeetingMinutesCreateView.as_view(), name='meeting_minutes_create'),
    path('meeting_minutes/<str:company_id>/<str:pk>/update/', MeetingMinutesUpdateView.as_view(), name='meeting_minutes_update'),
    path('meeting_minutes/<str:company_id>/<str:pk>/delete/', MeetingMinutesDeleteView.as_view(), name='meeting_minutes_delete'),
    path('meeting_minutes_list/', MeetingMinutesListView.as_view(), name='meeting_minutes_list'),
    path('meeting_minutes/<str:company_id>/<str:pk>/', MeetingMinutesDetailView.as_view(), name='meeting_minutes_detail'),
    path('about/', AboutView.as_view(), name='about'),
    path('news_list/', NewsListView.as_view(), name='news_list'),
    path('company_profile/', CompanyProfileView.as_view(), name='company_profile'),
    path('help/', HelpView.as_view(), name='help'),
    path('manual/', ManualView.as_view(), name='manual'),
    path('terms_of_service/', TermsOfServiceView.as_view(), name='terms_of_service'),
    path('privacy_policy/', PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('legal_notice/', LegalNoticeView.as_view(), name='legal_notice'),
    path('security_policy/', SecurityPolicyView.as_view(), name='security_policy'),
    path('firm_clientslist/', ClientsList.as_view(), name='firm_clientslist'),
    path('import-financial-institution/', ImportFinancialInstitutionView.as_view(), name='import_financial_institution'),
    path('download/financial_institutions/', views.download_financial_institutions_csv, name='download_financial_institutions_csv'),
    path('sample/', SampleView.as_view(), name='sample'),
    path('import_industry_classification/', ImportIndustryClassificationView.as_view(), name='import_industry_classification'),
    path('industry_classification_list/', IndustryClassificationListView.as_view(), name='industry_classification_list'),
    path('import_industry_subclassification/', ImportIndustrySubClassificationView.as_view(), name='import_industry_subclassification'),
    path('industry_subclassification_list/', IndustrySubClassificationListView.as_view(), name='industry_subclassification_list'),
]
