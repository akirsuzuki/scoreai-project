from django.urls import path
# views/__init__.pyから新しいビューをインポート
from .views import (
    IndexView,
    LoginView,
    ScoreLogoutView,
    UserCreateView,
    UserProfileView,
    UserProfileUpdateView,
    CustomPasswordChangeView,
    CustomPasswordChangeDoneView,
    CustomPasswordResetView,
    CustomPasswordResetDoneView,
    CustomPasswordResetConfirmView,
    CustomPasswordResetCompleteView,
    CompanyDetailView,
    CompanyUpdateView,
    CompanyMemberListView,
    CompanyMemberInviteView,
    CompanyMemberDeleteView,
    CompanyInvitationCancelView,
    select_company,
    load_industry_subclassifications,
    ImportFiscalSummaryFromOcrView,
)
from .views.auth_views import (
    EmailVerificationSentView,
    EmailVerifyView,
    WelcomeView,
)
from .views.ai_consultation_views import (
    AIConsultationCenterView,
    AIConsultationView,
    AIConsultationAPIView,
    AIConsultationHistoryView,
)
from .views.industry_consultation_views import (
    IndustryConsultationCenterView,
    IndustryClassificationDetailView,
    IzakayaPlanCreateView,
    IzakayaPlanUpdateView,
    IzakayaPlanPreviewView,
    IzakayaPlanListView,
    IzakayaPlanDeleteView,
)
from .views.industry_consultation_settings_views import (
    IndustryCategoryListView,
    IndustryCategoryCreateView,
    IndustryCategoryUpdateView,
    IndustryCategoryDeleteView,
    IndustryConsultationTypeListView,
    IndustryConsultationTypeCreateView,
    IndustryConsultationTypeUpdateView,
    IndustryConsultationTypeDeleteView,
)
from .views.izakaya_plan_export_views import IzakayaPlanExportView
from .views.fiscal_ai_diagnosis_views import (
    FiscalAIDiagnosisGenerateView,
    FiscalAIDiagnosisChatView,
    FiscalAIDiagnosisDownloadView,
)
from .views.about_links_views import AboutLinksView
from .views.ai_script_views import (
    AdminAIScriptListView,
    AdminAIScriptCreateView,
    AdminAIScriptUpdateView,
    AdminAIScriptDeleteView,
    UserAIScriptListView,
    UserAIScriptCreateView,
    UserAIScriptUpdateView,
    UserAIScriptDeleteView,
)
from .views.storage_views import (
    CloudStorageSettingView,
    GoogleDriveOAuthInitView,
    GoogleDriveOAuthCallbackView,
    BoxOAuthInitView,
    BoxOAuthCallbackView,
    CloudStorageDisconnectView,
    CloudStorageTestConnectionView,
)
from .views.storage_file_views import (
    StorageFileListView,
    StorageFileProcessView,
)
from .views.blog_views import (
    AnnouncementListView,
    AnnouncementDetailView,
)
from .views.plan_views import (
    PlanListView,
    PlanDetailView,
    PlanDetailPublicView,
    SubscriptionManageView,
    SubscriptionCreateView,
    SubscriptionSuccessView,
    SubscriptionCancelView,
)
from .views.usage_report_views import (
    UsageReportView,
    UsageReportExportView,
    CompanyUsageReportView,
    MonthlyCompanyUsageAPIView,
)
from .views.billing_views import (
    BillingHistoryView,
    BillingInvoiceDetailView,
    PaymentMethodUpdateView,
    PaymentMethodSuccessView,
)
from .views.subscription_history_views import (
    SubscriptionHistoryView,
)
from .views.firm_settings_views import (
    FirmSettingsView,
)
from .views.firm_registration_views import (
    FirmRegistrationView,
    FirmRegistrationSuccessView,
    FirmCompanyRegistrationView,
    CompanyRegistrationSuccessView,
)
from .views.notification_views import (
    NotificationListView,
    NotificationDetailView,
    NotificationMarkReadView,
    NotificationMarkAllReadView,
)
from .views.meeting_minutes_ai_views import (
    MeetingMinutesAIGenerateView,
    MeetingMinutesAIResultView,
    MeetingMinutesAISaveView,
)
from .views.firm_member_views import (
    FirmMemberListView,
    FirmMemberInviteView,
    FirmMemberUpdateView,
    FirmInvitationCancelView,
)
from .views.assigned_clients_views import (
    AssignedClientsListView,
)
from .views.firm_company_limit_views import (
    FirmCompanyLimitUpdateView,
)
from .views.budget_views import (
    FiscalSummary_YearBudgetCreateView,
    FiscalSummary_YearBudgetUpdateView,
    FiscalSummary_MonthBudgetCreateView,
    FiscalSummary_MonthBudgetUpdateView,
    BudgetSuggestView,
    BudgetSuggest_MonthView,
    BudgetVsActualComparisonView,
    BudgetVsActualYearlyComparisonView,
    BudgetVsActualMonthlyComparisonView,
    BudgetAnalysisView,
)
from .views.stripe_webhook_views import StripeWebhookView
from .views.export_views import (
    export_debts,
    export_fiscal_summary_year,
)
from .views import (
    # views.pyから再エクスポートされた関数
    add_client,
    remove_client,
    distribute_limits_evenly,
    download_fiscal_summary_year_csv,
    download_fiscal_summary_month_csv,
    download_financial_institutions_csv,
    # views.pyから再エクスポートされたビュー
    FiscalSummary_YearCreateView,
    FiscalSummary_YearUpdateView,
    FiscalSummary_YearDeleteView,
    FiscalSummary_YearDetailView,
    LatestFiscalSummaryYearDetailView,
    FiscalSummary_YearListView,
    ImportFiscalSummary_Year,
    ImportFiscalSummary_Year_FromMoneyforward,
    FiscalSummary_MonthCreateView,
    FiscalSummary_MonthUpdateView,
    FiscalSummary_MonthDeleteView,
    FiscalSummary_MonthDetailView,
    FiscalSummary_MonthListView,
    LatestMonthlyPLView,
    ImportFiscalSummary_Month,
    ImportFiscalSummary_Month_FromMoneyforward,
    DebtCreateView,
    DebtsOverviewView,
    DebtsAllListView,
    DebtsByBankListView,
    DebtsByBankDetailListView,
    DebtsBySecuredTypeListView,
    DebtsBySecuredTypeDetailListView,
    DebtsArchivedListView,
    DebtDetailView,
    DebtUpdateView,
    DebtDeleteView,
    Stakeholder_nameCreateView,
    Stakeholder_nameUpdateView,
    Stakeholder_nameListView,
    Stakeholder_nameDeleteView,
    Stakeholder_nameDetailView,
    StockEventCreateView,
    StockEventUpdateView,
    StockEventListView,
    StockEventDetailView,
    StockEventDeleteView,
    StockEventLineCreateView,
    StockEventLineUpdateView,
    MeetingMinutesCreateView,
    MeetingMinutesUpdateView,
    MeetingMinutesListView,
    MeetingMinutesDetailView,
    MeetingMinutesDeleteView,
    MeetingMinutesImportView,
    MeetingMinutesAIGenerateView,
    MeetingMinutesAIResultView,
    MeetingMinutesAISaveView,
    AboutView,
    NewsListView,
    CompanyProfileView,
    HelpView,
    HelpDetailView,
    ManualListView,
    ManualDetailView,
    FAQView,
    TermsOfServiceView,
    PrivacyPolicyView,
    LegalNoticeView,
    SecurityPolicyView,
    ClientsList,
    ImportFinancialInstitutionView,
    SampleView,
    ImportIndustryClassificationView,
    IndustryClassificationListView,
    ImportIndustrySubClassificationView,
    IndustrySubClassificationListView,
    ImportIndustryBenchmarkView,
    IndustryBenchmarkListView,
)


urlpatterns = [
    path("", IndexView.as_view(), name="index"),
    path('user_create/', UserCreateView.as_view(), name='user_create'),
    path('email/verification-sent/', EmailVerificationSentView.as_view(), name='email_verification_sent'),
    path('email/verify/<str:token>/', EmailVerifyView.as_view(), name='email_verify'),
    path('welcome/', WelcomeView.as_view(), name='welcome'),
    path("login/", LoginView.as_view(), name="login"),
    path('logout/', ScoreLogoutView.as_view(), name='logout'),
    # Firm登録
    path('firm/register/', FirmRegistrationView.as_view(), name='firm_register'),
    path('firm/register/success/', FirmRegistrationSuccessView.as_view(), name='firm_registration_success'),
    # Company登録（Firm配下）
    path('firm/company/register/', FirmCompanyRegistrationView.as_view(), name='firm_company_register'),
    path('company/register/success/<str:company_id>/', CompanyRegistrationSuccessView.as_view(), name='company_registration_success'),
    path('user_profile/', UserProfileView.as_view(), name='user_profile'),
    path('user_profile_update/', UserProfileUpdateView.as_view(), name='user_profile_update'),
    # パスワード変更（ログイン済みユーザー用）
    path('password_change/', CustomPasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', CustomPasswordChangeDoneView.as_view(), name='password_change_done'),
    # パスワードリセット（ログイン不要）
    path('password_reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password_reset/confirm/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password_reset/complete/', CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('select_company/<str:this_company>/', select_company, name='select_company'),
    path('add_client/<str:client_id>/', add_client, name='add_client'),
    path('remove_client/<str:client_id>/', remove_client, name='remove_client'),
    path('company/<str:id>/', CompanyDetailView.as_view(), name='company_detail'),
    path('company/<str:company_id>/members/', CompanyMemberListView.as_view(), name='company_member_list'),
    path('company/<str:company_id>/members/invite/', CompanyMemberInviteView.as_view(), name='company_member_invite'),
    path('company/<str:company_id>/members/<str:member_id>/delete/', CompanyMemberDeleteView.as_view(), name='company_member_delete'),
    path('company/<str:company_id>/invitations/<str:invitation_id>/cancel/', CompanyInvitationCancelView.as_view(), name='company_invitation_cancel'),
    path('company/<str:id>/update/', CompanyUpdateView.as_view(), name='company_update'),
    path('ajax/load-industry-subclassifications/', load_industry_subclassifications, name='ajax_load_industry_subclassifications'),
    path('select_company/<str:this_company>/', select_company, name='select_company'),
    path('add_client/<str:client_id>/', add_client, name='add_client'),
    path('remove_client/<str:client_id>/', remove_client, name='remove_client'),
    path('import_industry_benchmark/', ImportIndustryBenchmarkView.as_view(), name='import_industry_benchmark'),
    path('industry_benchmark_list/', IndustryBenchmarkListView.as_view(), name='industry_benchmark_list'),
    path('fiscal_summary_year/', FiscalSummary_YearListView.as_view(), name='fiscal_summary_year_list'),
    path('fiscal_summary_year/create/', FiscalSummary_YearCreateView.as_view(), name='fiscal_summary_year_create'),
    path('fiscal_summary_year/<str:pk>/update/', FiscalSummary_YearUpdateView.as_view(), name='fiscal_summary_year_update'),
    path('fiscal_summary_year/<str:pk>/detail/', FiscalSummary_YearDetailView.as_view(), name='fiscal_summary_year_detail'),
    path('fiscal-summary-year/latest/', LatestFiscalSummaryYearDetailView.as_view(), name='latest_fiscal_summary_year_detail'),
    # AI診断レポート
    path('fiscal_summary_year/<str:fiscal_summary_year_id>/ai-diagnosis/generate/', FiscalAIDiagnosisGenerateView.as_view(), name='fiscal_ai_diagnosis_generate'),
    path('fiscal_summary_year/<str:fiscal_summary_year_id>/ai-diagnosis/chat/', FiscalAIDiagnosisChatView.as_view(), name='fiscal_ai_diagnosis_chat'),
    path('fiscal_summary_year/<str:fiscal_summary_year_id>/ai-diagnosis/download/<str:format_type>/', FiscalAIDiagnosisDownloadView.as_view(), name='fiscal_ai_diagnosis_download'),
    path('fiscal_summary_year/<str:pk>/delete/', FiscalSummary_YearDeleteView.as_view(), name='fiscal_summary_year_delete'),
    # 予算管理
    path('fiscal_summary_year/budget/create/', FiscalSummary_YearBudgetCreateView.as_view(), name='fiscal_summary_year_budget_create'),
    path('fiscal_summary_year/budget/<str:pk>/update/', FiscalSummary_YearBudgetUpdateView.as_view(), name='fiscal_summary_year_budget_update'),
    path('fiscal_summary_month/budget/create/', FiscalSummary_MonthBudgetCreateView.as_view(), name='fiscal_summary_month_budget_create'),
    path('fiscal_summary_month/budget/<str:pk>/update/', FiscalSummary_MonthBudgetUpdateView.as_view(), name='fiscal_summary_month_budget_update'),
    path('budget/suggest/', BudgetSuggestView.as_view(), name='budget_suggest'),
    path('budget/suggest-month/', BudgetSuggest_MonthView.as_view(), name='budget_suggest_month'),
    path('budget/vs-actual/', BudgetVsActualComparisonView.as_view(), name='budget_vs_actual_comparison'),
    path('budget/vs-actual-yearly/', BudgetVsActualYearlyComparisonView.as_view(), name='budget_vs_actual_yearly'),
    path('budget/vs-actual-monthly/', BudgetVsActualMonthlyComparisonView.as_view(), name='budget_vs_actual_monthly'),
    path('budget/analysis/', BudgetAnalysisView.as_view(), name='budget_analysis'),
    path('fiscal_summary_month/', FiscalSummary_MonthListView.as_view(), name='fiscal_summary_month_list'),
    path('monthly-pl/single-year/', LatestMonthlyPLView.as_view(), name='latest_monthly_pl'),
    path('fiscal_summary_month/create/', FiscalSummary_MonthCreateView.as_view(), name='fiscal_summary_month_create'),
    path('fiscal_summary_month/<str:pk>/update/', FiscalSummary_MonthUpdateView.as_view(), name='fiscal_summary_month_update'),
    path('fiscal_summary_month/<str:pk>/detail/', FiscalSummary_MonthDetailView.as_view(), name='fiscal_summary_month_detail'),
    path('fiscal_summary_month/<str:pk>/delete/', FiscalSummary_MonthDeleteView.as_view(), name='fiscal_summary_month_delete'),
    # path('fiscal_summary_year/<int:pk>/csv_download/', download_fiscal_summary_year_csv, name='download_fiscal_summary_year_csv'),
    path('download_fiscal_summary_year_csv/<str:param>/', download_fiscal_summary_year_csv, name='download_fiscal_summary_year_csv_param'),
    path('fiscal_summary_year/export/<str:format_type>/', export_fiscal_summary_year, name='export_fiscal_summary_year'),
    path('fiscal_summary_year/<str:year_id>/export/<str:format_type>/', export_fiscal_summary_year, name='export_fiscal_summary_year_detail'),
    path('download_fiscal_summary_month_csv/<str:param>/', download_fiscal_summary_month_csv, name='download_fiscal_summary_month_csv_param'),
    path('import_fiscal_summary_month/', ImportFiscalSummary_Month.as_view(), name='import_fiscal_summary_month'),
    path('import_fiscal_summary_month_MF/', ImportFiscalSummary_Month_FromMoneyforward.as_view(), name='import_fiscal_summary_month_MF'),
    path('import_fiscal_summary_year/', ImportFiscalSummary_Year.as_view(), name='import_fiscal_summary_year'),
    path('import_fiscal_summary_year_MF/', ImportFiscalSummary_Year_FromMoneyforward.as_view(), name='import_fiscal_summary_year_MF'),
    path('import_fiscal_summary_ocr/', ImportFiscalSummaryFromOcrView.as_view(), name='import_fiscal_summary_ocr'),
    # 追加
    path('get-monthly-totals/', FiscalSummary_YearCreateView.as_view(http_method_names=['get']), name='get_monthly_totals'),
    path('debt/create/', DebtCreateView.as_view(), name='debt_create'),
    path('debts_overview/', DebtsOverviewView.as_view(), name='debts_overview'),
    path('debts_all/', DebtsAllListView.as_view(), name='debts_all'),
    path('debts_all/export/<str:format_type>/', export_debts, name='export_debts'),
    path('debts_byBank/', DebtsByBankListView.as_view(), name='debts_byBank'),
    path('debts_byBank/<str:financial_institution_id>/', DebtsByBankDetailListView.as_view(), name='debts_byBank_detail'),
    path('debts_bySecuredType/', DebtsBySecuredTypeListView.as_view(), name='debts_bySecuredType'),
    path('debts_bySecuredType/<str:secured_type_id>/', DebtsBySecuredTypeDetailListView.as_view(), name='debts_bySecuredType_detail'),
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
    path('stockevent/<int:pk>/', StockEventDetailView.as_view(), name='stock_event_detail'),
    path('stockevent/<int:stock_event_pk>/line/add/', StockEventLineCreateView.as_view(), name='stockeventline_create'),
    path('stockeventline/<int:pk>/edit/', StockEventLineUpdateView.as_view(), name='stockeventline_update'),
    path('meeting_minutes/create/', MeetingMinutesCreateView.as_view(), name='meeting_minutes_create'),
    path('meeting_minutes/import/', MeetingMinutesImportView.as_view(), name='meeting_minutes_import'),
    path('meeting_minutes/<str:company_id>/<str:pk>/update/', MeetingMinutesUpdateView.as_view(), name='meeting_minutes_update'),
    path('meeting_minutes/<str:company_id>/<str:pk>/delete/', MeetingMinutesDeleteView.as_view(), name='meeting_minutes_delete'),
    
    # AI議事録生成
    path('meeting_minutes/ai/generate/', MeetingMinutesAIGenerateView.as_view(), name='meeting_minutes_ai_generate'),
    path('meeting_minutes/ai/result/', MeetingMinutesAIResultView.as_view(), name='meeting_minutes_ai_result'),
    path('meeting_minutes/ai/save/', MeetingMinutesAISaveView.as_view(), name='meeting_minutes_ai_save'),
    path('meeting_minutes_list/', MeetingMinutesListView.as_view(), name='meeting_minutes_list'),
    path('meeting_minutes/<str:company_id>/<str:pk>/', MeetingMinutesDetailView.as_view(), name='meeting_minutes_detail'),
    path('about/', AboutView.as_view(), name='about'),
    path('about-links/', AboutLinksView.as_view(), name='about_links'),
    path('news_list/', NewsListView.as_view(), name='news_list'),
    path('company_profile/', CompanyProfileView.as_view(), name='company_profile'),
    path('help/', HelpView.as_view(), name='help'),
    path('help/<str:pk>/', HelpDetailView.as_view(), name='help_detail'),
    path('manual/', ManualListView.as_view(), name='manual_list'),
    path('manual/<str:pk>/', ManualDetailView.as_view(), name='manual_detail'),
    path('faq/', FAQView.as_view(), name='faq'),
    path('support/plans/<str:plan_id>/', PlanDetailPublicView.as_view(), name='plan_detail_public'),
    path('terms_of_service/', TermsOfServiceView.as_view(), name='terms_of_service'),
    path('privacy_policy/', PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('legal_notice/', LegalNoticeView.as_view(), name='legal_notice'),
    path('security_policy/', SecurityPolicyView.as_view(), name='security_policy'),
    path('firm_clientslist/', ClientsList.as_view(), name='firm_clientslist'),
    path('assigned-clients/', AssignedClientsListView.as_view(), name='assigned_clients_list'),
    path('firm/<str:firm_id>/company/<str:company_id>/limit/', FirmCompanyLimitUpdateView.as_view(), name='firm_company_limit_update'),
    path('firm/<str:firm_id>/distribute-limits-evenly/<str:limit_type>/', distribute_limits_evenly, name='distribute_limits_evenly'),
    path('import-financial-institution/', ImportFinancialInstitutionView.as_view(), name='import_financial_institution'),
    path('download/financial_institutions/', download_financial_institutions_csv, name='download_financial_institutions_csv'),
    path('sample/', SampleView.as_view(), name='sample'),
    path('import_industry_classification/', ImportIndustryClassificationView.as_view(), name='import_industry_classification'),
    path('industry_classification_list/', IndustryClassificationListView.as_view(), name='industry_classification_list'),
    path('import_industry_subclassification/', ImportIndustrySubClassificationView.as_view(), name='import_industry_subclassification'),
    path('industry_subclassification_list/', IndustrySubClassificationListView.as_view(), name='industry_subclassification_list'),
    # AI相談関連
    path('ai-consultation/', AIConsultationCenterView.as_view(), name='ai_consultation_center'),
    path('ai-consultation/history/', AIConsultationHistoryView.as_view(), name='ai_consultation_history'),
    # 業界別相談室（より具体的なパスを先に配置）
    path('ai-consultation/industry/', IndustryConsultationCenterView.as_view(), name='industry_consultation_center'),
    path('ai-consultation/industry/<int:classification_id>/', IndustryClassificationDetailView.as_view(), name='industry_classification_detail'),
    # 業界別相談室設定（Companyのmanager用）
    # IndustryCategoryとIndustryConsultationTypeが削除されたため、設定画面は一時的に無効化
    # path('ai-consultation/industry/settings/categories/', IndustryCategoryListView.as_view(), name='industry_category_list'),
    # path('ai-consultation/industry/settings/categories/create/', IndustryCategoryCreateView.as_view(), name='industry_category_create'),
    # path('ai-consultation/industry/settings/categories/<str:pk>/update/', IndustryCategoryUpdateView.as_view(), name='industry_category_update'),
    # path('ai-consultation/industry/settings/categories/<str:pk>/delete/', IndustryCategoryDeleteView.as_view(), name='industry_category_delete'),
    # path('ai-consultation/industry/settings/consultation-types/', IndustryConsultationTypeListView.as_view(), name='industry_consultation_type_list'),
    # path('ai-consultation/industry/settings/consultation-types/create/', IndustryConsultationTypeCreateView.as_view(), name='industry_consultation_type_create'),
    # path('ai-consultation/industry/settings/consultation-types/<str:pk>/update/', IndustryConsultationTypeUpdateView.as_view(), name='industry_consultation_type_update'),
    # path('ai-consultation/industry/settings/consultation-types/<str:pk>/delete/', IndustryConsultationTypeDeleteView.as_view(), name='industry_consultation_type_delete'),
    # 居酒屋出店計画
    path('ai-consultation/industry/<int:classification_id>/izakaya-plan/create/', IzakayaPlanCreateView.as_view(), name='izakaya_plan_create'),
    path('ai-consultation/industry/izakaya-plan/<str:pk>/update/', IzakayaPlanUpdateView.as_view(), name='izakaya_plan_update'),
    path('ai-consultation/industry/izakaya-plan/<str:pk>/preview/', IzakayaPlanPreviewView.as_view(), name='izakaya_plan_preview'),
    path('ai-consultation/industry/izakaya-plan/<str:pk>/delete/', IzakayaPlanDeleteView.as_view(), name='izakaya_plan_delete'),
    path('ai-consultation/industry/izakaya-plan/<str:plan_id>/export/<str:format_type>/', IzakayaPlanExportView.as_view(), name='izakaya_plan_export'),
    path('ai-consultation/industry/izakaya-plan/list/', IzakayaPlanListView.as_view(), name='izakaya_plan_list'),
    # 汎用AI相談（より一般的なパスを後に配置）
    path('ai-consultation/<str:consultation_type_id>/api/', AIConsultationAPIView.as_view(), name='ai_consultation_api'),
    path('ai-consultation/<str:consultation_type_id>/', AIConsultationView.as_view(), name='ai_consultation'),
    # スクリプト管理（管理者用）
    path('admin/ai-scripts/', AdminAIScriptListView.as_view(), name='admin_ai_script_list'),
    path('admin/ai-scripts/create/', AdminAIScriptCreateView.as_view(), name='admin_ai_script_create'),
    path('admin/ai-scripts/<str:pk>/edit/', AdminAIScriptUpdateView.as_view(), name='admin_ai_script_edit'),
    path('admin/ai-scripts/<str:pk>/delete/', AdminAIScriptDeleteView.as_view(), name='admin_ai_script_delete'),
    # スクリプト管理（ユーザー用）
    path('settings/my-scripts/', UserAIScriptListView.as_view(), name='user_ai_script_list'),
    path('settings/my-scripts/create/', UserAIScriptCreateView.as_view(), name='user_ai_script_create'),
    path('settings/my-scripts/<str:pk>/edit/', UserAIScriptUpdateView.as_view(), name='user_ai_script_edit'),
    path('settings/my-scripts/<str:pk>/delete/', UserAIScriptDeleteView.as_view(), name='user_ai_script_delete'),
    
    # クラウドストレージ設定
    path('storage/setting/', CloudStorageSettingView.as_view(), name='storage_setting'),
    path('storage/google-drive/auth/', GoogleDriveOAuthInitView.as_view(), name='storage_google_drive_auth'),
    path('storage/google-drive/callback/', GoogleDriveOAuthCallbackView.as_view(), name='storage_google_drive_callback'),
    path('storage/box/auth/', BoxOAuthInitView.as_view(), name='storage_box_auth'),
    path('storage/box/callback/', BoxOAuthCallbackView.as_view(), name='storage_box_callback'),
    path('storage/disconnect/', CloudStorageDisconnectView.as_view(), name='storage_disconnect'),
    path('storage/test-connection/', CloudStorageTestConnectionView.as_view(), name='storage_test_connection'),
    # ストレージファイル管理
    path('storage/files/', StorageFileListView.as_view(), name='storage_file_list'),
    path('storage/files/process/', StorageFileProcessView.as_view(), name='storage_file_process'),
    
    # お知らせ（ブログ記事を表示）
    path('announcement/', AnnouncementListView.as_view(), name='announcement_list'),
    path('announcement/<int:pk>/', AnnouncementDetailView.as_view(), name='announcement_detail'),
    
    # プラン管理（より具体的なパターンを先に配置）
    path('plans/<str:firm_id>/subscription/create/<str:plan_id>/', SubscriptionCreateView.as_view(), name='subscription_create'),
    path('plans/<str:firm_id>/subscription/success/', SubscriptionSuccessView.as_view(), name='subscription_success'),
    path('plans/<str:firm_id>/subscription/cancel/', SubscriptionCancelView.as_view(), name='subscription_cancel'),
    path('plans/<str:firm_id>/subscription/', SubscriptionManageView.as_view(), name='subscription_manage'),
    path('plans/<str:firm_id>/<str:plan_id>/', PlanDetailView.as_view(), name='plan_detail'),
    path('plans/<str:firm_id>/', PlanListView.as_view(), name='plan_list'),
    # Firmメンバー管理
    path('firm/<str:firm_id>/members/', FirmMemberListView.as_view(), name='firm_member_list'),
    path('firm/<str:firm_id>/members/invite/', FirmMemberInviteView.as_view(), name='firm_member_invite'),
    path('firm/<str:firm_id>/members/<str:member_id>/update/', FirmMemberUpdateView.as_view(), name='firm_member_update'),
    path('firm/<str:firm_id>/members/<str:invitation_id>/cancel/', FirmInvitationCancelView.as_view(), name='firm_invitation_cancel'),
    
    # 利用状況レポート
    path('firm/<str:firm_id>/usage/report/', UsageReportView.as_view(), name='usage_report'),
    path('firm/<str:firm_id>/usage/report/export/', UsageReportExportView.as_view(), name='usage_report_export'),
    path('firm/<str:firm_id>/usage/report/monthly-company/', MonthlyCompanyUsageAPIView.as_view(), name='monthly_company_usage_api'),
    path('firm/<str:firm_id>/companies/<str:company_id>/usage/', CompanyUsageReportView.as_view(), name='company_usage_report'),
    
    # 請求履歴
    path('firm/<str:firm_id>/billing/history/', BillingHistoryView.as_view(), name='billing_history'),
    path('firm/<str:firm_id>/billing/invoice/<str:invoice_id>/', BillingInvoiceDetailView.as_view(), name='billing_invoice_detail'),
    path('firm/<str:firm_id>/billing/payment-method/update/', PaymentMethodUpdateView.as_view(), name='payment_method_update'),
    path('firm/<str:firm_id>/billing/payment-method/success/', PaymentMethodSuccessView.as_view(), name='payment_method_success'),
    
    # プラン変更履歴
    path('firm/<str:firm_id>/subscription/history/', SubscriptionHistoryView.as_view(), name='subscription_history'),
    
    # Firm設定管理
    path('firm/<str:firm_id>/settings/', FirmSettingsView.as_view(), name='firm_settings'),
    
    # 通知機能
    path('firm/<str:firm_id>/notifications/', NotificationListView.as_view(), name='notification_list'),
    path('firm/<str:firm_id>/notifications/mark-all-read/', NotificationMarkAllReadView.as_view(), name='notification_mark_all_read'),
    path('firm/<str:firm_id>/notifications/<str:notification_id>/mark-read/', NotificationMarkReadView.as_view(), name='notification_mark_read'),
    path('firm/<str:firm_id>/notifications/<str:notification_id>/', NotificationDetailView.as_view(), name='notification_detail'),
    # Stripe Webhook
    path('stripe/webhook/', StripeWebhookView.as_view(), name='stripe_webhook'),
]
