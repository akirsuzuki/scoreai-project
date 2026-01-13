from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django import forms

from django.core.mail import send_mail
from django.core.paginator import Paginator

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordChangeView, PasswordChangeDoneView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
)
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils.decorators import method_decorator

from django.urls import reverse_lazy

from django.db import transaction
from django.db.models import Max, Sum, Q, ProtectedError
from django.template.loader import render_to_string
from django.views import generic
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from itertools import groupby
from operator import itemgetter
from io import TextIOWrapper

from .mixins import SelectedCompanyMixin, TransactionMixin, ErrorHandlingMixin
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
    Manual,
)
from .forms import (
    CustomUserCreationForm,
    LoginForm,
    UserProfileUpdateForm,
    CompanyForm,
    IndustryBenchmarkImportForm,
    FiscalSummary_YearForm,
    FiscalSummary_MonthForm,
    MoneyForwardCsvUploadForm_Month,
    MoneyForwardCsvUploadForm_Year,
    DebtForm,
    Stakeholder_nameForm,
    StockEventForm,
    StockEventLineForm,
    CsvUploadForm,
    ChatForm,
    MeetingMinutesForm,
    MeetingMinutesImportForm,
    IndustryClassificationImportForm,
    IndustrySubClassificationImportForm,
)
from .tokens import account_activation_token
import random
import csv, io
import calendar
import json
import requests
from django.core.serializers import serialize
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import FieldDoesNotExist
from decimal import Decimal, InvalidOperation

# デバッグ用
import logging
logger = logging.getLogger(__name__)

# 注意: views/__init__.pyからインポートしない（循環インポートを避けるため）
# urls.pyで直接views/__init__.pyからインポートする
# ここでは、views.py内で必要な関数を直接インポート
from scoreai.utils.csv_utils import (
    read_csv_with_auto_encoding,
    validate_csv_structure,
    preview_csv_data
)
from .views.utils import (
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

# 既存のIndexView、LoginView、ScoreLogoutView、UserCreateView、UserProfileView、UserProfileUpdateView、
# CompanyDetailView、CompanyUpdateView、load_industry_subclassificationsは
# 上記のインポートで取得済みのため、ここでは定義しない

##########################################################################
###                    FiscalSummary Yearの View                        ###
##########################################################################

# 既存のLoginView、ScoreLogoutView、UserCreateView、UserProfileView、UserProfileUpdateViewは
# views.auth_viewsからインポート済みのため、ここでは定義しない
##########################################################################
###                    Company の View                                 ###
##########################################################################

# 既存のCompanyDetailView、CompanyUpdateView、load_industry_subclassificationsは
# views.company_viewsからインポート済みのため、ここでは定義しない

##########################################################################
###                   FiscalSummary Yearの View                        ###
##########################################################################

class FiscalSummary_YearCreateView(SelectedCompanyMixin, TransactionMixin, CreateView):
    model = FiscalSummary_Year
    form_class = FiscalSummary_YearForm
    template_name = 'scoreai/fiscal_summary_year_form.html'
    success_url = reverse_lazy('fiscal_summary_year_list')

    def get_initial(self):
        initial = super().get_initial()
        max_year = FiscalSummary_Year.objects.filter(
            company=self.this_company
        ).aggregate(Max('year'))['year__max']
        if max_year is not None:
            initial['year'] = max_year + 1
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['year'].initial = self.get_initial().get('year')
        return form

    def form_valid(self, form):
        # フォームからインスタンスを取得（まだ保存はしない）
        fiscal_summary_year = form.save(commit=False)
        fiscal_summary_year.company = self.this_company
        fiscal_summary_year.version = 1  # versionは常に1に設定
        # is_budgetはフォームから取得（デフォルトはFalse）
        if form.cleaned_data.get('is_budget') is None:
            fiscal_summary_year.is_budget = False

        # 業界分類・小分類が設定されている場合のみスコアを計算
        company = fiscal_summary_year.company
        if company.industry_classification and company.industry_subclassification:
            # 必要な情報を取得
            year = fiscal_summary_year.year
            industry_classification = company.industry_classification
            industry_subclassification = company.industry_subclassification
            company_size = company.company_size

            logger.debug(f"Instance: {fiscal_summary_year}, Year: {year}, Industry Classification: {industry_classification}, "
                         f"Subclassification: {industry_subclassification}, Company Size: {company_size}")

            # 各指標の値を取得
            indicator_values = {
                'sales_growth_rate': fiscal_summary_year.sales_growth_rate,
                'operating_profit_margin': fiscal_summary_year.operating_profit_margin,
                'labor_productivity': fiscal_summary_year.labor_productivity,
                'EBITDA_interest_bearing_debt_ratio': fiscal_summary_year.EBITDA_interest_bearing_debt_ratio,
                'operating_working_capital_turnover_period': fiscal_summary_year.operating_working_capital_turnover_period,
                'equity_ratio': fiscal_summary_year.equity_ratio,
            }

            # 各指標のスコアを計算して更新
            for indicator_name, value in indicator_values.items():
                if value is not None:
                    score = get_finance_score(
                        year,
                        industry_classification,
                        industry_subclassification,
                        company_size,
                        indicator_name,
                        value
                    )
                    if score is not None:
                        if indicator_name == 'sales_growth_rate':
                            fiscal_summary_year.score_sales_growth_rate = score
                        elif indicator_name == 'operating_profit_margin':
                            fiscal_summary_year.score_operating_profit_margin = score
                        elif indicator_name == 'labor_productivity':
                            fiscal_summary_year.score_labor_productivity = score
                        elif indicator_name == 'EBITDA_interest_bearing_debt_ratio':
                            fiscal_summary_year.score_EBITDA_interest_bearing_debt_ratio = score
                        elif indicator_name == 'operating_working_capital_turnover_period':
                            fiscal_summary_year.score_operating_working_capital_turnover_period = score
                        elif indicator_name == 'equity_ratio':
                            fiscal_summary_year.score_equity_ratio = score

        # インスタンスを保存
        fiscal_summary_year.save()
        # self.objectを設定してget_success_urlが正しく動作するようにする
        self.object = fiscal_summary_year
        messages.success(self.request, f'{fiscal_summary_year.year}年の決算データが正常に登録されました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '年次財務諸表'
        context['show_title_card'] = False  # タイトルカードを非表示
        return context

class FiscalSummary_YearUpdateView(SelectedCompanyMixin, TransactionMixin, UpdateView):
    model = FiscalSummary_Year
    form_class = FiscalSummary_YearForm
    template_name = 'scoreai/fiscal_summary_year_form.html'
    success_url = reverse_lazy('fiscal_summary_year_list')

    def get_queryset(self):
        """選択されたCompanyのFiscalSummary_Yearのみを取得"""
        return FiscalSummary_Year.objects.filter(
            company=self.this_company
        )

    def post(self, request, *args, **kwargs):
        """POSTリクエストを処理"""
        logger.info(f"FiscalSummary_YearUpdateView.post called: pk={kwargs.get('pk')}, company={self.this_company.name}")
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        """フォームが無効な場合の処理"""
        logger.warning(f"FiscalSummary_YearUpdateView.form_invalid: errors={form.errors}")
        return super().form_invalid(form)

    def form_valid(self, form):
        logger.info(f"FiscalSummary_YearUpdateView.form_valid called for company: {self.this_company.name}")
        # フォームからインスタンスを取得（まだ保存はしない）
        fiscal_summary_year = form.save(commit=False)
        fiscal_summary_year.company = self.this_company
        fiscal_summary_year.version = 1  # versionは常に1に設定
        logger.info(f"FiscalSummary_Year instance: ID={fiscal_summary_year.id}, Year={fiscal_summary_year.year}")

        # 業界分類・小分類が設定されている場合のみスコアを計算
        company = fiscal_summary_year.company
        if company.industry_classification and company.industry_subclassification:
            # 必要な情報を取得
            year = fiscal_summary_year.year
            industry_classification = company.industry_classification
            industry_subclassification = company.industry_subclassification
            company_size = company.company_size

            logger.debug(f"Instance: {fiscal_summary_year}, Year: {year}, Industry Classification: {industry_classification}, "
                         f"Subclassification: {industry_subclassification}, Company Size: {company_size}")

            # 各指標の値を取得
            indicator_values = {
                'sales_growth_rate': fiscal_summary_year.sales_growth_rate,
                'operating_profit_margin': fiscal_summary_year.operating_profit_margin,
                'labor_productivity': fiscal_summary_year.labor_productivity,
                'EBITDA_interest_bearing_debt_ratio': fiscal_summary_year.EBITDA_interest_bearing_debt_ratio,
                'operating_working_capital_turnover_period': fiscal_summary_year.operating_working_capital_turnover_period,
                'equity_ratio': fiscal_summary_year.equity_ratio,
            }

            # 各指標のスコアを計算して更新
            for indicator_name, value in indicator_values.items():
                if value is not None:
                    score = get_finance_score(
                        year,
                        industry_classification,
                        industry_subclassification,
                        company_size,
                        indicator_name,
                        value
                    )
                    if score is not None:
                        if indicator_name == 'sales_growth_rate':
                            fiscal_summary_year.score_sales_growth_rate = score
                        elif indicator_name == 'operating_profit_margin':
                            fiscal_summary_year.score_operating_profit_margin = score
                        elif indicator_name == 'labor_productivity':
                            fiscal_summary_year.score_labor_productivity = score
                        elif indicator_name == 'EBITDA_interest_bearing_debt_ratio':
                            fiscal_summary_year.score_EBITDA_interest_bearing_debt_ratio = score
                        elif indicator_name == 'operating_working_capital_turnover_period':
                            fiscal_summary_year.score_operating_working_capital_turnover_period = score
                        elif indicator_name == 'equity_ratio':
                            fiscal_summary_year.score_equity_ratio = score

        # インスタンスを保存
        try:
            fiscal_summary_year.save()
            # self.objectを設定してget_success_urlが正しく動作するようにする
            self.object = fiscal_summary_year
            logger.info(f"FiscalSummary_Year updated successfully: ID={fiscal_summary_year.id}, Year={fiscal_summary_year.year}, Company={fiscal_summary_year.company.name}")
            messages.success(self.request, '財務情報が正常に更新されました。')
            return super().form_valid(form)
        except Exception as e:
            logger.error(f"Error saving FiscalSummary_Year: {e}", exc_info=True)
            messages.error(self.request, f'財務情報の更新中にエラーが発生しました: {str(e)}')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '年次財務諸表'
        context['show_title_card'] = False  # タイトルカードを非表示
        return context


# 既存のget_finance_scoreはviews.utilsからインポート済みのため、ここでは定義しない


class FiscalSummary_YearDeleteView(SelectedCompanyMixin, DeleteView):
    model = FiscalSummary_Year
    template_name = 'scoreai/fiscal_summary_year_confirm_delete.html'
    success_url = reverse_lazy('fiscal_summary_year_list')

    def form_valid(self, form):
        fiscal_summary_year = self.get_object()  # 削除するオブジェクトを取得
        try:
            response = super().form_valid(form)
            messages.success(self.request, f'{fiscal_summary_year.year}年の決算データが正常に削除されました。')
            return response
        except ProtectedError:
            messages.error(self.request, '関連データがあるため、この決算データを削除できません。')
            return self.form_invalid(form) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '年次財務諸表'
        context['show_title_card'] = False
        return context


@login_required
def download_fiscal_summary_year_csv(request, param=None):
   # SelectedCompanyMixinのget_selected_company方法を再現
    def get_selected_company():
        return UserCompany.objects.filter(
            user=request.user,
            is_selected=True
        ).select_related('user', 'company').first()
    response = HttpResponse(content_type='text/csv')
    response.charset = 'shift-jis'
    response['Content-Disposition'] = 'attachment; filename="fiscal_summary_years.csv"'

    writer = csv.writer(response)
    headers = [
        'year', '現金及び預金合計（千円）', '売上債権合計（千円）', '棚卸資産合計（千円）', '短期貸付金（千円）',
        '流動資産合計（千円）', '土地（千円）', '建物及び附属設備（千円）', '機械及び装置（千円）',
        '車両運搬具（千円）', '有形固定資産の減価償却累計額（千円）', '有形固定資産合計（千円）',
        'のれん（千円）', '無形固定資産合計（千円）', '長期貸付金（千円）', '投資その他の資産（千円）',
        '繰延資産合計（千円）', '固定資産合計（千円）', '資産の部合計（千円）', '仕入債務合計（千円）',
        '短期借入金（千円）', '流動負債合計（千円）', '長期借入金（千円）', '固定負債合計（千円）',
        '負債の部合計（千円）', '資本金合計（千円）', '資本剰余金合計（千円）', '利益剰余金合計（千円）',
        '株主資本合計（千円）', '評価・換算差額合計（千円）', '新株予約権合計（千円）', '純資産の部合計（千円）',
        '役員貸付金または借入金（千円）', '売上高（千円）', '粗利益（千円）', '売上原価内の減価償却費（千円）',
        '役員報酬（千円）', '給与・雑給（千円）', '販管費内の減価償却費（千円）', '販管費内のその他の償却費（千円）',
        '営業利益（千円）', '営業外収益合計（千円）', '営業外の償却費（千円）', '支払利息（千円）',
        '営業外費用合計（千円）', '経常利益（千円）', '特別利益合計（千円）', '特別損失合計（千円）',
        '法人税等（千円）', '当期純利益（千円）', '税務-繰越欠損金（千円）', '期末従業員数（人）',
        '期末発行済株式数（株）', '注意事項'
    ]
    writer.writerow(headers)

    if param == 'sample':
        return response

    selected_company = get_selected_company()
    if not selected_company:
        return HttpResponse("選択された会社がありません。", status=400)

    this_company = selected_company.company

    if param == 'all':
        fiscal_summary_years = FiscalSummary_Year.objects.filter(
            company=this_company
        ).select_related('company').order_by('year')
    elif param != 'all' and param != 'sample':
        fiscal_summary_years = [get_object_or_404(FiscalSummary_Year, pk=str(param), company=this_company)]
    else:
        return HttpResponse("無効なパラメータです。", status=400)

    for fiscal_summary_year in fiscal_summary_years:
        writer.writerow([
            fiscal_summary_year.year,
            fiscal_summary_year.cash_and_deposits,
            fiscal_summary_year.accounts_receivable,
            fiscal_summary_year.inventory,
            fiscal_summary_year.short_term_loans_receivable,
            fiscal_summary_year.total_current_assets,
            fiscal_summary_year.land,
            fiscal_summary_year.buildings,
            fiscal_summary_year.machinery_equipment,
            fiscal_summary_year.vehicles,
            fiscal_summary_year.accumulated_depreciation,
            fiscal_summary_year.total_tangible_fixed_assets,
            fiscal_summary_year.goodwill,
            fiscal_summary_year.total_intangible_assets,
            fiscal_summary_year.long_term_loans_receivable,
            fiscal_summary_year.investment_other_assets,
            fiscal_summary_year.deferred_assets,
            fiscal_summary_year.total_fixed_assets,
            fiscal_summary_year.total_assets,
            fiscal_summary_year.accounts_payable,
            fiscal_summary_year.short_term_loans_payable,
            fiscal_summary_year.total_current_liabilities,
            fiscal_summary_year.long_term_loans_payable,
            fiscal_summary_year.total_long_term_liabilities,
            fiscal_summary_year.total_liabilities,
            fiscal_summary_year.total_stakeholder_equity,
            fiscal_summary_year.capital_stock,
            fiscal_summary_year.capital_surplus,
            fiscal_summary_year.retained_earnings,
            fiscal_summary_year.valuation_and_translation_adjustment,
            fiscal_summary_year.new_shares_reserve,
            fiscal_summary_year.total_net_assets,
            fiscal_summary_year.directors_loan,
            fiscal_summary_year.sales,
            fiscal_summary_year.gross_profit,
            fiscal_summary_year.depreciation_cogs,
            fiscal_summary_year.depreciation_expense,
            fiscal_summary_year.other_amortization_expense,
            fiscal_summary_year.directors_compensation,
            fiscal_summary_year.payroll_expense,
            fiscal_summary_year.operating_profit,
            fiscal_summary_year.non_operating_amortization_expense,
            fiscal_summary_year.interest_expense,
            fiscal_summary_year.other_income,
            fiscal_summary_year.other_loss,
            fiscal_summary_year.ordinary_profit,
            fiscal_summary_year.extraordinary_income,
            fiscal_summary_year.extraordinary_loss,
            fiscal_summary_year.income_taxes,
            fiscal_summary_year.net_profit,
            fiscal_summary_year.tax_loss_carryforward,
            fiscal_summary_year.number_of_employees_EOY,
            fiscal_summary_year.issued_shares_EOY,
            fiscal_summary_year.financial_statement_notes
        ])

    return response


class FiscalSummary_YearDetailView(SelectedCompanyMixin, DetailView):
    model = FiscalSummary_Year
    template_name = 'scoreai/fiscal_summary_year_detail.html'
    context_object_name = 'fiscal_summary_year'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # スコアが未計算の場合、自動的に計算する
        fiscal_summary_year = self.object
        
        # 年度と予算/実績のプルダウン用データを追加
        available_years = FiscalSummary_Year.objects.filter(
            company=self.this_company
        ).values_list('year', flat=True).distinct().order_by('-year')
        context['available_years'] = list(available_years)
        context['selected_year'] = fiscal_summary_year.year
        context['is_budget'] = fiscal_summary_year.is_budget
        
        needs_save = False
        
        # 必要な情報を取得
        year = fiscal_summary_year.year
        industry_classification = fiscal_summary_year.company.industry_classification
        industry_subclassification = fiscal_summary_year.company.industry_subclassification
        company_size = fiscal_summary_year.company.company_size
        
        # 各指標の値を取得
        indicator_values = {
            'sales_growth_rate': fiscal_summary_year.sales_growth_rate,
            'operating_profit_margin': fiscal_summary_year.operating_profit_margin,
            'labor_productivity': fiscal_summary_year.labor_productivity,
            'EBITDA_interest_bearing_debt_ratio': fiscal_summary_year.EBITDA_interest_bearing_debt_ratio,
            'operating_working_capital_turnover_period': fiscal_summary_year.operating_working_capital_turnover_period,
            'equity_ratio': fiscal_summary_year.equity_ratio,
        }
        
        # 各指標のスコアを計算して更新（スコアが0またはNoneの場合のみ）
        for indicator_name, value in indicator_values.items():
            if value is not None:
                # 現在のスコアを取得
                current_score = None
                if indicator_name == 'sales_growth_rate':
                    current_score = fiscal_summary_year.score_sales_growth_rate
                elif indicator_name == 'operating_profit_margin':
                    current_score = fiscal_summary_year.score_operating_profit_margin
                elif indicator_name == 'labor_productivity':
                    current_score = fiscal_summary_year.score_labor_productivity
                elif indicator_name == 'EBITDA_interest_bearing_debt_ratio':
                    current_score = fiscal_summary_year.score_EBITDA_interest_bearing_debt_ratio
                elif indicator_name == 'operating_working_capital_turnover_period':
                    current_score = fiscal_summary_year.score_operating_working_capital_turnover_period
                elif indicator_name == 'equity_ratio':
                    current_score = fiscal_summary_year.score_equity_ratio
                
                # スコアが0またはNoneの場合のみ計算
                if current_score is None or current_score == 0:
                    score = get_finance_score(
                        year,
                        industry_classification,
                        industry_subclassification,
                        company_size,
                        indicator_name,
                        value
                    )
                    if score is not None:
                        if indicator_name == 'sales_growth_rate':
                            fiscal_summary_year.score_sales_growth_rate = score
                        elif indicator_name == 'operating_profit_margin':
                            fiscal_summary_year.score_operating_profit_margin = score
                        elif indicator_name == 'labor_productivity':
                            fiscal_summary_year.score_labor_productivity = score
                        elif indicator_name == 'EBITDA_interest_bearing_debt_ratio':
                            fiscal_summary_year.score_EBITDA_interest_bearing_debt_ratio = score
                        elif indicator_name == 'operating_working_capital_turnover_period':
                            fiscal_summary_year.score_operating_working_capital_turnover_period = score
                        elif indicator_name == 'equity_ratio':
                            fiscal_summary_year.score_equity_ratio = score
                        needs_save = True
        
        # スコアを更新した場合は保存
        if needs_save:
            fiscal_summary_year.save()
        
        # 前年のデータを取得してcontextに追加
        # previous_year = self.object.year - 1
        previous_data = FiscalSummary_Year.objects.filter(
            year__lt=self.object.year,
            company=self.object.company
        ).select_related('company').order_by('-year').first()
        next_data = FiscalSummary_Year.objects.filter(
            year__gt=self.object.year,
            company=self.object.company
        ).select_related('company').order_by('year').first()
        context['previous_year_data'] = previous_data
        context['next_year_data'] = next_data

        # TechnicalTermの全データを取得し、nameをキーにして辞書を作成
        technical_terms = TechnicalTerm.objects.all()  # 関連オブジェクトなし
        context['technical_terms'] = technical_terms

        # ベンチマーク指数を取得
        benchmark_index = get_benchmark_index(self.this_company.industry_classification, self.this_company.industry_subclassification, self.this_company.company_size, self.object.year)
        context['benchmark_index'] = benchmark_index
        
        # AI診断用: プラン情報を取得（ダウンロード形式の制限用）
        try:
            # Firmユーザーの場合、Firmのプランを確認
            if hasattr(self.request.user, 'userfirm') and self.request.user.userfirm.exists():
                user_firm = self.request.user.userfirm.filter(is_selected=True, active=True).first()
                if user_firm:
                    subscription = user_firm.firm.subscription
                    plan_type = subscription.plan.plan_type
                    # ProfessionalまたはEnterpriseプランの場合、高度なレポート形式をダウンロード可能
                    context['can_download_advanced'] = plan_type in ['professional', 'enterprise']
                else:
                    context['can_download_advanced'] = False
            else:
                # Companyユーザーの場合、デフォルトはPDFのみ
                context['can_download_advanced'] = False
        except Exception:
            context['can_download_advanced'] = False
        
        context['title'] = '年次財務諸表'
        context['show_title_card'] = False  # 第二レベルなのでタイトルカードを非表示

        return context

class LatestFiscalSummaryYearDetailView(SelectedCompanyMixin, TemplateView):
    """単年度決算詳細ビュー（年度と予算/実績を選択可能）"""
    template_name = 'scoreai/fiscal_summary_year_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 年度と予算/実績を取得（デフォルトは直近年度の実績）
        year_param = self.request.GET.get('year')
        is_budget_param = self.request.GET.get('is_budget', 'false')
        
        # 利用可能な年度を取得
        available_years = FiscalSummary_Year.objects.filter(
            company=self.this_company
        ).values_list('year', flat=True).distinct().order_by('-year')
        
        context['available_years'] = list(available_years)
        
        # 年度を決定（デフォルトは最新年度）
        if year_param:
            try:
                selected_year = int(year_param)
            except ValueError:
                selected_year = available_years[0] if available_years else None
        else:
            selected_year = available_years[0] if available_years else None
        
        context['selected_year'] = selected_year
        
        # 予算/実績を決定（デフォルトは実績）
        is_budget = is_budget_param.lower() == 'true'
        context['is_budget'] = is_budget
        
        # 該当するFiscalSummary_Yearを取得
        data_not_found = False
        previous_fiscal_summary_year = None
        
        # まず、選択された年度・予算/実績のデータを探す
        if selected_year:
            fiscal_summary_year = FiscalSummary_Year.objects.filter(
                company=self.this_company,
                year=selected_year,
                is_budget=is_budget,
                is_draft=False
            ).order_by('-version').first()
            
            # データが見つからない場合
            if not fiscal_summary_year:
                data_not_found = True
                context['data_not_found'] = True
                context['data_not_found_year'] = selected_year
                context['data_not_found_is_budget'] = is_budget
                
                # 前回表示していたデータを取得（直近年度の実績をデフォルトとして使用）
                if available_years:
                    latest_year = available_years[0]
                    previous_fiscal_summary_year = FiscalSummary_Year.objects.filter(
                        company=self.this_company,
                        year=latest_year,
                        is_budget=False,
                        is_draft=False
                    ).order_by('-version').first()
        else:
            fiscal_summary_year = None
            data_not_found = True
            context['data_not_found'] = True
        
        # データが見つからない場合は、前回のデータを表示
        if data_not_found and previous_fiscal_summary_year:
            fiscal_summary_year = previous_fiscal_summary_year
        elif not fiscal_summary_year:
            # データが全くない場合
            context['data_not_found'] = True
        
        if fiscal_summary_year:
            # FiscalSummary_YearDetailViewと同じロジックでスコアを計算
            needs_save = False
            year = fiscal_summary_year.year
            industry_classification = fiscal_summary_year.company.industry_classification
            industry_subclassification = fiscal_summary_year.company.industry_subclassification
            company_size = fiscal_summary_year.company.company_size
            
            indicator_values = {
                'sales_growth_rate': fiscal_summary_year.sales_growth_rate,
                'operating_profit_margin': fiscal_summary_year.operating_profit_margin,
                'labor_productivity': fiscal_summary_year.labor_productivity,
                'EBITDA_interest_bearing_debt_ratio': fiscal_summary_year.EBITDA_interest_bearing_debt_ratio,
                'operating_working_capital_turnover_period': fiscal_summary_year.operating_working_capital_turnover_period,
                'equity_ratio': fiscal_summary_year.equity_ratio,
            }
            
            for indicator_name, value in indicator_values.items():
                if value is not None:
                    current_score = None
                    if indicator_name == 'sales_growth_rate':
                        current_score = fiscal_summary_year.score_sales_growth_rate
                    elif indicator_name == 'operating_profit_margin':
                        current_score = fiscal_summary_year.score_operating_profit_margin
                    elif indicator_name == 'labor_productivity':
                        current_score = fiscal_summary_year.score_labor_productivity
                    elif indicator_name == 'EBITDA_interest_bearing_debt_ratio':
                        current_score = fiscal_summary_year.score_EBITDA_interest_bearing_debt_ratio
                    elif indicator_name == 'operating_working_capital_turnover_period':
                        current_score = fiscal_summary_year.score_operating_working_capital_turnover_period
                    elif indicator_name == 'equity_ratio':
                        current_score = fiscal_summary_year.score_equity_ratio
                    
                    if current_score is None or current_score == 0:
                        score = get_finance_score(
                            year,
                            industry_classification,
                            industry_subclassification,
                            company_size,
                            indicator_name,
                            value
                        )
                        if score is not None:
                            if indicator_name == 'sales_growth_rate':
                                fiscal_summary_year.score_sales_growth_rate = score
                            elif indicator_name == 'operating_profit_margin':
                                fiscal_summary_year.score_operating_profit_margin = score
                            elif indicator_name == 'labor_productivity':
                                fiscal_summary_year.score_labor_productivity = score
                            elif indicator_name == 'EBITDA_interest_bearing_debt_ratio':
                                fiscal_summary_year.score_EBITDA_interest_bearing_debt_ratio = score
                            elif indicator_name == 'operating_working_capital_turnover_period':
                                fiscal_summary_year.score_operating_working_capital_turnover_period = score
                            elif indicator_name == 'equity_ratio':
                                fiscal_summary_year.score_equity_ratio = score
                            needs_save = True
            
            if needs_save:
                fiscal_summary_year.save()
            
            # 前年・翌年のデータを取得
            previous_data = FiscalSummary_Year.objects.filter(
                year__lt=fiscal_summary_year.year,
                company=fiscal_summary_year.company
            ).select_related('company').order_by('-year').first()
            next_data = FiscalSummary_Year.objects.filter(
                year__gt=fiscal_summary_year.year,
                company=fiscal_summary_year.company
            ).select_related('company').order_by('year').first()
            context['previous_year_data'] = previous_data
            context['next_year_data'] = next_data
            
            # TechnicalTermの全データを取得
            technical_terms = TechnicalTerm.objects.all()
            context['technical_terms'] = technical_terms
            
            # ベンチマーク指数を取得
            benchmark_index = get_benchmark_index(
                self.this_company.industry_classification,
                self.this_company.industry_subclassification,
                self.this_company.company_size,
                fiscal_summary_year.year
            )
            context['benchmark_index'] = benchmark_index
            
            # AI診断用: プラン情報を取得
            try:
                if hasattr(self.request.user, 'userfirm') and self.request.user.userfirm.exists():
                    user_firm = self.request.user.userfirm.filter(is_selected=True, active=True).first()
                    if user_firm:
                        subscription = user_firm.firm.subscription
                        plan_type = subscription.plan.plan_type
                        context['can_download_advanced'] = plan_type in ['professional', 'enterprise']
                    else:
                        context['can_download_advanced'] = False
                else:
                    context['can_download_advanced'] = False
            except Exception:
                context['can_download_advanced'] = False
        
        context['fiscal_summary_year'] = fiscal_summary_year
        context['title'] = '年次財務諸表'
        context['show_title_card'] = False
        
        return context


# 決算年次推移
class FiscalSummary_YearListView(SelectedCompanyMixin, ListView):
    model = FiscalSummary_Year
    template_name = 'scoreai/fiscal_summary_year_list.html'
    context_object_name = 'fiscal_summary_years'

    def get_queryset(self):
        is_draft = self.request.GET.get('is_draft', 'false').lower() == 'true'
        page_param = int(self.request.GET.get('page_param', 1))
        years_in_page = int(self.request.GET.get('years_in_page', 5))  # Default to 5 if not specified
        show_all = self.request.GET.get('show_all', 'false').lower() == 'true'
        start_year = self.request.GET.get('start_year')
        end_year = self.request.GET.get('end_year')

        # 実績データのみを取得（is_budget=False）
        queryset = FiscalSummary_Year.objects.filter(
            company=self.this_company,
            is_budget=False  # 実績データのみ
        ).select_related('company').order_by('-year')
        
        if not is_draft:
            queryset = queryset.filter(is_draft=False)

        # 年度範囲でフィルタリング
        if start_year:
            try:
                queryset = queryset.filter(year__gte=int(start_year))
            except ValueError:
                pass
        if end_year:
            try:
                queryset = queryset.filter(year__lte=int(end_year))
            except ValueError:
                pass

        # 全期間表示の場合はページネーションなし
        if show_all:
            return queryset

        # Calculate the start and end indices for slicing the queryset
        start_index = (page_param - 1) * years_in_page
        end_index = start_index + years_in_page

        return queryset[start_index:end_index]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # パラメータを取得
        is_draft = self.request.GET.get('is_draft', 'false').lower() == 'true'
        show_all = self.request.GET.get('show_all', 'false').lower() == 'true'
        start_year = self.request.GET.get('start_year')
        end_year = self.request.GET.get('end_year')
        years_in_page = int(self.request.GET.get('years_in_page', 5))
        
        # フィルタリング用のクエリセットを作成
        base_queryset = FiscalSummary_Year.objects.filter(
            company=self.this_company,
            is_budget=False
        )
        if not is_draft:
            base_queryset = base_queryset.filter(is_draft=False)
        if start_year:
            try:
                base_queryset = base_queryset.filter(year__gte=int(start_year))
            except ValueError:
                pass
        if end_year:
            try:
                base_queryset = base_queryset.filter(year__lte=int(end_year))
            except ValueError:
                pass
        
        # Calculate total pages（フィルタリング後のデータをカウント）
        total_records = base_queryset.count()
        
        # 利用可能な年度範囲を取得
        all_years = FiscalSummary_Year.objects.filter(
            company=self.this_company,
            is_budget=False
        ).values_list('year', flat=True).distinct().order_by('year')
        context['min_year'] = all_years.first() if all_years else None
        context['max_year'] = all_years.last() if all_years else None
        
        if show_all:
            context['total_pages'] = 1
        else:
            context['total_pages'] = (total_records + years_in_page - 1) // years_in_page if total_records > 0 else 1
        
        # Add parameters to the context
        context['page_param'] = self.request.GET.get('page_param', 1)
        context['years_in_page'] = years_in_page
        context['show_all'] = show_all
        context['start_year'] = start_year
        context['end_year'] = end_year
        context['is_draft'] = is_draft

        # 予算実績比較データを取得（最新年度）
        queryset = self.get_queryset()
        latest_fiscal = queryset.first()
        if latest_fiscal:
            latest_year = latest_fiscal.year
            budget_year = FiscalSummary_Year.objects.filter(
                company=self.this_company,
                year=latest_year,
                is_budget=True
            ).first()
            
            actual_year = FiscalSummary_Year.objects.filter(
                company=self.this_company,
                year=latest_year,
                is_budget=False,
                is_draft=False
            ).first()
        else:
            budget_year = None
            actual_year = None
        
        context['title'] = '年次財務諸表'
        context['show_title_card'] = False  # タイトルカードを非表示（他のページと統一）
        context['budget_year'] = budget_year
        context['actual_year'] = actual_year
        return context


class ImportFiscalSummary_Year(SelectedCompanyMixin, TransactionMixin, FormView):
    template_name = "scoreai/import_fiscal_summary_year.html"
    form_class = CsvUploadForm
    success_url = reverse_lazy('fiscal_summary_year_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '年次決算'
        context['show_title_card'] = False
        return context

    def form_valid(self, form):
        csv_file = form.cleaned_data['csv_file']
        override_flag = form.cleaned_data.get('override_flag', False)
        if not csv_file.name.endswith('.csv'):
            messages.error(self.request, 'アップロードされたファイルはCSV形式ではありません。')
            return super().form_invalid(form)
        
        try:
            file = TextIOWrapper(csv_file.file, encoding='shift-jis')
            reader = csv.DictReader(file)
            
            def safe_value(field_name, value):
                if value.strip() == '':
                    try:
                        return FiscalSummary_Year._meta.get_field(field_name).get_default()
                    except FieldDoesNotExist:
                        return None
                try:
                    return int(value)
                except ValueError:
                    return value

            for row in reader:
                year = safe_value('year', row['year'])
                defaults = {
                    'cash_and_deposits': safe_value('cash_and_deposits', row['現金及び預金合計（千円）']),
                    'accounts_receivable': safe_value('accounts_receivable', row['売上債権合計（千円）']),
                    'inventory': safe_value('inventory', row['棚卸資産合計（千円）']),
                    'short_term_loans_receivable': safe_value('short_term_loans_receivable', row['短期貸付金（千円）']),
                    'total_current_assets': safe_value('total_current_assets', row['流動資産合計（千円）']),
                    'land': safe_value('land', row['土地（千円）']),
                    'buildings': safe_value('buildings', row['建物及び附属設備（千円）']),
                    'machinery_equipment': safe_value('machinery_equipment', row['機械及び装置（千円）']),
                    'vehicles': safe_value('vehicles', row['車両運搬具（千円）']),
                    'accumulated_depreciation': safe_value('accumulated_depreciation', row['有形固定資産の減価償却累計額（千円）']),
                    'total_tangible_fixed_assets': safe_value('total_tangible_fixed_assets', row['有形固定資産合計（千円）']),
                    'goodwill': safe_value('goodwill', row['のれん（千円）']),
                    'total_intangible_assets': safe_value('total_intangible_assets', row['無形固定資産合計（千円）']),
                    'long_term_loans_receivable': safe_value('long_term_loans_receivable', row['長期貸付金（千円）']),
                    'investment_other_assets': safe_value('investment_other_assets', row['投資その他の資産（千円）']),
                    'total_fixed_assets': safe_value('total_fixed_assets', row['固定資産合計（千円）']),
                    'deferred_assets': safe_value('deferred_assets', row['繰延資産合計（千円）']),
                    'total_assets': safe_value('total_assets', row['資産の部合計（千円）']),
                    'accounts_payable': safe_value('accounts_payable', row['仕入債務合計（千円）']),
                    'short_term_loans_payable': safe_value('short_term_loans_payable', row['短期借入金（千円）']),
                    'total_current_liabilities': safe_value('total_current_liabilities', row['流動負債合計（千円）']),
                    'long_term_loans_payable': safe_value('long_term_loans_payable', row['長期借入金（千円）']),
                    'total_long_term_liabilities': safe_value('total_long_term_liabilities', row['固定負債合計（千円）']),
                    'total_liabilities': safe_value('total_liabilities', row['負債の部合計（千円）']),
                    'capital_stock': safe_value('capital_stock', row['資本金合計（千円）']),
                    'capital_surplus': safe_value('capital_surplus', row['資本剰余金合計（千円）']),
                    'retained_earnings': safe_value('retained_earnings', row['利益剰余金合計（千円）']),
                    'total_stakeholder_equity': safe_value('total_stakeholder_equity', row['株主資本合計（千円）']),
                    'valuation_and_translation_adjustment': safe_value('valuation_and_translation_adjustment', row['評価・換算差額合計（千円）']),
                    'new_shares_reserve': safe_value('new_shares_reserve', row['新株予約権合計（千円）']),
                    'total_net_assets': safe_value('total_net_assets', row['純資産の部合計（千円）']),
                    'directors_loan': safe_value('directors_loan', row['役員貸付金または借入金（千円）']),
                    'sales': safe_value('sales', row['売上高（千円）']),
                    'gross_profit': safe_value('gross_profit', row['粗利益（千円）']),
                    'depreciation_cogs': safe_value('depreciation_cogs', row['売上原価内の減価償却費（千円）']),
                    'directors_compensation': safe_value('directors_compensation', row['役員報酬（千円）']),
                    'payroll_expense': safe_value('payroll_expense', row['給与・雑給（千円）']),
                    'depreciation_expense': safe_value('depreciation_expense', row['販管費内の減価償却費（千円）']),
                    'other_amortization_expense': safe_value('other_amortization_expense', row['販管費内のその他の償却費（千円）']),
                    'operating_profit': safe_value('operating_profit', row['営業利益（千円）']),
                    'other_income': safe_value('other_income', row['営業外収益合計（千円）']),
                    'non_operating_amortization_expense': safe_value('non_operating_amortization_expense', row['営業外の償却費（千円）']),
                    'interest_expense': safe_value('interest_expense', row['支払利息（千円）']),
                    'other_loss': safe_value('other_loss', row['営業外費用合計（千円）']),
                    'ordinary_profit': safe_value('ordinary_profit', row['経常利益（千円）']),
                    'extraordinary_income': safe_value('extraordinary_income', row['特別利益合計（千円）']),
                    'extraordinary_loss': safe_value('extraordinary_loss', row['特別損失合計（千円）']),
                    'income_taxes': safe_value('income_taxes', row['法人税等（千円）']),
                    'net_profit': safe_value('net_profit', row['当期純利益（千円）']),
                    'tax_loss_carryforward': safe_value('tax_loss_carryforward', row['税務-繰越欠損金（千円）']),
                    'number_of_employees_EOY': safe_value('number_of_employees_EOY', row['期末従業員数（人）']),
                    'issued_shares_EOY': safe_value('issued_shares_EOY', row['期末発行済株式数（株）']),
                    'financial_statement_notes': row['注意事項'],
                }                
                
                if year is not None:
                    # 実績データ（is_budget=False）のみをチェック
                    existing_data = FiscalSummary_Year.objects.filter(
                        company=self.this_company,
                        year=year,
                        is_budget=False,  # 実績データのみをチェック
                    ).exists()

                    if existing_data and not override_flag:
                        messages.error(
                            self.request,
                            f'{year}年の実績データは既に存在します。上書きする場合は「既存データを上書きする」を選択してください。'
                        )
                        return self.form_invalid(form)
                    else:
                        # 実績データとして設定（is_budget=False）
                        defaults['is_budget'] = False
                        defaults['is_draft'] = False  # 下書きではない
                        defaults['version'] = 1  # versionは常に1に設定
                        FiscalSummary_Year.objects.update_or_create(
                            company=self.this_company,
                            year=year,
                            is_budget=False,  # 実績データのみを対象
                            defaults=defaults
                        )
                else:
                    messages.warning(self.request, '年度が指定されていない行をスキップしました。')
            
            messages.success(self.request, 'CSVファイルが正常にインポートされました。')
        except Exception as e:
            messages.error(self.request, f'CSVファイルの処理中にエラーが発生しました: {str(e)}')
            return self.form_invalid(form)

        return super().form_valid(form)

##########################################################################
###                   FiscalSummary Monthの View                        ###
##########################################################################
from django.urls import reverse_lazy
from django.contrib import messages

class FiscalSummary_MonthCreateView(SelectedCompanyMixin, CreateView):
    model = FiscalSummary_Month
    form_class = FiscalSummary_MonthForm
    template_name = 'scoreai/fiscal_summary_month_form.html'
    success_url = reverse_lazy('fiscal_summary_month_list')

    def get_initial(self):
        initial = super().get_initial()
        company = self.this_company
        latest_fiscal_year = FiscalSummary_Year.objects.filter(company=company).order_by('-year').first()
        if latest_fiscal_year:
            initial['fiscal_summary_year'] = latest_fiscal_year
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        company = self.this_company
        queryset = FiscalSummary_Year.objects.filter(company=company)
        form.fields['fiscal_summary_year'].queryset = queryset
        
        # 選択肢の表示名に予算/実績を追加
        form.fields['fiscal_summary_year'].label_from_instance = lambda obj: f"{obj.company.name} - {obj.year}年 ({'予算' if obj.is_budget else '実績'})"
        
        # is_budgetフィールドを非表示（自動制御のため）
        form.fields['is_budget'].widget = forms.HiddenInput()
        
        return form

    def form_valid(self, form):
        # 選択したFiscalSummary_Yearのis_budgetに基づいて、FiscalSummary_Monthのis_budgetを自動設定
        selected_year = form.cleaned_data['fiscal_summary_year']
        form.instance.is_budget = selected_year.is_budget
        form.instance.fiscal_summary_year.company = self.this_company
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '月次PL'
        context['show_title_card'] = False  # タイトルカードを非表示
        return context


class FiscalSummary_MonthUpdateView(SelectedCompanyMixin, UpdateView):
    model = FiscalSummary_Month
    form_class = FiscalSummary_MonthForm
    template_name = 'scoreai/fiscal_summary_month_form.html'
    success_url = reverse_lazy('fiscal_summary_month_list')

    def get_queryset(self):
        return FiscalSummary_Month.objects.filter(
            fiscal_summary_year__company=self.this_company
        ).select_related(
            'fiscal_summary_year',
            'fiscal_summary_year__company'
        ).order_by('-fiscal_summary_year__year', 'period')

    def get_object(self, queryset=None):
        obj = super(UpdateView, self).get_object(queryset)
        if obj.fiscal_summary_year.company != self.this_company:
            raise PermissionDenied("このデータを更新する権限がありません。")
        return obj

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # 編集時はfiscal_summary_yearを読み取り専用にする
        if self.object:
            form.fields['fiscal_summary_year'].disabled = True
        return form

    def form_valid(self, form):
        # fiscal_summary_yearの変更を防ぐ
        form.instance.fiscal_summary_year = self.object.fiscal_summary_year
        response = super().form_valid(form)
        messages.success(self.request, f'{self.object.fiscal_summary_year.year}年{self.object.period}月の月次データを更新しました。')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '月次PL'
        context['fiscal_summary_year'] = self.object.fiscal_summary_year
        context['show_title_card'] = False  # タイトルカードを非表示
        return context


class FiscalSummary_MonthDeleteView(SelectedCompanyMixin, DeleteView):
    model = FiscalSummary_Month
    template_name = 'scoreai/fiscal_summary_month_confirm_delete.html'
    success_url = reverse_lazy('fiscal_summary_month_list')

    def get_queryset(self):
        company = self.this_company
        return FiscalSummary_Month.objects.filter(fiscal_summary_year__company=company).order_by('-fiscal_summary_year__year', 'period')

    def get_object(self, queryset=None):
        obj = super(DeleteView, self).get_object(queryset)
        if obj.fiscal_summary_year.company != self.this_company:
            raise PermissionDenied("このデータを削除する権限がありません。")
        return obj

    def form_valid(self, form):
        fiscal_summary_month = self.get_object()
        year = fiscal_summary_month.fiscal_summary_year.year
        month = fiscal_summary_month.period
        response = super().form_valid(form)
        messages.success(self.request, f'{year}年{month}月の月次財務サマリーデータを削除しました。')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '月次PL'
        context['show_title_card'] = False
        return context

class FiscalSummary_MonthDetailView(SelectedCompanyMixin, DetailView):
    model = FiscalSummary_Month
    template_name = 'scoreai/fiscal_summary_month_detail.html'
    context_object_name = 'fiscal_summary_month'

    def get_queryset(self):
        return FiscalSummary_Month.objects.filter(
            fiscal_summary_year__company=self.this_company
        ).select_related(
            'fiscal_summary_year',
            'fiscal_summary_year__company'
        ).order_by('-fiscal_summary_year__year', 'period')

    def get_object(self, queryset=None):
        # Override get_object to check if the object belongs to the selected company
        obj = super(DetailView, self).get_object(queryset)
        if obj.fiscal_summary_year.company != self.this_company:
            raise PermissionDenied("You don't have permission to access this object.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '月次PL'
        context['show_title_card'] = False
        return context

class LatestMonthlyPLView(SelectedCompanyMixin, TemplateView):
    """単年度月次PLビュー（年度と予算/実績を選択可能）"""
    template_name = 'scoreai/monthly_pl_single_year.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 年度と予算/実績を取得（デフォルトは直近年度の実績）
        year_param = self.request.GET.get('year')
        is_budget_param = self.request.GET.get('is_budget', 'false')
        
        # 利用可能な年度を取得
        available_years = FiscalSummary_Year.objects.filter(
            company=self.this_company
        ).values_list('year', flat=True).distinct().order_by('-year')
        
        context['available_years'] = list(available_years)
        
        # 年度を決定（デフォルトは最新年度）
        if year_param:
            try:
                selected_year = int(year_param)
            except ValueError:
                selected_year = available_years[0] if available_years else None
        else:
            selected_year = available_years[0] if available_years else None
        
        context['selected_year'] = selected_year
        
        # 予算/実績を決定（デフォルトは実績）
        is_budget = is_budget_param.lower() == 'true'
        context['is_budget'] = is_budget
        
        # 該当するFiscalSummary_Yearを取得
        data_not_found = False
        fallback_fiscal_summary_year = None
        
        if selected_year:
            fiscal_summary_year = FiscalSummary_Year.objects.filter(
                company=self.this_company,
                year=selected_year,
                is_budget=is_budget,
                is_draft=False
            ).order_by('-version').first()
            
            # データが見つからない場合、フォールバックを試す
            if not fiscal_summary_year:
                # まず、同じ年度で予算/実績を逆に試す
                fallback_fiscal_summary_year = FiscalSummary_Year.objects.filter(
                    company=self.this_company,
                    year=selected_year,
                    is_budget=not is_budget,
                    is_draft=False
                ).order_by('-version').first()
                
                # それでも見つからない場合、直近年度の実績を取得
                if not fallback_fiscal_summary_year and available_years:
                    latest_year = available_years[0]
                    fallback_fiscal_summary_year = FiscalSummary_Year.objects.filter(
                        company=self.this_company,
                        year=latest_year,
                        is_budget=False,
                        is_draft=False
                    ).order_by('-version').first()
                
                if fallback_fiscal_summary_year:
                    fiscal_summary_year = fallback_fiscal_summary_year
                    # フォールバックを使用した場合、警告を表示
                    data_not_found = True
                    context['data_not_found'] = True
                    context['data_not_found_year'] = selected_year
                    context['data_not_found_is_budget'] = is_budget
                    # 実際に表示する年度と予算/実績を更新
                    selected_year = fiscal_summary_year.year
                    is_budget = fiscal_summary_year.is_budget
                    context['selected_year'] = selected_year
                    context['is_budget'] = is_budget
                else:
                    data_not_found = True
                    context['data_not_found'] = True
                    context['data_not_found_year'] = selected_year
                    context['data_not_found_is_budget'] = is_budget
        else:
            # 年度が指定されていない場合、直近年度の実績を取得
            if available_years:
                latest_year = available_years[0]
                fiscal_summary_year = FiscalSummary_Year.objects.filter(
                    company=self.this_company,
                    year=latest_year,
                    is_budget=False,
                    is_draft=False
                ).order_by('-version').first()
                if fiscal_summary_year:
                    selected_year = latest_year
                    is_budget = False
                    context['selected_year'] = selected_year
                    context['is_budget'] = is_budget
            else:
                fiscal_summary_year = None
                data_not_found = True
                context['data_not_found'] = True
        
        # 月次データを取得
        monthly_data_list = []
        if fiscal_summary_year:
            monthly_data = FiscalSummary_Month.objects.filter(
                fiscal_summary_year=fiscal_summary_year,
                is_budget=fiscal_summary_year.is_budget
            ).order_by('period')
            
            # 決算月を取得
            fiscal_month = self.this_company.fiscal_month if hasattr(self.this_company, 'fiscal_month') else 1
            
            # 12ヶ月分のデータを作成
            monthly_dict = {m.period: m for m in monthly_data}
            for period in range(1, 13):
                # 決算月の次の月から開始（決算月が最後）
                display_month = (fiscal_month + period) % 12
                if display_month == 0:
                    display_month = 12
                
                if period in monthly_dict:
                    month_obj = monthly_dict[period]
                    monthly_data_list.append({
                        'id': month_obj.id,
                        'period': period,
                        'display_month': display_month,
                        'sales': float(month_obj.sales) if month_obj.sales is not None else 0.0,
                        'gross_profit': float(month_obj.gross_profit) if month_obj.gross_profit is not None else 0.0,
                        'operating_profit': float(month_obj.operating_profit) if month_obj.operating_profit is not None else 0.0,
                        'ordinary_profit': float(month_obj.ordinary_profit) if month_obj.ordinary_profit is not None else 0.0,
                        'gross_profit_rate': float(month_obj.gross_profit_rate) if month_obj.gross_profit_rate is not None else 0.0,
                        'operating_profit_rate': float(month_obj.operating_profit_rate) if month_obj.operating_profit_rate is not None else 0.0,
                        'ordinary_profit_rate': float(month_obj.ordinary_profit_rate) if month_obj.ordinary_profit_rate is not None else 0.0,
                        'is_budget': month_obj.is_budget,
                    })
                else:
                    # データがない月は空データを追加
                    monthly_data_list.append({
                        'id': None,
                        'period': period,
                        'display_month': display_month,
                        'sales': 0.0,
                        'gross_profit': 0.0,
                        'operating_profit': 0.0,
                        'ordinary_profit': 0.0,
                        'gross_profit_rate': 0.0,
                        'operating_profit_rate': 0.0,
                        'ordinary_profit_rate': 0.0,
                        'is_budget': is_budget,
                    })
            
            # 合計値を計算
            total_sales = sum(m['sales'] for m in monthly_data_list)
            total_gross_profit = sum(m['gross_profit'] for m in monthly_data_list)
            total_operating_profit = sum(m['operating_profit'] for m in monthly_data_list)
            total_ordinary_profit = sum(m['ordinary_profit'] for m in monthly_data_list)
            
            total_gross_profit_rate = (total_gross_profit / total_sales * 100) if total_sales > 0 else 0
            total_operating_profit_rate = (total_operating_profit / total_sales * 100) if total_sales > 0 else 0
            total_ordinary_profit_rate = (total_ordinary_profit / total_sales * 100) if total_sales > 0 else 0
            
            context['monthly_data'] = monthly_data_list
            context['total_sales'] = total_sales
            context['total_gross_profit'] = total_gross_profit
            context['total_operating_profit'] = total_operating_profit
            context['total_ordinary_profit'] = total_ordinary_profit
            context['total_gross_profit_rate'] = total_gross_profit_rate
            context['total_operating_profit_rate'] = total_operating_profit_rate
            context['total_ordinary_profit_rate'] = total_ordinary_profit_rate
            context['fiscal_summary_year'] = fiscal_summary_year
            context['fiscal_month'] = fiscal_month
        
        context['title'] = '月次PL'
        context['show_title_card'] = False
        
        return context


class FiscalSummary_MonthListView(SelectedCompanyMixin, ListView):
    model = FiscalSummary_Month
    template_name = 'scoreai/fiscal_summary_month_list.html'
    context_object_name = 'fiscal_summary_months'

    def get_queryset(self):
        # 実績データのみを取得（is_budget=False、下書きも含む）
        return FiscalSummary_Month.objects.filter(
            fiscal_summary_year__company=self.this_company,
            fiscal_summary_year__is_budget=False,
            is_budget=False
        ).select_related(
            'fiscal_summary_year',
            'fiscal_summary_year__company'
        ).order_by('-fiscal_summary_year__year', '-fiscal_summary_year__is_draft', 'period')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 利用可能な年度を取得
        available_years = FiscalSummary_Year.objects.filter(
            company=self.this_company,
            is_budget=False
        ).values_list('year', flat=True).distinct().order_by('-year')
        
        context['available_years'] = list(available_years)
        
        # 開始年度と終了年度を取得
        start_year_param = self.request.GET.get('start_year')
        end_year_param = self.request.GET.get('end_year')
        
        # デフォルトは最新年度から過去3年分
        default_end_year = available_years[0] if available_years else None
        default_start_year = default_end_year - 2 if default_end_year else None
        
        if end_year_param:
            try:
                end_year = int(end_year_param)
            except ValueError:
                end_year = default_end_year
        else:
            end_year = default_end_year
        
        if start_year_param:
            try:
                start_year = int(start_year_param)
            except ValueError:
                start_year = default_start_year
        else:
            start_year = default_start_year
        
        # 範囲の検証（最大5年間、開始年度 <= 終了年度）
        if start_year and end_year:
            if start_year > end_year:
                start_year, end_year = end_year, start_year
            if end_year - start_year > 4:
                start_year = end_year - 4
        
        context['start_year'] = start_year
        context['end_year'] = end_year
        
        # 選択された年度範囲のデータを取得
        comparison_years_data = []
        chart_data = None
        
        if start_year and end_year:
            # 開始年度から終了年度までの年度リストを作成（最大5年）
            # 古い年度から新しい年度へと昇順で並べる（グラフの棒グラフ表示順序のため）
            years_to_compare = [year for year in range(start_year, end_year + 1) if year in available_years]
            years_to_compare.sort()  # 昇順にソート
            # 最大5年までに制限
            if len(years_to_compare) > 5:
                years_to_compare = years_to_compare[:5]
            
            fiscal_month = self.this_company.fiscal_month if hasattr(self.this_company, 'fiscal_month') else 1
            
            # 各年度のデータを取得
            for year in years_to_compare:
                fiscal_summary_year = FiscalSummary_Year.objects.filter(
                    company=self.this_company,
                    year=year,
                    is_budget=False,
                    is_draft=False
                ).select_related('company').order_by('-version').first()
                
                if fiscal_summary_year:
                    monthly_data_list = FiscalSummary_Month.objects.filter(
                        fiscal_summary_year=fiscal_summary_year,
                        is_budget=False
                    ).select_related('fiscal_summary_year', 'fiscal_summary_year__company').order_by('period')
                    
                    # 12ヶ月分のデータを作成
                    monthly_dict = {m.period: m for m in monthly_data_list}
                    year_data_list = []
                    
                    for period in range(1, 13):
                        # 決算月の次の月から開始（決算月が最後）
                        display_month = (fiscal_month + period) % 12
                        if display_month == 0:
                            display_month = 12
                        
                        if period in monthly_dict:
                            month_obj = monthly_dict[period]
                            month_data = {
                                'id': month_obj.id,
                                'period': period,
                                'display_month': display_month,
                                'sales': float(month_obj.sales) if month_obj.sales is not None else 0.0,
                                'gross_profit': float(month_obj.gross_profit) if month_obj.gross_profit is not None else 0.0,
                                'operating_profit': float(month_obj.operating_profit) if month_obj.operating_profit is not None else 0.0,
                                'ordinary_profit': float(month_obj.ordinary_profit) if month_obj.ordinary_profit is not None else 0.0,
                                'gross_profit_rate': float(month_obj.gross_profit_rate) if month_obj.gross_profit_rate is not None else 0.0,
                                'operating_profit_rate': float(month_obj.operating_profit_rate) if month_obj.operating_profit_rate is not None else 0.0,
                                'ordinary_profit_rate': float(month_obj.ordinary_profit_rate) if month_obj.ordinary_profit_rate is not None else 0.0,
                                'is_budget': month_obj.is_budget,
                            }
                        else:
                            month_data = {
                                'id': None,
                                'period': period,
                                'display_month': display_month,
                                'sales': 0.0,
                                'gross_profit': 0.0,
                                'operating_profit': 0.0,
                                'ordinary_profit': 0.0,
                                'gross_profit_rate': 0.0,
                                'operating_profit_rate': 0.0,
                                'ordinary_profit_rate': 0.0,
                                'is_budget': False,
                            }
                        
                        year_data_list.append(month_data)
                    
                    # 合計値を計算
                    total_sales = sum(m['sales'] for m in year_data_list)
                    total_gross_profit = sum(m['gross_profit'] for m in year_data_list)
                    total_operating_profit = sum(m['operating_profit'] for m in year_data_list)
                    total_ordinary_profit = sum(m['ordinary_profit'] for m in year_data_list)
                    
                    total_gross_profit_rate = (total_gross_profit / total_sales * 100) if total_sales > 0 else 0
                    total_operating_profit_rate = (total_operating_profit / total_sales * 100) if total_sales > 0 else 0
                    total_ordinary_profit_rate = (total_ordinary_profit / total_sales * 100) if total_sales > 0 else 0
                    
                    year_summary = {
                        'year': year,
                        'data': year_data_list,
                        'total_sales': total_sales,
                        'total_gross_profit': total_gross_profit,
                        'total_operating_profit': total_operating_profit,
                        'total_ordinary_profit': total_ordinary_profit,
                        'total_gross_profit_rate': total_gross_profit_rate,
                        'total_operating_profit_rate': total_operating_profit_rate,
                        'total_ordinary_profit_rate': total_ordinary_profit_rate,
                    }
                    
                    comparison_years_data.append(year_summary)
            
            # チャート用データを準備（各年度の月次データ）
            if comparison_years_data:
                # 月のラベル（最初の年度のデータから取得）
                first_year_data = comparison_years_data[0]
                chart_data = {
                    'labels': [f"{m['display_month']}月" for m in first_year_data['data']],
                    'years': [],
                    'sales': {},
                    'gross_profit': {},
                    'operating_profit': {},
                    'ordinary_profit': {},
                }
                
                for year_data in comparison_years_data:
                    year = year_data['year']
                    chart_data['years'].append(year)
                    chart_data['sales'][str(year)] = [m['sales'] for m in year_data['data']]
                    chart_data['gross_profit'][str(year)] = [m['gross_profit'] for m in year_data['data']]
                    chart_data['operating_profit'][str(year)] = [m['operating_profit'] for m in year_data['data']]
                    chart_data['ordinary_profit'][str(year)] = [m['ordinary_profit'] for m in year_data['data']]
        
        import json
        context['chart_data_json'] = json.dumps(chart_data) if chart_data else None
        
        # 比較年度のデータをテーブル用に準備
        monthly_summaries_with_summary = {
            'monthly_data': comparison_years_data,
            'summary_data': []
        }
        
        # ラベル情報（決算月の次の月から開始、決算月が最後）
        fiscal_month = self.this_company.fiscal_month if hasattr(self.this_company, 'fiscal_month') else 1
        months_label = [((fiscal_month + i) % 12) or 12 for i in range(1, 13)]
        
        context.update({
            'title': '月次PL',
            'show_title_card': False,  # タイトルカードを非表示（他のページと統一）
            'monthly_summaries_with_summary': monthly_summaries_with_summary,
            'months_label': months_label,
        })
        return context


@login_required
def download_fiscal_summary_month_csv(request, param=None):
    def get_selected_company():
        return UserCompany.objects.filter(
            user=request.user,
            is_selected=True
        ).select_related('user', 'company').first()
    
    response = HttpResponse(content_type='text/csv')
    response.charset = 'shift-jis'
    response['Content-Disposition'] = 'attachment; filename="fiscal_summary_months.csv"'

    writer = csv.writer(response)
    headers = [
        '年度', '月度', '売上高（千円）', '粗利益（千円）', '営業利益（千円）', '経常利益（千円）'
    ]
    writer.writerow(headers)

    if param == 'sample':
        return response

    selected_company = get_selected_company()
    if not selected_company:
        return HttpResponse("選択された会社がありません。", status=400)

    this_company = selected_company.company

    if param == 'all':
        fiscal_summary_months = FiscalSummary_Month.objects.filter(
            fiscal_summary_year__company=this_company
        ).order_by('fiscal_summary_year__year', 'period')
    elif param != 'all' and param != 'sample':
        fiscal_summary_year = get_object_or_404(FiscalSummary_Year, pk=str(param), company=this_company)
        fiscal_summary_months = FiscalSummary_Month.objects.filter(
            fiscal_summary_year=fiscal_summary_year
        ).order_by('period')
    else:
        return HttpResponse("無効なパラメータです。", status=400)

    for fiscal_summary_month in fiscal_summary_months:
        writer.writerow([
            fiscal_summary_month.fiscal_summary_year.year,
            fiscal_summary_month.period,
            fiscal_summary_month.sales,
            fiscal_summary_month.gross_profit,
            fiscal_summary_month.operating_profit,
            fiscal_summary_month.ordinary_profit
        ])

    return response

##########################################################################
### CSVアップロード機能　###
##########################################################################

# CSVを編集してからアップロードする
class ImportFiscalSummary_Month(SelectedCompanyMixin, TransactionMixin, FormView):
    template_name = "scoreai/import_fiscal_summary_month.html"
    form_class = CsvUploadForm
    success_url = reverse_lazy('fiscal_summary_month_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '月次PL'
        context['show_title_card'] = False
        return context

    def form_valid(self, form):
        csv_file = form.cleaned_data['csv_file']
        override_flag = form.cleaned_data.get('override_flag', False)
        if not csv_file.name.endswith('.csv'):
            messages.error(self.request, 'アップロードされたファイルはCSV形式ではありません。')
            return super().form_invalid(form)

        try:
            file = TextIOWrapper(csv_file.file, encoding='shift-jis')
            reader = csv.DictReader(file)
            
            def safe_value(field_name, value):
                if value.strip() == '':
                    return 0
                try:
                    return float(value.replace(',', ''))
                except ValueError:
                    return value

            for row in reader:
                fiscal_year = int(row['年度'])
                period = int(row['月度'])
                
                # versionは常に1で固定（defaultsに含めない、モデルのdefault=1が適用される）
                fiscal_summary_year, created = FiscalSummary_Year.objects.get_or_create(
                    company=self.this_company,
                    year=fiscal_year,
                    is_budget=False,  # 実績データとして明示的に指定
                    defaults={}
                )
                
                defaults = {
                    'sales': safe_value('sales', row['売上高（千円）']),
                    'gross_profit': safe_value('gross_profit', row['粗利益（千円）']),
                    'operating_profit': safe_value('operating_profit', row['営業利益（千円）']),
                    'ordinary_profit': safe_value('ordinary_profit', row['経常利益（千円）']),
                }
                
                existing_data = FiscalSummary_Month.objects.filter(
                    fiscal_summary_year=fiscal_summary_year,
                    period=period
                ).exists()

                if existing_data and not override_flag:
                    messages.error(
                        self.request,
                        f'{fiscal_year}年の{period}月のデータは既に存在します。上書きする場合は「既存データを上書きする」を選択してください。'
                    )
                    return self.form_invalid(form)
                else:
                    FiscalSummary_Month.objects.update_or_create(
                        fiscal_summary_year=fiscal_summary_year,
                        period=period,
                        defaults=defaults
                    )

            messages.success(self.request, 'CSVファイルが正常にインポートされました。')
        except UnicodeDecodeError as e:
            logger.error(f"CSV encoding error in ImportFiscalSummary_Month: {e}", exc_info=True)
            messages.error(self.request, 'CSVファイルの文字コードが正しくありません。Shift-JIS形式のファイルをアップロードしてください。')
            return self.form_invalid(form)
        except KeyError as e:
            logger.error(f"CSV column error in ImportFiscalSummary_Month: {e}", exc_info=True)
            messages.error(self.request, f'CSVファイルの列名が正しくありません。必要な列が見つかりません: {str(e)}')
            return self.form_invalid(form)
        except ValueError as e:
            logger.error(f"CSV value error in ImportFiscalSummary_Month: {e}", exc_info=True)
            messages.error(self.request, f'CSVファイルの値が正しくありません: {str(e)}')
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Unexpected error in ImportFiscalSummary_Month: {e}", exc_info=True,
                        extra={'user': self.request.user.id if self.request.user.is_authenticated else None})
            messages.error(self.request, 'CSVファイルの処理中にエラーが発生しました。管理者にお問い合わせください。')
            return self.form_invalid(form)

        return super().form_valid(form)


# Moneyfowardの月次推移表をアップしたらそのまま変換してインポートする
class ImportFiscalSummary_Month_FromMoneyforward(SelectedCompanyMixin, TransactionMixin, FormView):
    template_name = "scoreai/import_fiscal_summary_month_MF.html"
    form_class = MoneyForwardCsvUploadForm_Month
    success_url = reverse_lazy('fiscal_summary_month_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['fiscal_year'].queryset = FiscalSummary_Year.objects.filter(company=self.this_company).order_by('-year')
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '月次PL'
        context['show_title_card'] = False
        context['fiscal_years'] = FiscalSummary_Year.objects.filter(company=self.this_company)
        return context

    def form_valid(self, form):
        fiscal_year = form.cleaned_data['fiscal_year']
        csv_file = form.cleaned_data['file']
        override_flag = form.cleaned_data.get('override_flag', False)

        try:
            # エンコーディング自動検出でCSVを読み込む
            csv_data, encoding = read_csv_with_auto_encoding(csv_file)
            
            if not csv_data:
                messages.error(self.request, 'CSVファイルが空です。')
                return self.form_invalid(form)
            
            # CSV構造の検証（マネーフォワードのCSVは列名が異なる可能性があるため、柔軟に検証）
            # 最低限、データが存在することを確認
            is_valid, error_msg = validate_csv_structure(
                csv_data,
                expected_columns=None,  # 列名のチェックをスキップ（マネーフォワードの形式に依存）
                min_rows=2
            )
            
            if not is_valid:
                messages.error(self.request, f'CSVファイルの構造が不正です: {error_msg}')
                return self.form_invalid(form)
            
            # デバッグ用: ヘッダー行をログに記録
            if csv_data:
                logger.info(f"CSV header row: {csv_data[0]}")
            
            # CSVデータを処理
            csv_reader = iter(csv_data)
            header = next(csv_reader)  # ヘッダー行を読み飛ばす
            
            # デバッグ用: ヘッダー行をログとメッセージに記録
            logger.info(f"CSV header row: {header}")
            logger.info(f"CSV header length: {len(header)}")
            
            # ヘッダー行が空または短すぎる場合のチェック
            if not header or len(header) < 2:
                messages.error(
                    self.request, 
                    f'CSVファイルのヘッダー行が不正です。ヘッダー: {header}'
                )
                return self.form_invalid(form)

            # ヘッダーから月度情報を取得
            # 最初の2列をスキップ ("科目", "行" またはマネーフォワードの形式)
            # マネーフォワードのCSVは最初の列が科目名、2列目が行番号の可能性がある
            header_columns = header[2:] if len(header) > 2 else header
            months = []
            current_month = 1

            for h in header_columns:
                if h == "決算整理":
                    months.append(13)
                elif h == "合計":
                    # "合計"が出てきたら、その列の処理をせずに終了
                    break
                else:
                    months.append(current_month)
                    current_month += 1
                    # 最大13ヶ月まで処理
                    if current_month > 13:
                        break

            # 読み込むデータの列数に合わせて、データ格納用リストの初期化
            num_columns = len(months)
            sales_data = [0] * num_columns
            gross_profit_data = [0] * num_columns
            operating_profit_data = [0] * num_columns
            ordinary_profit_data = [0] * num_columns

            # データ行を処理（元のロジックに戻す）
            for row in csv_reader:
                label = row[0]  # ラベルは最初の列にある

                if label == "売上高合計":
                    sales_data = [
                        int(Decimal(col.replace(',', '')) // 1000) if col else 0
                        for col in row[2:2+num_columns]
                    ]
                elif label == "売上総利益":
                    gross_profit_data = [
                        int(Decimal(col.replace(',', '')) // 1000) if col else 0
                        for col in row[2:2+num_columns]
                    ]
                elif label == "営業利益":
                    operating_profit_data = [
                        int(Decimal(col.replace(',', '')) // 1000) if col else 0
                        for col in row[2:2+num_columns]
                    ]
                elif label == "経常利益":
                    ordinary_profit_data = [
                        int(Decimal(col.replace(',', '')) // 1000) if col else 0
                        for col in row[2:2+num_columns]
                    ]
                elif label == "当期純利益":
                    # "当期純利益"が出てきたら読み込み終了
                    break
            

            # 月度データを生成
            imported_count = 0
            updated_count = 0
            for month, sales, gross_profit, operating_profit, ordinary_profit in zip(
                months, sales_data, gross_profit_data, operating_profit_data, ordinary_profit_data
            ):
                # 実績データ（is_budget=False）のみをチェック
                existing_actual = FiscalSummary_Month.objects.filter(
                    fiscal_summary_year=fiscal_year,
                    period=month,
                    is_budget=False
                ).first()

                if existing_actual and not override_flag:
                    messages.error(
                        self.request,
                        f'{fiscal_year.year}年の{month}月の実績データは既に存在します。上書きする場合は「既存データを上書きする」を選択してください。'
                    )
                    return self.form_invalid(form)
                else:
                    # 実績データとしてインポート（is_budget=False）
                    # unique_togetherにis_budgetが含まれているため、予算データとは別レコードとして作成される
                    obj, created = FiscalSummary_Month.objects.update_or_create(
                        fiscal_summary_year=fiscal_year,
                        period=month,
                        is_budget=False,  # 実績データのみを対象
                        defaults={
                            'sales': sales,
                            'gross_profit': gross_profit,
                            'operating_profit': operating_profit,
                            'ordinary_profit': ordinary_profit,
                        }
                    )
                    
                    if created:
                        imported_count += 1
                    else:
                        updated_count += 1

            # 成功メッセージを詳細に表示
            if imported_count > 0 and updated_count > 0:
                messages.success(
                    self.request, 
                    f'✅ CSVファイルが正常にインポートされました！<br>'
                    f'<strong>新規登録:</strong> {imported_count}件<br>'
                    f'<strong>更新:</strong> {updated_count}件<br>'
                    f'<strong>エンコーディング:</strong> {encoding}',
                    extra_tags='safe'
                )
            elif imported_count > 0:
                messages.success(
                    self.request, 
                    f'✅ CSVファイルが正常にインポートされました！<br>'
                    f'<strong>新規登録:</strong> {imported_count}件<br>'
                    f'<strong>エンコーディング:</strong> {encoding}',
                    extra_tags='safe'
                )
            elif updated_count > 0:
                messages.success(
                    self.request, 
                    f'✅ CSVファイルが正常にインポートされました！<br>'
                    f'<strong>更新:</strong> {updated_count}件<br>'
                    f'<strong>エンコーディング:</strong> {encoding}',
                    extra_tags='safe'
                )
            else:
                messages.warning(
                    self.request, 
                    f'⚠️ CSVファイルは処理されましたが、データが登録されませんでした。<br>'
                    f'<strong>エンコーディング:</strong> {encoding}',
                    extra_tags='safe'
                )
        except UnicodeDecodeError as e:
            messages.error(
                self.request, 
                f'CSVファイルのエンコーディングを検出できませんでした。UTF-8またはShift-JIS形式のファイルをアップロードしてください。'
            )
            logger.error(f"CSV encoding error: {e}", exc_info=True)
            return self.form_invalid(form)
        except ValueError as e:
            messages.error(self.request, f'CSVファイルの形式が不正です: {str(e)}')
            logger.error(f"CSV validation error: {e}", exc_info=True)
            return self.form_invalid(form)
        except Exception as e:
            messages.error(
                self.request, 
                f'CSVファイルの処理中にエラーが発生しました: {str(e)}'
            )
            logger.error(f"CSV processing error: {e}", exc_info=True, extra={'user': self.request.user.id})
            return self.form_invalid(form)

        return super().form_valid(form)
    
    def _parse_amount(self, value: str, row_number: int, column_index: int) -> int:
        """
        金額文字列をパース（エラーハンドリング付き）
        
        Args:
            value: 金額文字列
            row_number: 行番号（エラーメッセージ用）
            column_index: 列インデックス（エラーメッセージ用）
            
        Returns:
            パースされた金額（千円単位）
        """
        if not value or value.strip() == '':
            return 0
        
        try:
            # カンマと全角スペースを除去
            cleaned_value = value.replace(',', '').replace('，', '').replace(' ', '').replace('　', '')
            amount = Decimal(cleaned_value)
            return int(amount // 1000)
        except (ValueError, InvalidOperation) as e:
            raise ValueError(f"列{column_index}: 数値のパースに失敗しました（値: '{value}'）")


# Moneyfowardの試算表（貸借対照表と損益計算書）をアップしたらそのまま変換してインポートする
class ImportFiscalSummary_Year_FromMoneyforward(SelectedCompanyMixin, TransactionMixin, FormView):
    template_name = "scoreai/import_fiscal_summary_year_MF.html"
    form_class = MoneyForwardCsvUploadForm_Year
    success_url = None  # リダイレクトしない

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # 会社の年度を設定
        form.fields['fiscal_year'].queryset = FiscalSummary_Year.objects.filter(company=self.this_company).order_by('-year')
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '年次決算'
        context['show_title_card'] = False
        return context

    def form_invalid(self, form):
        logger.error(f"ImportFiscalSummary_Year_FromMoneyforward: form_invalid called. Errors: {form.errors}")
        return super().form_invalid(form)

    def form_valid(self, form):
        logger.info("ImportFiscalSummary_Year_FromMoneyforward: form_valid called")
        csv_file = form.cleaned_data.get('file')
        override_flag = form.cleaned_data.get('override_flag', False)
        
        if not csv_file:
            messages.error(self.request, 'CSVファイルが選択されていません。')
            logger.error("ImportFiscalSummary_Year_FromMoneyforward: No file provided")
            return self.form_invalid(form)

        try:
            # エンコーディング自動検出でCSVを読み込む
            csv_data, encoding = read_csv_with_auto_encoding(csv_file)
            
            if not csv_data:
                messages.error(self.request, 'CSVファイルが空です。')
                return self.form_invalid(form)
            
            # CSV構造の検証
            is_valid, error_msg = validate_csv_structure(
                csv_data,
                min_rows=2
            )
            
            if not is_valid:
                messages.error(self.request, f'CSVファイルの構造が不正です: {error_msg}')
                return self.form_invalid(form)
            
            # CSVデータを処理
            csv_reader = iter(csv_data)

            # 1行目の3列目から年度を取得（エラーハンドリング強化）
            first_row = next(csv_reader)
            
            if len(first_row) < 3:
                messages.error(
                    self.request, 
                    f'CSVファイルの1行目の列数が不足しています（最低3列必要）。実際の列数: {len(first_row)}'
                )
                return self.form_invalid(form)
            
            try:
                fiscal_year_str = first_row[2]
                if len(fiscal_year_str) < 8:
                    messages.error(
                        self.request, 
                        f'年度情報の形式が不正です。3列目の値: "{fiscal_year_str}"'
                    )
                    return self.form_invalid(form)
                fiscal_year = fiscal_year_str[4:8]
                
                # 年度が数値か確認
                int(fiscal_year)  # 数値でない場合はValueErrorが発生
            except (IndexError, ValueError) as e:
                messages.error(
                    self.request, 
                    f'年度の取得に失敗しました。CSVファイルの1行目3列目に年度情報が含まれているか確認してください。'
                )
                logger.error(f"Fiscal year extraction error: {e}", exc_info=True)
                return self.form_invalid(form)

            # 実績データ（is_budget=False）のみをチェック
            existing_actual = FiscalSummary_Year.objects.filter(
                year=fiscal_year, 
                company=self.this_company,
                is_budget=False  # 実績データのみをチェック
            ).first()
            
            if existing_actual:
                if not override_flag:
                    messages.error(
                        self.request,
                        f'{fiscal_year}年の実績データは既に存在します。上書きする場合は「既存データを上書きする」を選択してください。'
                    )
                    return self.form_invalid(form)
            else:
                # 実績データが存在しない場合は新規作成（is_budget=Falseを明示的に指定）
                # unique_togetherにis_budgetが含まれているため、予算データが存在しても
                # 実績データとして別レコードを作成できる
                # versionは常に1で固定（defaultsに含めない、モデルのdefault=1が適用される）
                FiscalSummary_Year.objects.get_or_create(
                    year=fiscal_year,
                    company=self.this_company,
                    is_budget=False,  # 実績データとして明示的に指定
                    defaults={
                        'is_draft': True,
                    }
                )

            current_line = 0 # 行数を取得するための変数
            sales_line = 0
            gross_profit_line = 0
            operating_profit_line = 0
            ordinary_profit_line = 0

            # 更新内容を入れるための辞書を用意
            data_dict = {}

            # 項目名とフィールド名のマッピング
            label_field_mapping = {
                "現金及び預金合計": "cash_and_deposits",
                "売上債権合計": "accounts_receivable",
                "棚卸資産合計": "inventory",
                "短期貸付金": "short_term_loans_receivable",
                "流動資産合計": "total_current_assets",
                "土地": "land",
                "建物": "buildings",
                "附属設備": "buildings",
                "建物附属設備": "buildings",
                "機械及び装置": "machinery_equipment",
                "器具備品": "machinery_equipment",
                "車両": "vehicles",
                "車両運搬具": "vehicles",
                "有形固定資産合計": "total_tangible_fixed_assets",
                "のれん": "goodwill",
                "無形固定資産合計": "total_intangible_fixed_assets",
                "長期貸付金": "long_term_loans_receivable",
                "投資その他の資産合計": "investment_other_assets",
                "固定資産合計": "total_fixed_assets",
                "繰延資産合計": "deferred_assets",
                "資産の部合計": "total_assets",
                "仕入債務合計": "accounts_payable",
                "短期借入金": "short_term_loans_payable",
                "流動負債合計": "total_current_liabilities",
                "長期借入金": "long_term_loans_payable",
                "役員借入金": "directors_loan",
                #役員貸付を入れて、計算させる
                "役員等借入金": "directors_loan",
                "固定負債合計": "total_long_term_liabilities",
                "負債の部合計": "total_liabilities",
                "資本金合計": "capital_stock",
                "資本剰余金合計": "capital_surplus",
                "利益剰余金合計": "retained_earnings",
                "株主資本合計": "total_stakeholder_equity",
                "評価・換算差額等合計": "valuation_and_translation_adjustment",
                "新株予約権合計": "new_shares_reserve",
                "純資産の部合計": "total_net_assets",
                "売上高合計": "sales",
                "売上総利益": "gross_profit",
                "役員報酬": "directors_compensation",
                "給料": "payroll_expense",
                "給与": "payroll_expense",
                "雑給": "payroll_expense",
                "給料賃金": "payroll_expense",
                "営業利益": "operating_profit",
                "営業損失": "operating_profit",
                "営業外収益合計": "other_income",
                "営業外費用合計": "other_loss",
                "経常利益": "ordinary_profit",
                "経常損失": "ordinary_profit",
                "特別利益合計": "extraordinary_income",
                "特別損失合計": "extraordinary_loss",
                "当期純利益": "net_profit",
                "法人税等": "income_taxes",
                "支払利息": "interest_expense",
            }

            errors = []
            for row in csv_reader:
                current_line += 1
                # 空行または不完全な行をスキップ
                if not row or len(row) < 1:
                    logger.warning(f"空行または不完全な行が検出されました（行番号: {current_line}）")
                    continue

                # 項目名の決定（エラーハンドリング強化）
                try:
                    if len(row) >= 5 and row[0] != '':
                        mapping_label = row[0]
                    elif len(row) >= 2 and row[1] != '':
                        mapping_label = row[1]
                    else:
                        logger.warning(f"この行はスキップします（行番号: {current_line}）")
                        continue

                    # 金額のパース（エラーハンドリング強化）
                    if len(row) < 6:
                        errors.append(f"行{current_line}: 列数が不足しています（最低6列必要）。実際の列数: {len(row)}")
                        continue
                    
                    value_str = row[5] if row[5] else '0'
                    try:
                        cleaned_value = value_str.replace(',', '').replace('，', '').replace(' ', '').replace('　', '')
                        value = int(Decimal(cleaned_value) // 1000)
                    except (ValueError, InvalidOperation) as e:
                        errors.append(f"行{current_line}列6: 数値のパースに失敗しました（値: '{value_str}'）")
                        continue
                except Exception as e:
                    errors.append(f"行{current_line}: 処理中にエラーが発生しました: {str(e)}")
                    logger.error(f"Row {current_line} processing error: {e}", exc_info=True)
                    continue
                
                if mapping_label in label_field_mapping:
                    field_name = label_field_mapping[mapping_label]
                    data_dict[field_name] = data_dict.get(field_name, 0) + value
                    logger.warning(f"項目名に従って処理をしました【行番号: {current_line} 科目：{mapping_label}】= {value}")
                    if mapping_label == "売上高合計":
                        sales_line = current_line
                    elif mapping_label == "売上総利益":
                        gross_profit_line = current_line
                    elif mapping_label in ["営業利益", "営業損失"]:
                        operating_profit_line = current_line
                    elif mapping_label in ["経常利益", "経常損失"]:
                        ordinary_profit_line = current_line
                elif "償却" in mapping_label:
                    if gross_profit_line == 0:
                        data_dict['depreciation_cogs'] = data_dict.get('depreciation_cogs', 0) + value
                    elif operating_profit_line == 0:
                        if mapping_label == "減価償却費":
                            data_dict['depreciation_expense'] = data_dict.get('depreciation_expense', 0) + value
                        else:
                            data_dict['other_amortization_expense'] = data_dict.get('other_amortization_expense', 0) + value
                    elif ordinary_profit_line == 0:
                        data_dict['non_operating_amortization_expense'] = data_dict.get('non_operating_amortization_expense', 0) + value
                else:
                    logger.warning(f"条件に一致しない行（行番号: {current_line}）： {row}")
                    continue

            # データを更新（実績データとして、is_budget=Falseを明示的に指定）
            data_dict['is_budget'] = False  # 実績データとして明示的に指定
            # versionは常に1で固定（defaultsに含めない）
            fiscal_summary_year, created = FiscalSummary_Year.objects.update_or_create(
                year=fiscal_year,
                company=self.this_company,
                is_budget=False,  # 実績データのみを対象
                defaults=data_dict
            )

            # ループ終了後の処理
            logger.info("CSVファイルの全行を正常に処理しました。")

            # 更新された項目数をカウント
            updated_fields_count = len([k for k, v in data_dict.items() if v != 0])
            
            # 成功メッセージを詳細に表示
            if created:
                messages.success(
                    self.request, 
                    f'✅ CSVファイルが正常にインポートされました！<br>'
                    f'<strong>年度:</strong> {fiscal_year}年<br>'
                    f'<strong>新規登録:</strong> 下書きデータとして保存されました<br>'
                    f'<strong>更新項目数:</strong> {updated_fields_count}項目<br>'
                    f'<strong>エンコーディング:</strong> {encoding}<br>'
                    f'<small class="text-muted">適宜必要な情報を追加してください。</small>',
                    extra_tags='safe'
                )
            else:
                messages.success(
                    self.request, 
                    f'✅ CSVファイルが正常にインポートされました！<br>'
                    f'<strong>年度:</strong> {fiscal_year}年<br>'
                    f'<strong>更新:</strong> 既存データを更新しました<br>'
                    f'<strong>更新項目数:</strong> {updated_fields_count}項目<br>'
                    f'<strong>エンコーディング:</strong> {encoding}',
                    extra_tags='safe'
                )

        except UnicodeDecodeError as e:
            messages.error(
                self.request, 
                f'CSVファイルのエンコーディングを検出できませんでした。UTF-8またはShift-JIS形式のファイルをアップロードしてください。'
            )
            logger.error(f"CSV encoding error: {e}", exc_info=True)
            return self.form_invalid(form)
        except ValueError as e:
            messages.error(self.request, f'CSVファイルの形式が不正です: {str(e)}')
            logger.error(f"CSV validation error: {e}", exc_info=True)
            return self.form_invalid(form)
        except Exception as e:
            error_detail = f'CSVファイルの処理中にエラーが発生しました: {str(e)}'
            if 'current_line' in locals():
                error_detail += f' (行番号: {current_line})'
            if 'mapping_label' in locals():
                error_detail += f' (項目名: {mapping_label})'
            messages.error(self.request, error_detail)
            logger.error(f"CSV processing error: {e}", exc_info=True, extra={'user': self.request.user.id})
            return self.form_invalid(form)

        # 成功時も同じページに留まり、メッセージを表示する
        # フォームをリセットして再表示
        form = self.form_class()
        # 会社情報をフォームに渡す
        form.fields['fiscal_year'].queryset = FiscalSummary_Year.objects.filter(company=self.this_company).order_by('-year')
        context = self.get_context_data(form=form)
        return render(self.request, self.template_name, context)


##########################################################################
###                    Debt の View                                    ###
##########################################################################

class DebtCreateView(SelectedCompanyMixin, TransactionMixin, CreateView):
    model = Debt
    form_class = DebtForm
    template_name = 'scoreai/debt_form.html'
    success_url = reverse_lazy('debts_all')

    def form_valid(self, form):
        form.instance.company = self.this_company
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'新しい借り入れが登録されました。金融機関: {form.instance.financial_institution}, '
            f'借入日: {form.instance.issue_date}, 借入額: {form.instance.principal:,}円'
        )
        return response

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # フィールドにクラスを追加
        form.fields['financial_institution'].widget.attrs.update({'class': 'form-control select2'})
        for field in form.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '新規借入登録'
        context['show_title_card'] = False
        return context


class DebtDetailView(SelectedCompanyMixin, DetailView):
    model = Debt
    template_name = 'scoreai/debt_detail.html'
    context_object_name = 'debt'

    def get_queryset(self):
        """N+1問題を回避するため、関連オブジェクトを事前取得"""
        return Debt.objects.select_related(
            'financial_institution',
            'secured_type',
            'company'
        ).filter(company=self.this_company)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debt_list, debt_list_totals, debt_list_nodisplay, debt_list_rescheduled, debt_list_finished = get_debt_list(self.this_company)
        debt_list_byBank = get_debt_list_byAny('financial_institution', debt_list)
        debt_list_bySecuredType = get_debt_list_byAny('secured_type', debt_list)

        # 自分のデータのfinancial_institutionでフィルタをかけたdebt_list
        self_debt = self.get_object()
        debt_list_sameBank = [debt for debt in debt_list if debt['financial_institution'] == self_debt.financial_institution]

        context.update({            
            'title': '借入管理',
            'debt_list': debt_list_sameBank,
            'debt_list_totals': debt_list_totals,
            'debt_list_rescheduled': debt_list_rescheduled,
            'debt_list_finished': debt_list_finished,
            'debt_list_nodisplay': debt_list_nodisplay,
            'today': timezone.now().date(),
            'show_title_card': False,  # タイトルカードを非表示（他の借入管理ページと統一）
        })
        return context


class DebtUpdateView(SelectedCompanyMixin, TransactionMixin, UpdateView):
    model = Debt
    form_class = DebtForm
    template_name = 'scoreai/debt_form.html'
    
    def get_success_url(self):
        return reverse_lazy('debt_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, '借入情報を更新しました。')
        return response

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # フィールドにクラスを追加
        form.fields['financial_institution'].widget.attrs.update({'class': 'form-control select2'})
        for field in form.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
        
        # 日付フィールドに自動的に 'datepicker' クラスを追加
        for field_name, field in form.fields.items():
            if isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({
                    'class': 'form-control datepicker',
                    'placeholder': 'YYYY-MM-DD'
                })

        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['debt'] = self.object
        context['title'] = '借入管理'
        context['show_title_card'] = False
        return context


class DebtDeleteView(SelectedCompanyMixin, DeleteView):
    model = Debt
    template_name = 'scoreai/debt_confirm_delete.html'
    context_object_name = 'debt'
    success_url = reverse_lazy('debts_all')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, '借入を削除しました。')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '借入管理'
        context['show_title_card'] = False
        return context

class DebtsAllListView(SelectedCompanyMixin, ListView):
    model = Debt
    template_name = 'scoreai/debt_list_all.html'
    context_object_name = 'debt_list'
    paginate_by = 20

    def get_queryset(self):
        """検索・フィルタリング機能付きクエリセット（django-filter使用）"""
        from .filters import DebtFilter
        
        queryset = Debt.objects.filter(
            company=self.this_company
        ).select_related(
            'financial_institution',
            'secured_type',
            'company'
        )
        
        # django-filterを使用したフィルタリング
        debt_filter = DebtFilter(
            self.request.GET,
            queryset=queryset,
            company=self.this_company
        )
        queryset = debt_filter.qs
        
        # ソート機能
        order_by = self.request.GET.get('order_by', '-issue_date')
        if order_by:
            queryset = queryset.order_by(order_by)
        
        return queryset

    def get_context_data(self, **kwargs):
        from .filters import DebtFilter
        
        context = super().get_context_data(**kwargs)
        debt_list, debt_list_totals, debt_list_nodisplay, debt_list_rescheduled, debt_list_finished = get_debt_list(self.this_company)
        
        # django-filterを使用したフィルタリング
        queryset = Debt.objects.filter(company=self.this_company)
        debt_filter = DebtFilter(
            self.request.GET,
            queryset=queryset,
            company=self.this_company
        )
        context['filter'] = debt_filter
        
        # 検索・フィルタリング用のコンテキスト（後方互換性のため保持）
        context['financial_institutions'] = FinancialInstitution.objects.all().order_by('name')
        context['secured_types'] = SecuredType.objects.all().order_by('name')
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_financial_institution'] = self.request.GET.get('financial_institution', '')
        context['selected_secured_type'] = self.request.GET.get('secured_type', '')
        context['selected_is_rescheduled'] = self.request.GET.get('is_rescheduled', '')
        context['selected_is_nodisplay'] = self.request.GET.get('is_nodisplay', '')
        context['order_by'] = self.request.GET.get('order_by', '-issue_date')
        debt_list_byBank = get_debt_list_byAny('financial_institution', debt_list)
        debt_list_bySecuredType = get_debt_list_byAny('secured_type', debt_list)
        debt_list_bySecuredByManagement = get_debt_list_byAny('is_securedby_management', debt_list)
        debt_list_byCollateraled = get_debt_list_byAny('is_collateraled', debt_list)
        debt_list_byBankAndSecuredType = get_debt_list_byBankAndSecuredType(debt_list)
        # Calculate weighted_average_interest using service layer
        from .services.debt_service import DebtService
        weighted_average_interest = DebtService.calculate_weighted_average_interest(
            debt_list_totals['total_interest_amount_monthly'],
            debt_list_totals['total_balances_monthly']
        )

        context.update({
            'title': '借入管理',
            'debt_list': debt_list,
            'debt_list_totals': debt_list_totals,
            'debt_list_byBank': debt_list_byBank,
            'debt_list_byBankAndSecuredType': debt_list_byBankAndSecuredType,
            'debt_list_bySecuredType': debt_list_bySecuredType,
            'debt_list_bySecuredByManagement': debt_list_bySecuredByManagement,
            'debt_list_byCollateraled': debt_list_byCollateraled,
            'debt_list_rescheduled': debt_list_rescheduled,
            'debt_list_finished': debt_list_finished,
            'debt_list_nodisplay': debt_list_nodisplay,
            'weighted_average_interest': weighted_average_interest,
            'today': timezone.now().date(),
            'show_title_card': False,  # タイトルカードを非表示（他の借入管理ページと統一）
        })
        return context


class DebtsByBankListView(SelectedCompanyMixin, ListView):
    model = Debt
    template_name = 'scoreai/debt_list_byBank.html'
    context_object_name = 'debt_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debt_list, debt_list_totals, debt_list_nodisplay, debt_list_rescheduled, debt_list_finished = get_debt_list(self.this_company)
        debt_list_byBank = get_debt_list_byAny('financial_institution', debt_list)
        debt_list_bySecuredType = get_debt_list_byAny('secured_type', debt_list)
        debt_list_byBankAndSecuredType = get_debt_list_byBankAndSecuredType(debt_list)

        # Calculate weighted average interest rate for each bank
        for bank_debt in debt_list_byBank:
            # Calculate weighted average interest rate using the same formula as weighted_average_interest
            # Formula: 12 * interest_amount_monthly[0] / balances_monthly[0] * 100 if balance != 0 else 0
            # Multiply by 100 to convert to percentage
            if bank_debt['balances_monthly'][0] != 0:
                bank_debt['weighted_average_interest'] = (12 * bank_debt['interest_amount_monthly'][0]) / bank_debt['balances_monthly'][0] * 100
            else:
                bank_debt['weighted_average_interest'] = 0

        context.update({
            'title': '借入管理',
            'debt_list': debt_list,
            'debt_list_totals': debt_list_totals,
            'debt_list_byBank': debt_list_byBank,
            'show_title_card': False,  # タイトルカードを非表示（他の借入管理ページと統一）
        })
        return context


class DebtsByBankDetailListView(SelectedCompanyMixin, ListView):
    model = Debt
    template_name = 'scoreai/debt_list_byBank_detail.html'
    context_object_name = 'debt_list'

    def get_queryset(self):
        financial_institution_id = self.kwargs.get('financial_institution_id')
        debt_list, debt_list_totals, debt_list_nodisplay, debt_list_rescheduled, debt_list_finished = get_debt_list(self.this_company)
        # 特定の金融機関の借入のみをフィルタリング
        filtered_debt_list = [
            debt for debt in debt_list 
            if str(debt['financial_institution'].id) == str(financial_institution_id)
        ]
        return filtered_debt_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        financial_institution_id = self.kwargs.get('financial_institution_id')
        
        # 金融機関情報を取得
        from scoreai.models import FinancialInstitution
        try:
            financial_institution = FinancialInstitution.objects.get(id=financial_institution_id)
        except FinancialInstitution.DoesNotExist:
            financial_institution = None

        debt_list, debt_list_totals, debt_list_nodisplay, debt_list_rescheduled, debt_list_finished = get_debt_list(self.this_company)
        filtered_debt_list = [
            debt for debt in debt_list 
            if str(debt['financial_institution'].id) == str(financial_institution_id)
        ]

        # この金融機関の合計を計算
        bank_totals = {
            'principal': sum(d['principal'] for d in filtered_debt_list),
            'monthly_repayment': sum(d['monthly_repayment'] for d in filtered_debt_list),
            'balances_monthly': [sum(d['balances_monthly'][i] for d in filtered_debt_list) for i in range(12)],
            'balance_fy1': sum(d['balance_fy1'] for d in filtered_debt_list),
        }

        from django.utils import timezone
        context.update({
            'title': '借入管理',
            'financial_institution': financial_institution,
            'debt_list': filtered_debt_list,
            'debt_list_totals': debt_list_totals,
            'bank_totals': bank_totals,
            'today': timezone.now().date(),
            'show_title_card': False,  # タイトルカードを非表示（他の借入管理ページと統一）
        })
        return context


class DebtsBySecuredTypeListView(SelectedCompanyMixin, ListView):
    model = Debt
    template_name = 'scoreai/debt_list_bySecuredType.html'
    context_object_name = 'debt_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debt_list, debt_list_totals, debt_list_nodisplay, debt_list_rescheduled, debt_list_finished = get_debt_list(self.this_company)
        debt_list_bySecuredType = get_debt_list_byAny('secured_type', debt_list)
        debt_list_byBankAndSecuredType = get_debt_list_byBankAndSecuredType(debt_list)

        # Calculate weighted average interest rate for each secured type
        for secured_debt in debt_list_bySecuredType:
            # Calculate weighted average interest rate using the same formula as weighted_average_interest
            # Formula: 12 * interest_amount_monthly[0] / balances_monthly[0] * 100 if balance != 0 else 0
            # Multiply by 100 to convert to percentage
            if secured_debt['balances_monthly'][0] != 0:
                secured_debt['weighted_average_interest'] = (12 * secured_debt['interest_amount_monthly'][0]) / secured_debt['balances_monthly'][0] * 100
            else:
                secured_debt['weighted_average_interest'] = 0

        # Calculate weighted average interest rate for each bank and secured type combination
        for bank_secured_debt in debt_list_byBankAndSecuredType:
            # Calculate weighted average interest rate using the same formula as weighted_average_interest
            # Formula: 12 * interest_amount_monthly[0] / balances_monthly[0] * 100 if balance != 0 else 0
            # Multiply by 100 to convert to percentage
            if bank_secured_debt['balances_monthly'][0] != 0:
                bank_secured_debt['weighted_average_interest'] = (12 * bank_secured_debt['interest_amount_monthly'][0]) / bank_secured_debt['balances_monthly'][0] * 100
            else:
                bank_secured_debt['weighted_average_interest'] = 0

        context.update({
            'title': '借入管理',
            'debt_list_totals': debt_list_totals,
            'debt_list_bySecuredType': debt_list_bySecuredType,
            'debt_list_byBankAndSecuredType': debt_list_byBankAndSecuredType,
            'show_title_card': False,  # タイトルカードを非表示（他の借入管理ページと統一）
        })
        return context


class DebtsBySecuredTypeDetailListView(SelectedCompanyMixin, ListView):
    model = Debt
    template_name = 'scoreai/debt_list_bySecuredType_detail.html'
    context_object_name = 'debt_list'

    def get_queryset(self):
        secured_type_id = self.kwargs.get('secured_type_id')
        debt_list, debt_list_totals, debt_list_nodisplay, debt_list_rescheduled, debt_list_finished = get_debt_list(self.this_company)
        # 特定の保証タイプの借入のみをフィルタリング
        filtered_debt_list = [
            debt for debt in debt_list 
            if str(debt['secured_type'].id) == str(secured_type_id)
        ]
        return filtered_debt_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        secured_type_id = self.kwargs.get('secured_type_id')
        
        # 保証タイプ情報を取得
        from scoreai.models import SecuredType
        try:
            secured_type = SecuredType.objects.get(id=secured_type_id)
        except SecuredType.DoesNotExist:
            secured_type = None

        debt_list, debt_list_totals, debt_list_nodisplay, debt_list_rescheduled, debt_list_finished = get_debt_list(self.this_company)
        filtered_debt_list = [
            debt for debt in debt_list 
            if str(debt['secured_type'].id) == str(secured_type_id)
        ]

        # この保証タイプの合計を計算
        secured_type_totals = {
            'principal': sum(d['principal'] for d in filtered_debt_list),
            'monthly_repayment': sum(d['monthly_repayment'] for d in filtered_debt_list),
            'balances_monthly': [sum(d['balances_monthly'][i] for d in filtered_debt_list) for i in range(12)],
            'balance_fy1': sum(d['balance_fy1'] for d in filtered_debt_list),
        }

        from django.utils import timezone
        context.update({
            'title': '借入管理',
            'secured_type': secured_type,
            'debt_list': filtered_debt_list,
            'debt_list_totals': debt_list_totals,
            'secured_type_totals': secured_type_totals,
            'today': timezone.now().date(),
            'show_title_card': False,  # タイトルカードを非表示（他の借入管理ページと統一）
        })
        return context


class DebtsArchivedListView(SelectedCompanyMixin, ListView):
    model = Debt
    template_name = 'scoreai/debt_list_archived.html'
    context_object_name = 'debt_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debt_list, debt_list_totals, debt_list_nodisplay, debt_list_rescheduled, debt_list_finished = get_debt_list(self.this_company)
        context.update({
            'title': '借入管理',
            'debt_list_nodisplay': debt_list_nodisplay,
            'show_title_card': False,  # タイトルカードを非表示（他の借入管理ページと統一）
        })
        return context

##########################################################################
###                 MeetingMinutes の View                             ###
##########################################################################

class MeetingMinutesCreateView(SelectedCompanyMixin, CreateView):
    model = MeetingMinutes
    form_class = MeetingMinutesForm
    template_name = 'scoreai/meeting_minutes_form.html'
    success_url = reverse_lazy('meeting_minutes_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # companyとcreated_byフィールドを非表示にし、変更不可能にする
        form.fields['company'].widget = forms.HiddenInput()
        form.fields['created_by'].widget = forms.HiddenInput()
        # dateフィールドのデフォルト値を今日の日付に設定
        form.fields['meeting_date'].initial = timezone.now().date()
        return form

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.company = self.this_company
        return super().form_valid(form)

    def get_initial(self):
        initial = super().get_initial()
        initial['company'] = self.this_company
        initial['created_by'] = self.request.user
        initial['meeting_date'] = timezone.now().date()
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '新規ノート作成'
        context['show_title_card'] = False
        return context

class MeetingMinutesUpdateView(SelectedCompanyMixin, UpdateView):
    model = MeetingMinutes
    form_class = MeetingMinutesForm
    template_name = 'scoreai/meeting_minutes_form.html'
    success_url = reverse_lazy('meeting_minutes_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # companyとcreated_byフィールドを非表示にし、変更不可能にする
        form.fields['company'].widget = forms.HiddenInput()
        form.fields['created_by'].widget = forms.HiddenInput()
        return form

    def form_valid(self, form):
        # UpdateViewでは、既存のcompanyとcreated_byを保持する
        form.instance.company = self.object.company
        form.instance.created_by = self.object.created_by
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'ノート（議事録）'
        context['show_title_card'] = False
        return context


class MeetingMinutesListView(SelectedCompanyMixin, ListView):
    model = MeetingMinutes
    template_name = 'scoreai/meeting_minutes_list.html'
    context_object_name = 'meeting_minutes'
    paginate_by = 10

    def get_queryset(self):
        queryset = MeetingMinutes.objects.filter(
            company=self.this_company
        ).select_related('company', 'created_by').order_by('-meeting_date')
        date = self.request.GET.get('date')
        keyword = self.request.GET.get('keyword')

        if date:
            queryset = queryset.filter(meeting_date=datetime.strptime(date, '%Y-%m-%d').date())
        
        if keyword:
            queryset = queryset.filter(
                Q(notes__icontains=keyword) |
                Q(created_by__username__icontains=keyword)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company_id'] = self.this_company.id
        context['title'] = 'ノート（議事録）'
        context['show_title_card'] = False  # タイトルカードを非表示（他のページと統一）
        return context
        


class MeetingMinutesDetailView(SelectedCompanyMixin, DetailView):
    model = MeetingMinutes
    template_name = 'scoreai/meeting_minutes_detail.html'
    context_object_name = 'meeting_minutes'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company_id'] = self.this_company.id
        context['title'] = 'ノート（議事録）'
        context['show_title_card'] = False
        # 現在の議事録を取得
        current_meeting = self.object
        
        # 同じ会社の直近5件の議事録を取得（現在の議事録を除く）
        recent_meetings = MeetingMinutes.objects.filter(
            company=current_meeting.company
        ).select_related('company', 'created_by').exclude(
            id=current_meeting.id
        ).order_by('-meeting_date')[:5]
        
        context['recent_meetings'] = recent_meetings
        return context


class MeetingMinutesDeleteView(SelectedCompanyMixin, DeleteView):
    model = MeetingMinutes
    template_name = 'scoreai/meeting_minutes_confirm_delete.html'
    success_url = reverse_lazy('meeting_minutes_list')

    def get_queryset(self):
        return MeetingMinutes.objects.filter(
            company=self.this_company
        ).select_related('company', 'created_by')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company_id'] = self.this_company.id
        context['title'] = 'ノート（議事録）'
        context['show_title_card'] = False
        return context


class MeetingMinutesImportView(SelectedCompanyMixin, TransactionMixin, FormView):
    """Google Documentsからエクスポートしたファイルをインポート（複数ファイル対応）"""
    form_class = MeetingMinutesImportForm
    template_name = 'scoreai/meeting_minutes_import.html'
    success_url = reverse_lazy('meeting_minutes_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '議事録インポート'
        context['show_title_card'] = False
        return context

    def _extract_date_from_filename(self, filename):
        """ファイル名から日付を抽出
        
        対応パターン:
        - YYYY-MM-DD_*.docx
        - YYYYMMDD_*.docx
        - YYYY年MM月DD日_*.docx
        - YYYY/MM/DD_*.docx
        """
        import re
        from datetime import datetime
        
        # YYYY-MM-DD形式
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', filename)
        if match:
            try:
                return datetime.strptime(f"{match.group(1)}-{match.group(2)}-{match.group(3)}", "%Y-%m-%d").date()
            except ValueError:
                pass
        
        # YYYYMMDD形式
        match = re.search(r'(\d{4})(\d{2})(\d{2})', filename)
        if match:
            try:
                return datetime.strptime(f"{match.group(1)}-{match.group(2)}-{match.group(3)}", "%Y-%m-%d").date()
            except ValueError:
                pass
        
        # YYYY年MM月DD日形式
        match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', filename)
        if match:
            try:
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))
                return datetime(year, month, day).date()
            except ValueError:
                pass
        
        # YYYY/MM/DD形式
        match = re.search(r'(\d{4})/(\d{2})/(\d{2})', filename)
        if match:
            try:
                return datetime.strptime(f"{match.group(1)}-{match.group(2)}-{match.group(3)}", "%Y-%m-%d").date()
            except ValueError:
                pass
        
        return None

    def _extract_text_from_file(self, uploaded_file):
        """ファイルからテキストを抽出"""
        file_name = uploaded_file.name.lower()
        
        if file_name.endswith('.docx'):
            # .docxファイルの場合
            try:
                from docx import Document
                doc = Document(uploaded_file)
                return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            except ImportError:
                raise ValueError('python-docxライブラリがインストールされていません。')
        elif file_name.endswith(('.txt', '.md')):
            # テキストファイルの場合
            uploaded_file.seek(0)
            # エンコーディングを自動検出（chardetが利用可能な場合）
            try:
                import chardet
                raw_data = uploaded_file.read()
                detected = chardet.detect(raw_data)
                encoding = detected.get('encoding', 'utf-8')
                return raw_data.decode(encoding, errors='ignore')
            except ImportError:
                # chardetがインストールされていない場合はUTF-8で試行
                uploaded_file.seek(0)
                try:
                    return uploaded_file.read().decode('utf-8')
                except UnicodeDecodeError:
                    # UTF-8で失敗した場合はshift-jisで試行
                    uploaded_file.seek(0)
                    return uploaded_file.read().decode('shift-jis', errors='ignore')
        elif file_name.endswith('.doc'):
            raise ValueError('.doc形式はサポートされていません。Google Documentsから.docx形式でエクスポートしてください。')
        else:
            raise ValueError('サポートされていないファイル形式です。.docx、.txt、.md形式のファイルをアップロードしてください。')

    def form_valid(self, form):
        uploaded_files = self.request.FILES.getlist('files')
        default_meeting_date = form.cleaned_data.get('default_meeting_date')
        category = form.cleaned_data['category']
        extract_date_from_filename = form.cleaned_data.get('extract_date_from_filename', True)
        
        if not uploaded_files:
            messages.error(self.request, 'ファイルが選択されていません。')
            return self.form_invalid(form)
        
        success_count = 0
        error_count = 0
        error_messages = []
        
        for uploaded_file in uploaded_files:
            try:
                # ファイル名から日付を抽出
                meeting_date = None
                if extract_date_from_filename:
                    meeting_date = self._extract_date_from_filename(uploaded_file.name)
                
                # 日付が抽出できなかった場合はデフォルト日付を使用
                if not meeting_date:
                    if default_meeting_date:
                        meeting_date = default_meeting_date
                    else:
                        error_messages.append(f'{uploaded_file.name}: 日付を抽出できませんでした。デフォルト日付を指定してください。')
                        error_count += 1
                        continue
                
                # テキストを抽出
                text_content = self._extract_text_from_file(uploaded_file)
                
                if not text_content or not text_content.strip():
                    error_messages.append(f'{uploaded_file.name}: ファイルが空か、テキストを抽出できませんでした。')
                    error_count += 1
                    continue
                
                # 議事録を作成
                MeetingMinutes.objects.create(
                    company=self.this_company,
                    created_by=self.request.user,
                    meeting_date=meeting_date,
                    category=category,
                    notes=text_content.strip()
                )
                success_count += 1
                
            except Exception as e:
                logger.error(f"Meeting minutes import error for {uploaded_file.name}: {e}", exc_info=True)
                error_messages.append(f'{uploaded_file.name}: {str(e)}')
                error_count += 1
        
        # 結果メッセージを表示
        if success_count > 0:
            messages.success(
                self.request,
                f'{success_count}件の議事録をインポートしました。'
            )
        
        if error_count > 0:
            for error_msg in error_messages:
                messages.error(self.request, error_msg)
        
        if success_count == 0:
            return self.form_invalid(form)
        
        return redirect('meeting_minutes_list')


##########################################################################
###                 Stakeholder_name の View                         ###
##########################################################################

class Stakeholder_nameCreateView(SelectedCompanyMixin, CreateView):
    model = Stakeholder_name
    form_class = Stakeholder_nameForm
    template_name = 'scoreai/stakeholder_name_form.html'
    success_url = reverse_lazy('stakeholder_name_list')

    def form_valid(self, form):
        form.instance.company = self.this_company
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '株主情報'
        context['show_title_card'] = False
        return context

class Stakeholder_nameUpdateView(SelectedCompanyMixin, UpdateView):
    model = Stakeholder_name
    form_class = Stakeholder_nameForm
    template_name = 'scoreai/stakeholder_name_form.html'
    success_url = reverse_lazy('stakeholder_name_list')

    def get_queryset(self):
        # 選択された会社のStakeholder_nameオブジェクトのみを返す
        return Stakeholder_name.objects.filter(
            company=self.this_company
        ).select_related('company')

    def get_success_url(self):
        return reverse_lazy('stakeholder_name_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, '株主情報を更新しました。')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stakeholder_name'] = self.object
        context['title'] = '株主情報'
        context['show_title_card'] = False
        return context

class Stakeholder_nameListView(SelectedCompanyMixin, ListView):
    model = Stakeholder_name
    template_name = 'scoreai/stakeholder_name_list.html'
    context_object_name = 'stakeholder_names'

    def get_queryset(self):
        return Stakeholder_name.objects.filter(
            company=self.this_company
        ).select_related('company')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '株主情報'
        context['show_title_card'] = False  # タイトルカードを非表示（他のページと統一）
        return context

class Stakeholder_nameDeleteView(SelectedCompanyMixin, DeleteView):
    model = Stakeholder_name
    template_name = 'scoreai/stakeholder_name_confirm_delete.html'
    success_url = reverse_lazy('stakeholder_name_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, '株主名を削除しました。')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '株主情報'
        context['show_title_card'] = False
        return context


class Stakeholder_nameDetailView(SelectedCompanyMixin, DetailView):
    model = Stakeholder_name
    template_name = 'scoreai/stakeholder_name_detail.html'
    context_object_name = 'stakeholder_name'

    def get_queryset(self):
        return Stakeholder_name.objects.filter(
            company=self.this_company
        ).select_related('company')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '株主情報'
        context['show_title_card'] = False
        context['company_id'] = self.this_company.id
        return context


##########################################################################
###                 StockEvent の View                               ###
##########################################################################
class StockEventCreateView(SelectedCompanyMixin, CreateView):
    model = StockEvent
    form_class = StockEventForm
    template_name = 'scoreai/stock_event_form.html'
    success_url = reverse_lazy('stock_event_list')

    def get_initial(self):
        initial = super().get_initial()
        company = self.this_company
        latest_fiscal_year = FiscalSummary_Year.objects.filter(company=company).order_by('-year').first()
        if latest_fiscal_year:
            initial['fiscal_summary_year'] = latest_fiscal_year
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        company = self.this_company
        form.fields['fiscal_summary_year'].queryset = FiscalSummary_Year.objects.filter(company=company)
        return form

    def form_valid(self, form):
        form.instance.fiscal_summary_year.company = self.this_company
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '株主情報'
        context['show_title_card'] = False
        return context


class StockEventUpdateView(SelectedCompanyMixin, UpdateView):
    model = StockEvent
    form_class = StockEventForm
    template_name = 'scoreai/stock_event_form.html'
    success_url = reverse_lazy('stock_event_list')

    def get_queryset(self):
        return StockEvent.objects.filter(fiscal_summary_year__company=self.this_company).order_by('-fiscal_summary_year__year', 'event_date')

    def get_object(self, queryset=None):
        obj = super(UpdateView, self).get_object(queryset)
        if obj.fiscal_summary_year.company != self.this_company:
            raise PermissionDenied("この株式発行データを更新する権限がありません。")
        return obj

    def form_valid(self, form):
        # fiscal_summary_yearの変更を防ぐ
        form.instance.fiscal_summary_year = self.object.fiscal_summary_year
        response = super().form_valid(form)
        messages.success(self.request, f'{self.object.fiscal_summary_year.year}年度の株式発行データを更新しました。')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '株主情報'
        context['show_title_card'] = False
        context['fiscal_summary_year'] = self.object.fiscal_summary_year
        return context


class StockEventListView(SelectedCompanyMixin, ListView):
    model = StockEvent
    template_name = 'scoreai/stock_event_list.html'
    context_object_name = 'stock_events'

    def get_queryset(self):
        queryset = StockEvent.objects.filter(fiscal_summary_year__company=self.this_company).order_by('-event_date')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': '株主情報',
            'show_title_card': False,  # タイトルカードを非表示（他のページと統一）
        })
        return context

class StockEventDetailView(SelectedCompanyMixin, DetailView):
    model = StockEvent
    template_name = 'scoreai/stock_event_detail.html'
    context_object_name = 'stock_event'

    def get_queryset(self):
        return StockEvent.objects.filter(fiscal_summary_year__company=self.this_company)

    def get_object(self, queryset=None):
        obj = super(DetailView, self).get_object(queryset)
        if obj.fiscal_summary_year.company != self.this_company:
            raise PermissionDenied("このStockEventにアクセスする権限がありません。")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '株主情報'
        context['show_title_card'] = False
        # これに紐づくStockEventLineのデータを取得し、contextに含める
        context['stock_event_line'] = self.object.details.all()
        return context

class StockEventDeleteView(SelectedCompanyMixin, DeleteView):
    model = StockEvent
    template_name = 'scoreai/stock_event_confirm_delete.html'
    success_url = reverse_lazy('stock_event_list')

    def get_queryset(self):
        company = self.this_company
        return StockEvent.objects.filter(fiscal_summary_year__company=company).order_by('-fiscal_summary_year__year', 'event_date')

    def get_object(self, queryset=None):
        obj = super(DeleteView, self).get_object(queryset)
        if obj.fiscal_summary_year.company != self.this_company:
            raise PermissionDenied("この株式発行データを削除する権限がありません。")
        return obj

    def form_valid(self, form):
        stock_event = self.get_object()
        year = stock_event.fiscal_summary_year.year
        response = super().form_valid(form)
        messages.success(self.request, f'{year}年度の株式発行データを削除しました。')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '株主情報'
        context['show_title_card'] = False
        return context


##########################################################################
###                 StockEventLine の View                              ###
##########################################################################
# StockEventから登録編集ができるようにする。

class StockEventLineCreateView(SelectedCompanyMixin, CreateView):
    model = StockEventLine
    form_class = StockEventLineForm
    template_name = 'scoreai/stock_event_line_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.stock_event = get_object_or_404(StockEvent, pk=kwargs['stock_event_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # 自社の株主だけが登録可能になるように制限
        form.fields['stakeholder'].queryset = Stakeholder_name.objects.filter(company=self.this_company)
        return form

    def form_valid(self, form):
        form.instance.stock_event = self.stock_event
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('stock_event_detail', kwargs={'pk': self.stock_event.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '株主情報'
        context['show_title_card'] = False
        context['stock_event'] = self.stock_event
        return context


class StockEventLineUpdateView(SelectedCompanyMixin, UpdateView):
    model = StockEventLine
    form_class = StockEventLineForm
    template_name = 'scoreai/stock_event_line_form.html'

    def get_success_url(self):
        return reverse_lazy('stock_event_detail', kwargs={'pk': self.object.stock_event.pk})

    def get_queryset(self):
        return StockEventLine.objects.filter(stock_event__fiscal_summary_year__company=self.this_company)

    def get_object(self, queryset=None):
        obj = super(UpdateView, self).get_object(queryset)
        if obj.stock_event.fiscal_summary_year.company != self.this_company:
            raise PermissionDenied("この株式発行明細データを更新する権限がありません。")
        return obj

    def form_valid(self, form):
        # fiscal_summary_yearの変更を防ぐ
        form.instance.stock_event = self.object.stock_event
        response = super().form_valid(form)
        messages.success(self.request, f'株式発行明細データを更新しました。')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stock_event'] = self.object.stock_event
        context['title'] = '株主情報'
        context['show_title_card'] = False
        return context

##########################################################################
###                 FinancialInstitution の View                       ###
##########################################################################

class ImportFinancialInstitutionView(LoginRequiredMixin, DetailView):
    template_name = 'scoreai/import_financial_institution.html'

    # CSRF保護を有効化（csrf_exemptを削除）
    # 認証済みユーザーのみがアクセス可能なため、CSRF保護は必要
    # @method_decorator(csrf_exempt)
    # def dispatch(self, *args, **kwargs):
    #     return super().dispatch(*args, **kwargs)

    def get(self, request):
        context = {'title': '金融機関インポート'}
        return render(request, self.template_name, context)

    @transaction.atomic
    def post(self, request):
        """金融機関CSVインポート処理（トランザクション管理付き）"""
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, 'ファイルがアップロードされていません。')
            return redirect('import_financial_institution')

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'CSV形式のファイルではありません。')
            return redirect('import_financial_institution')

        try:
            # BOMを無視してファイルを読み込む
            file = TextIOWrapper(csv_file.file, encoding='utf-8-sig')
            reader = csv.reader(file)
            
            # ヘッダー行を読み込む
            header = next(reader)
            
            # BOMが残っている場合は除去する
            header[0] = header[0].lstrip('\ufeff')
            
            # デバッグ用：ヘッダー行の内容をログに出力
            print(f"CSV Header: {header}")
            
            # 期待される列名のリスト
            expected_fields = ['name', 'short_name', 'JBAcode', 'bank_category']
            
            # CSVファイルの列名を確認
            if not all(field in header for field in expected_fields):
                missing_fields = set(expected_fields) - set(header)
                messages.error(request, f'Missing required fields in CSV: {", ".join(missing_fields)}')
                return redirect('import_financial_institution')

            for row in reader:
                try:
                    # 行の内容をディクショナリに変換
                    row_dict = dict(zip(header, row))
                    
                    FinancialInstitution.objects.update_or_create(
                        name=row_dict['name'],
                        defaults={
                            'short_name': row_dict['short_name'],
                            'JBAcode': row_dict['JBAcode'],
                            'bank_category': row_dict['bank_category']
                        }
                    )
                except ValidationError as ve:
                    messages.warning(request, f'Validation error for row {reader.line_num}: {str(ve)}')
                except Exception as e:
                    messages.warning(request, f'Error processing row {reader.line_num}: {str(e)}')

            messages.success(request, 'Financial institutions imported successfully.')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')

        return redirect('import_financial_institution')


@login_required
def download_financial_institutions_csv(request):
    response = HttpResponse(content_type='text/csv')
    response.charset = 'utf-8-sig'  # Excelでの文字化けを防ぐためにBOM付きUTF-8を使用
    response['Content-Disposition'] = 'attachment; filename="financial_institutions.csv"'

    writer = csv.writer(response)
    headers = ['name', 'short_name', 'JBAcode', 'bank_category']
    writer.writerow(headers)

    institutions = FinancialInstitution.objects.all()
    for institution in institutions:
        writer.writerow([
            institution.name,
            institution.short_name,
            institution.JBAcode,
            institution.bank_category
        ])

    return response


class ImportIndustryClassificationView(LoginRequiredMixin, FormView):
    template_name = 'scoreai/import_industry_classification.html'
    form_class = IndustryClassificationImportForm
    success_url = reverse_lazy('industry_classification_list')  # 適切なURLに変更してください

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'ローカルベンチマーク'
        context['show_title_card'] = False
        return context

    def form_valid(self, form):
        csv_file = form.cleaned_data['csv_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(self.request, 'アップロードされたファイルはCSV形式ではありません。')
            return self.form_invalid(form)

        try:
            # Shift-JISエンコーディングでファイルを読み込む
            file = TextIOWrapper(csv_file.file, encoding='shift-jis')
            reader = csv.DictReader(file)
            # 期待されるフィールド
            expected_fields = ['name', 'code', 'memo']
            if not all(field in reader.fieldnames for field in expected_fields):
                missing_fields = set(expected_fields) - set(reader.fieldnames)
                messages.error(self.request, f'CSVに必要なフィールドがありません: {", ".join(missing_fields)}')
                return self.form_invalid(form)

            for row in reader:
                IndustryClassification.objects.update_or_create(
                    code=row['code'],
                    defaults={
                        'name': row['name'],
                        'memo': row.get('memo', ''),
                    },
                )
            messages.success(self.request, '業界分類のインポートが完了しました。')
        except Exception as e:
            messages.error(self.request, f'CSVファイルの処理中にエラーが発生しました: {str(e)}')
            return self.form_invalid(form)

        return super().form_valid(form)


class IndustryClassificationListView(LoginRequiredMixin, ListView):
    model = IndustryClassification
    template_name = 'scoreai/industry_classification_list.html'
    context_object_name = 'industry_classifications'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'ローカルベンチマーク'
        context['show_title_card'] = False
        return context


class ImportIndustrySubClassificationView(FormView):
    form_class = IndustrySubClassificationImportForm
    template_name = 'scoreai/industry_subclassification_import.html'
    success_url = reverse_lazy('industry_subclassification_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'ローカルベンチマーク'
        context['show_title_card'] = False
        return context

    def form_valid(self, form):
        csv_file = form.cleaned_data['csv_file']
        decoded_file = csv_file.read().decode('shift-jis').splitlines()
        csv_reader = csv.reader(decoded_file)
        for row in csv_reader:
            # Assuming CSV columns are: industry_classification_code, name, code, memo
            industry_classification_code = row[0]
            name = row[1]
            code = row[2]
            memo = row[3] if len(row) > 3 else ''
            try:
                industry_classification = IndustryClassification.objects.get(code=industry_classification_code)
                IndustrySubClassification.objects.create(
                    industry_classification=industry_classification,
                    name=name,
                    code=code,
                    memo=memo
                )
            except IndustryClassification.DoesNotExist:
                # Handle if the parent IndustryClassification does not exist
                pass  # You can add error handling or logging here
        return super().form_valid(form)

class IndustrySubClassificationListView(ListView):
    model = IndustrySubClassification
    template_name = 'scoreai/industry_subclassification_list.html'
    context_object_name = 'industry_subclassifications'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'ローカルベンチマーク'
        context['show_title_card'] = False
        return context


class ImportIndustryBenchmarkView(LoginRequiredMixin, FormView):
    template_name = 'scoreai/import_industry_benchmark.html'
    form_class = IndustryBenchmarkImportForm
    success_url = reverse_lazy('industry_benchmark_list')  # 適切なリスト表示のURLに変更してください

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'ローカルベンチマーク'
        context['show_title_card'] = False
        return context

    def form_valid(self, form):
        csv_file = form.cleaned_data['csv_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(self.request, 'アップロードされたファイルはCSV形式ではありません。')
            return self.form_invalid(form)

        try:
            # CSVファイルを適切なエンコーディングで読み込む
            file = TextIOWrapper(csv_file.file, encoding='shift-jis')
            reader = csv.DictReader(file)

            # 期待されるフィールド
            expected_fields = [
                'year', 'industry_classification_code', 'industry_subclassification_code',
                'company_size', 'indicator', 'median', 'standard_deviation',
                'range_iv', 'range_iii', 'range_ii', 'range_i', 'memo'
            ]
            if not all(field in reader.fieldnames for field in expected_fields):
                missing_fields = set(expected_fields) - set(reader.fieldnames)
                messages.error(self.request, f'CSVに必要なフィールドがありません: {", ".join(missing_fields)}')
                return self.form_invalid(form)

            for row in reader:
                try:
                    # 関連するIndustryClassificationとIndustrySubClassificationを取得
                    industry_classification = IndustryClassification.objects.get(code=row['industry_classification_code'])
                    industry_subclassification = IndustrySubClassification.objects.get(code=row['industry_subclassification_code'])

                    # IndustryIndicatorのインスタンスを取得
                    indicator_id = row['indicator']
                    try:
                        industry_indicator = IndustryIndicator.objects.get(id=indicator_id)
                    except IndustryIndicator.DoesNotExist:
                        messages.warning(self.request, f"IndustryIndicator が存在しません。ID: {indicator_id} 行番号 {reader.line_num}")
                        continue

                    company_size = row['company_size']
                    if company_size not in dict(IndustryBenchmark.COMPANY_SIZE_CHOICES):
                        messages.warning(self.request, f"有効な会社規模を指定してください。行番号 {reader.line_num}")
                        continue

                    # 数値データをDecimal型に変換
                    median = Decimal(row['median']) if row['median'] else None
                    standard_deviation = Decimal(row['standard_deviation']) if row['standard_deviation'] else None
                    range_iv = Decimal(row['range_iv']) if row['range_iv'] else None
                    range_iii = Decimal(row['range_iii']) if row['range_iii'] else None
                    range_ii = Decimal(row['range_ii']) if row['range_ii'] else None
                    range_i = Decimal(row['range_i']) if row['range_i'] else None

                    # レコードの作成または更新
                    IndustryBenchmark.objects.update_or_create(
                        year=row['year'],
                        industry_classification=industry_classification,
                        industry_subclassification=industry_subclassification,
                        company_size=company_size,
                        indicator=industry_indicator,
                        defaults={
                            'median': median,
                            'standard_deviation': standard_deviation,
                            'range_iv': range_iv,
                            'range_iii': range_iii,
                            'range_ii': range_ii,
                            'range_i': range_i,
                            'memo': row.get('memo', ''),
                        },
                    )
                except IndustryClassification.DoesNotExist:
                    messages.warning(self.request, f"IndustryClassification が存在しません。コード: {row['industry_classification_code']} 行番号 {reader.line_num}")
                except IndustrySubClassification.DoesNotExist:
                    messages.warning(self.request, f"IndustrySubClassification が存在しません。コード: {row['industry_subclassification_code']} 行番号 {reader.line_num}")
                except Exception as e:
                    messages.warning(self.request, f'行 {reader.line_num} の処理中にエラーが発生しました: {str(e)}')

            messages.success(self.request, '業界別経営指標のインポートが完了しました。')
        except Exception as e:
            messages.error(self.request, f'CSVファイルの処理中にエラーが発生しました: {str(e)}')
            return self.form_invalid(form)

        return super().form_valid(form)


class IndustryBenchmarkListView(LoginRequiredMixin, ListView):
    model = IndustryBenchmark
    template_name = 'scoreai/industry_benchmark_list.html'
    context_object_name = 'industry_benchmarks'
    paginate_by = 10  # 1ページに表示するオブジェクト数

    def get_queryset(self):
        queryset = super().get_queryset()

        # GETパラメータの取得
        year = self.request.GET.get('year')
        industry_classification_id = self.request.GET.get('industry_classification')
        industry_subclassification_id = self.request.GET.get('industry_subclassification')
        company_size = self.request.GET.get('company_size')
        indicator_id = self.request.GET.get('indicator')

        # フィルタリング
        if year:
            queryset = queryset.filter(year=year)
        if industry_classification_id:
            queryset = queryset.filter(industry_classification_id=industry_classification_id)
        if industry_subclassification_id:
            queryset = queryset.filter(industry_subclassification_id=industry_subclassification_id)
        if company_size:
            queryset = queryset.filter(company_size=company_size)
        if indicator_id:
            queryset = queryset.filter(indicator_id=indicator_id)

        return queryset.order_by('year', 'industry_classification', 'industry_subclassification')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # フォームの選択肢に必要な情報を取得
        context['industry_classifications'] = IndustryClassification.objects.all()
        context['industry_subclassifications'] = IndustrySubClassification.objects.all()
        context['indicators'] = IndustryIndicator.objects.all()
        context['company_size_choices'] = dict(IndustryBenchmark.COMPANY_SIZE_CHOICES).items()
        context['title'] = 'ローカルベンチマーク'
        context['show_title_card'] = False
        return context


##########################################################################
###                 コンサルタント(Firm）専用のView                          ###
##########################################################################

class ClientsList(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = FirmCompany
    template_name = 'scoreai/firm_clientslist.html'
    context_object_name = 'clients'

    # is_financial_consultant=Trueのユーザーのみがアクセス
    def test_func(self):
        return self.request.user.is_financial_consultant

    def get_queryset(self):
        user_firm = UserFirm.objects.filter(user=self.request.user, is_selected=True).first()
        if user_firm:
            return FirmCompany.objects.filter(firm=user_firm.firm, active=True)
        return FirmCompany.objects.none()

    def get_context_data(self, **kwargs):
        from .utils.plan_limits import check_company_limit
        
        context = super().get_context_data(**kwargs)
        context['title'] = 'クライアント一覧'
        context['show_title_card'] = False  # タイトルカードを非表示（他のページと統一）
        
        # Firmを取得してプラン制限情報を追加
        user_firm = UserFirm.objects.filter(user=self.request.user, is_selected=True).first()
        context['user_firm'] = user_firm  # テンプレートで使用するため追加
        
        if user_firm:
            # 選択中のFirmに属するCompanyのIDを取得
            firm_company_ids = FirmCompany.objects.filter(
                firm=user_firm.firm,
                active=True
            ).values_list('company_id', flat=True)
            
            # 自分がアサインされているクライアント（as_consultant=True）を取得
            # かつ、そのCompanyが選択中のFirmに属しているもの
            clients_assigned = UserCompany.objects.filter(
                user=self.request.user,
                as_consultant=True,
                active=True,
                company_id__in=firm_company_ids
            ).select_related('company').prefetch_related(
                'company__firm_companies'
            ).order_by('company__name').distinct()
            
            # FirmCompanyの情報を取得してコンテキストに追加
            # テンプレートでstart_dateを取得できるようにする
            firm_companies_dict = {
                fc.company_id: fc
                for fc in FirmCompany.objects.filter(
                    firm=user_firm.firm,
                    company_id__in=firm_company_ids,
                    active=True
                )
            }
            context['firm_companies_dict'] = firm_companies_dict
            context['clients_assigned'] = clients_assigned
            
            is_allowed, current_count, max_allowed = check_company_limit(user_firm.firm)
            context['current_company_count'] = current_count
            context['max_companies'] = max_allowed
            context['is_unlimited'] = max_allowed == 0
            context['can_add_company'] = is_allowed
            
            # Firmのマネージャーかどうかを確認
            context['is_firm_manager'] = self.request.user.is_manager
            
            # プランの利用枠情報を取得
            try:
                subscription = user_firm.firm.subscription
                plan = subscription.plan
                
                # プランの上限
                plan_api_limit = plan.api_limit if plan.api_limit > 0 else None
                plan_ocr_limit = plan.max_ocr_per_month if plan.max_ocr_per_month > 0 else None
                
                # 現在割り当て済みの利用枠
                active_firm_companies = FirmCompany.objects.filter(
                    firm=user_firm.firm,
                    active=True
                )
                assigned_api_limit = sum(fc.api_limit for fc in active_firm_companies)
                assigned_ocr_limit = sum(fc.ocr_limit for fc in active_firm_companies)
                
                # 未割り当ての利用枠
                unassigned_api_limit = None
                unassigned_ocr_limit = None
                if plan_api_limit is not None:
                    unassigned_api_limit = max(0, plan_api_limit - assigned_api_limit)
                if plan_ocr_limit is not None:
                    unassigned_ocr_limit = max(0, plan_ocr_limit - assigned_ocr_limit)
                
                context['plan_api_limit'] = plan_api_limit
                context['plan_ocr_limit'] = plan_ocr_limit
                context['assigned_api_limit'] = assigned_api_limit
                context['assigned_ocr_limit'] = assigned_ocr_limit
                context['unassigned_api_limit'] = unassigned_api_limit
                context['unassigned_ocr_limit'] = unassigned_ocr_limit
                context['active_company_count'] = active_firm_companies.count()
            except Exception as e:
                context['is_firm_manager'] = False
                context['plan_api_limit'] = None
                context['plan_ocr_limit'] = None
                context['unassigned_api_limit'] = None
                context['unassigned_ocr_limit'] = None
                context['active_company_count'] = 0
        else:
            context['clients_assigned'] = UserCompany.objects.none()
            context['current_company_count'] = 0
            context['max_companies'] = 0
            context['is_unlimited'] = True
            context['can_add_company'] = True
            context['is_firm_manager'] = False
            context['unassigned_api_limit'] = None
            context['unassigned_ocr_limit'] = None
            context['active_company_count'] = 0
        
        return context


@login_required
@require_http_methods(["POST"])
def distribute_limits_evenly(request, firm_id, limit_type):
    """プランの利用枠を各クライアントに均等に割り振る（APIまたはOCR）"""
    from django.http import JsonResponse
    from django.db import transaction
    from django.contrib import messages
    
    # Firmを取得
    user_firm = UserFirm.objects.filter(
        user=request.user,
        firm_id=firm_id,
        active=True
    ).first()
    
    if not user_firm:
        return JsonResponse({'error': 'Firmが見つかりません。'}, status=404)
    
    # マネージャー権限を確認
    if not request.user.is_manager:
        return JsonResponse({'error': 'マネージャー権限がありません。'}, status=403)
    
    # limit_typeの検証
    if limit_type not in ['api', 'ocr']:
        return JsonResponse({'error': '無効なlimit_typeです。apiまたはocrを指定してください。'}, status=400)
    
    try:
        subscription = user_firm.firm.subscription
        plan = subscription.plan
        
        # プランの上限を取得
        if limit_type == 'api':
            plan_limit = plan.api_limit if plan.api_limit > 0 else None
            limit_name = 'API利用枠'
        else:  # ocr
            plan_limit = plan.max_ocr_per_month if plan.max_ocr_per_month > 0 else None
            limit_name = 'OCR利用枠'
        
        if plan_limit is None:
            return JsonResponse({'error': f'{limit_name}の上限が設定されていません（無制限の可能性があります）。'}, status=400)
        
        # アクティブなクライアントを取得
        active_firm_companies = FirmCompany.objects.filter(
            firm=user_firm.firm,
            active=True
        )
        active_count = active_firm_companies.count()
        
        if active_count == 0:
            return JsonResponse({'error': 'アクティブなクライアントがありません。'}, status=400)
        
        with transaction.atomic():
            # 均等に割り振る
            limit_per_company = plan_limit // active_count
            remainder = plan_limit % active_count
            
            # 各クライアントに割り当て
            for idx, firm_company in enumerate(active_firm_companies):
                if limit_type == 'api':
                    # 余りは最初のクライアントに追加
                    firm_company.api_limit = limit_per_company + (remainder if idx < remainder else 0)
                else:  # ocr
                    # 余りは最初のクライアントに追加
                    firm_company.ocr_limit = limit_per_company + (remainder if idx < remainder else 0)
                
                firm_company.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{active_count}社のクライアントに{limit_name}を均等に割り当てました。',
            'limit_per_company': limit_per_company,
            'limit_type': limit_type,
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error distributing {limit_type} limits evenly: {e}")
        return JsonResponse({'error': f'エラーが発生しました: {str(e)}'}, status=500)


@login_required
def add_client(request, client_id):
    from django.utils import timezone
    from .utils.plan_limits import check_company_limit
    from .models import UserFirm, FirmCompany
    
    client = Company.objects.get(id=client_id)
    
    # Firmを取得
    user_firm = UserFirm.objects.filter(
        user=request.user,
        is_selected=True
    ).first()
    
    if not user_firm:
        messages.error(request, 'Firmが選択されていません。')
        return redirect('firm_clientslist')
    
    # プラン制限をチェック
    is_allowed, current_count, max_allowed = check_company_limit(user_firm.firm)
    
    if not is_allowed:
        messages.error(
            request,
            f'プランの制限により、これ以上Companyを追加できません。'
            f'（現在: {current_count}社 / 上限: {max_allowed}社）'
            f'プランをアップグレードしてください。'
        )
        return redirect('firm_clientslist')
    
    # 既に追加されているか確認
    if UserCompany.objects.filter(user=request.user, company=client).exists():
        messages.warning(request, f'クライアント "{client.name}" は既に追加されています。')
    else:
        UserCompany.objects.create(user=request.user, company=client, as_consultant=True)
        
        # FirmCompanyも作成（存在しない場合）
        FirmCompany.objects.get_or_create(
            firm=user_firm.firm,
            company=client,
            defaults={
                'active': True,
                'start_date': timezone.now().date()
            }
        )
        
        messages.success(request, f'クライアント "{client.name}" をアサインしました。')
    
    return redirect('firm_clientslist')

@login_required
def remove_client(request, client_id):
    client = Company.objects.get(id=client_id)
    UserCompany.objects.filter(user=request.user, company=client).delete()
    return redirect('firm_clientslist')


##########################################################################
###                 テキスト情報中心のシンプルなView                         ###
##########################################################################


class AboutView(generic.TemplateView):
    template_name = 'scoreai/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'About'
        context['show_title_card'] = False
        return context

class NewsListView(generic.TemplateView):
    template_name = 'scoreai/news_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'お知らせ'
        context['show_title_card'] = False
        return context

class CompanyProfileView(generic.TemplateView):
    template_name = 'scoreai/score_company_profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '会社概要'
        context['show_title_card'] = False
        return context

class HelpView(generic.ListView):
    """ヘルプ一覧ページ"""
    model = Help
    template_name = 'scoreai/help.html'
    context_object_name = 'help_items'
    paginate_by = 12

    def get_queryset(self):
        queryset = Help.objects.all()
        category = self.request.GET.get('category', '')
        if category:
            queryset = queryset.filter(category=category)
        return queryset.order_by('category', 'id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'ヘルプ'
        context['show_title_card'] = False
        context['selected_category'] = self.request.GET.get('category', '')
        # カテゴリの選択肢を定義
        context['categories'] = [
            {'value': 'ai_usage', 'label': 'AIの活用', 'icon': 'ti ti-brain'},
            {'value': 'data_entry', 'label': 'データ登録', 'icon': 'ti ti-database'},
            {'value': 'login', 'label': 'ログイン', 'icon': 'ti ti-login'},
            {'value': 'others', 'label': 'その他', 'icon': 'ti ti-dots'},
        ]
        return context


class HelpDetailView(generic.DetailView):
    """ヘルプ詳細ページ"""
    model = Help
    template_name = 'scoreai/help_detail.html'
    context_object_name = 'help_item'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.object.title
        context['show_title_card'] = False
        return context

class ManualListView(SelectedCompanyMixin, generic.ListView):
    """マニュアル一覧ページ"""
    model = Manual
    template_name = 'scoreai/manual_list.html'
    context_object_name = 'manuals'
    paginate_by = 12
    
    def get_queryset(self):
        # デフォルトのユーザータイプを判定
        from ..models import UserCompany
        user = self.request.user
        default_user_type = None
        if user.is_company_user:
            # 現在の会社のUserCompanyからis_managerを取得
            user_company = UserCompany.objects.filter(
                user=user,
                company=self.this_company,
                active=True
            ).first()
            if user_company and user_company.is_manager:
                default_user_type = 'company_admin'
            else:
                default_user_type = 'company_user'
        elif hasattr(user, 'userfirm') and user.userfirm.exists():
            # Firm関連は後で対応（UserFirmにis_managerフィールドを追加する必要がある）
            if user.is_manager:
                default_user_type = 'firm_admin'
            else:
                default_user_type = 'firm_user'
        else:
            default_user_type = 'company_user'
        
        # クエリパラメータからフィルタを取得
        user_type_filter = self.request.GET.get('user_type', default_user_type)
        category_filter = self.request.GET.get('category', '')
        search_query = self.request.GET.get('search', '')
        
        # ベースクエリセット
        queryset = Manual.objects.filter(is_active=True)
        
        # ユーザータイプでフィルタ
        if user_type_filter:
            queryset = queryset.filter(user_type=user_type_filter)
        
        # カテゴリでフィルタ
        if category_filter:
            queryset = queryset.filter(category=category_filter)
        
        # 検索クエリでフィルタ（タイトルと内容を検索）
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(content__icontains=search_query)
            )
        
        queryset = queryset.order_by('category', 'order', 'id')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'マニュアル'
        context['show_title_card'] = False
        
        # デフォルトのユーザータイプを判定
        from ..models import UserCompany
        user = self.request.user
        default_user_type = None
        if user.is_company_user:
            # 現在の会社のUserCompanyからis_managerを取得
            user_company = UserCompany.objects.filter(
                user=user,
                company=self.this_company,
                active=True
            ).first()
            if user_company and user_company.is_manager:
                default_user_type = 'company_admin'
            else:
                default_user_type = 'company_user'
        elif hasattr(user, 'userfirm') and user.userfirm.exists():
            # Firm関連は後で対応（UserFirmにis_managerフィールドを追加する必要がある）
            if user.is_manager:
                default_user_type = 'firm_admin'
            else:
                default_user_type = 'firm_user'
        else:
            default_user_type = 'company_user'
        
        # 現在のフィルタ値を取得（初回アクセス時はデフォルト値を使用）
        current_user_type = self.request.GET.get('user_type', '')
        if not current_user_type:
            current_user_type = default_user_type
        current_category = self.request.GET.get('category', '')
        current_search = self.request.GET.get('search', '')
        
        # ユーザータイプの選択肢
        context['user_type_choices'] = Manual.USER_TYPE_CHOICES
        context['current_user_type'] = current_user_type
        
        # カテゴリの選択肢
        context['category_choices'] = Manual.CATEGORY_CHOICES
        context['current_category'] = current_category
        
        # 検索クエリ
        context['current_search'] = current_search
        
        # ユーザータイプを表示用に取得
        user = self.request.user
        if user.is_company_user:
            # 現在の会社のUserCompanyからis_managerを取得
            user_company = UserCompany.objects.filter(
                user=user,
                company=self.this_company,
                active=True
            ).first()
            if user_company and user_company.is_manager:
                user_type_display = '会社ユーザー（管理者）'
            else:
                user_type_display = '会社ユーザー（一般）'
        elif hasattr(user, 'userfirm') and user.userfirm.exists():
            # Firm関連は後で対応
            if user.is_manager:
                user_type_display = 'Firmユーザー（管理者）'
            else:
                user_type_display = 'Firmユーザー（一般）'
        else:
            user_type_display = '会社ユーザー（一般）'
        
        context['user_type_display'] = user_type_display
        
        return context


class ManualDetailView(SelectedCompanyMixin, generic.DetailView):
    """マニュアル詳細ページ"""
    model = Manual
    template_name = 'scoreai/manual_detail.html'
    context_object_name = 'manual'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.object.title
        context['show_title_card'] = False
        
        # 前後のマニュアルを取得（同じカテゴリ、同じユーザータイプ）
        manual = self.object
        prev_manual = Manual.objects.filter(
            user_type=manual.user_type,
            category=manual.category,
            is_active=True,
            order__lt=manual.order
        ).order_by('-order', '-id').first()
        
        if not prev_manual:
            prev_manual = Manual.objects.filter(
                user_type=manual.user_type,
                is_active=True,
                category__lt=manual.category
            ).order_by('-category', '-order', '-id').first()
        
        next_manual = Manual.objects.filter(
            user_type=manual.user_type,
            category=manual.category,
            is_active=True,
            order__gt=manual.order
        ).order_by('order', 'id').first()
        
        if not next_manual:
            next_manual = Manual.objects.filter(
                user_type=manual.user_type,
                is_active=True,
                category__gt=manual.category
            ).order_by('category', 'order', 'id').first()
        
        context['prev_manual'] = prev_manual
        context['next_manual'] = next_manual
        
        return context


class FAQView(generic.TemplateView):
    template_name = 'scoreai/faq.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'よくある質問'
        context['show_title_card'] = False
        return context

class TermsOfServiceView(generic.TemplateView):
    template_name = 'scoreai/terms_of_service.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '利用規約'
        context['show_title_card'] = False
        return context

class PrivacyPolicyView(generic.TemplateView):
    template_name = 'scoreai/privacy_policy.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'プライバシーポリシー'
        context['show_title_card'] = False
        return context

class LegalNoticeView(generic.TemplateView):
    template_name = 'scoreai/legal_notice.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '特定商取引法に基づく表示'
        context['show_title_card'] = False
        return context

class SecurityPolicyView(generic.TemplateView):
    template_name = 'scoreai/security_policy.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'セキュリティポリシー'
        context['show_title_card'] = False
        return context


class SampleView(generic.TemplateView):
    template_name = 'scoreai/ui-forms.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Sample Page'
        context['show_title_card'] = False
        return context



##########################################################################
##########################################################################
###                           ここから                                   ###
###                           汎用関数                                  ###
##########################################################################
##########################################################################

def calculate_total_monthly_summaries(monthly_summaries, year_index=0, period_count=13):
    # 引数が空でないか確認
    if not monthly_summaries:
        return {
            'year': None,
            'sum_sales': 0,
            'sum_gross_profit': 0,
            'sum_operating_profit': 0,
            'average_ordinary_profit': 0,
            'average_gross_profit_rate': 0,
        }
    # 引数から年を取得
    try:
        year = monthly_summaries[year_index]['year']
    except (IndexError, KeyError):
        # yearが取得できない場合はNoneを返して終了
        return {
            'year': None,
            'sum_sales': 0,
            'sum_gross_profit': 0,
            'sum_operating_profit': 0,
            'average_ordinary_profit': 0,
            'average_gross_profit_rate': 0,
        }
            
    # 各合計値を初期化
    sum_sales = 0.0
    sum_gross_profit = 0.0
    sum_operating_profit = 0.0
    sum_ordinary_profit = 0.0

    # 各データをループして合計を計算
    for month in monthly_summaries[year_index]['data'][:period_count]:
        sum_sales += month['sales']
        sum_gross_profit += month['gross_profit']
        sum_operating_profit += month['operating_profit']
        sum_ordinary_profit += month['ordinary_profit']

    # 各利益率を計算
    average_gross_profit_rate = (sum_gross_profit / sum_sales * 100) if sum_sales > 0 else 0
    average_operating_profit_rate = (sum_operating_profit / sum_sales * 100) if sum_sales > 0 else 0
    average_ordinary_profit_rate = (sum_ordinary_profit / sum_sales * 100) if sum_sales > 0 else 0

    # 結果を辞書形式で返す
    return {
        'year': year,
        'sum_sales': sum_sales,
        'sum_gross_profit': sum_gross_profit,
        'sum_operating_profit': sum_operating_profit,
        'sum_ordinary_profit': sum_ordinary_profit,
        'average_gross_profit_rate': average_gross_profit_rate,
        'average_operating_profit_rate': average_operating_profit_rate,
        'average_ordinary_profit_rate': average_ordinary_profit_rate,
    }

##########################################################################
###                 指定した年度以下のベンチマーク指標を返す関数               ###
##########################################################################

def get_benchmark_index(classification, subclassification, company_size, year):
    while year >= 2000:
        benchmark_index = IndustryBenchmark.objects.filter(
            industry_classification=classification,
            industry_subclassification=subclassification,
            company_size=company_size,
            year=year
        )
        if benchmark_index:
            return benchmark_index
        year -= 1
    else:
        # If no data is found, attempt to get data for year=2022
        benchmark_index = IndustryBenchmark.objects.filter(
            industry_classification=classification,
            industry_subclassification=subclassification,
            company_size=company_size,
            year=2022
        )
        return benchmark_index
    
    if not benchmark_index:
        return IndustoryBenchmark.object.none()


##########################################################################
###                 計算値を返す単純で便利な関数                            ###
##########################################################################

# 指定した月（今から何ヶ月後かを指定）の月末日を返す
def get_last_day_of_next_month(months):
    today = datetime.today()
    # Calculate the target month and year
    target_month = today.month + months
    target_year = today.year + (target_month - 1) // 12
    target_month = (target_month - 1) % 12 + 1

    # Get the last day of the target month
    last_day = calendar.monthrange(target_year, target_month)[1]
    return datetime(target_year, target_month, last_day)


##########################################################################
###                    検証中 OPEN AI 財務アドバイス機能                    ###
##########################################################################


OPENAI_API_KEY = settings.OPENAI_API_KEY

# 既存のchat_viewはviews.helper_viewsからインポート済みのため、ここでは定義しない



##########################################################################
###                    ログインを前提として情報を取得する関数                   ###
##########################################################################

# 選択済みの会社を選択する関数
@login_required
def get_selected_company(self):
    user = self.request.user
    selected_company = UserCompany.objects.filter(user=user, is_selected=True).first()
    return selected_company


@login_required
def select_company(request, this_company):
    user = request.user
    
    # Get the previously selected company
    previous_company = UserCompany.objects.filter(user=user, is_selected=True).first()
    
    # Set all user companies to is_selected=False
    UserCompany.objects.filter(user=user).update(is_selected=False)
    
    # Set the selected company to is_selected=True
    new_company = UserCompany.objects.filter(user=user, company_id=this_company).first()
    if new_company:
        new_company.is_selected = True
        new_company.save()
        
        # Create success message
        if previous_company:
            messages.warning(request, f'対象の会社を{previous_company.company.name}から{new_company.company.name}に変更しました。')
        else:
            messages.warning(request, f'対象の会社を{new_company.company.name}に設定しました。')
    else:
        messages.error(request, '指定された会社が見つかりません。')
    
    return redirect('index')  # Redirect to the user profile page


##########################################################################
###                    FiscasSummary_Year                             ###
##########################################################################

from django.db.models import Max
from .models import FiscalSummary_Year

def get_YearlyFiscalSummary(this_company, years_ago=0):
    # 最新の年度を取得
    latest_year = FiscalSummary_Year.objects.filter(company=this_company).aggregate(Max('year'))['year__max']
    
    if latest_year is None:
        return None  # データが存在しない場合

    # 指定された年数分前の年度を計算
    target_year = latest_year - years_ago

    # 対象年度のFiscalSummary_Yearオブジェクトを取得
    fiscal_summary_year = FiscalSummary_Year.objects.filter(
        company=this_company,
        year=target_year
    ).first()

    return fiscal_summary_year 


def get_yearly_summaries(this_company, num_years):
    # 直近num_years分のデータを取得
    yearly_summaries = []
    for year in range(num_years):
        data = get_YearlyFiscalSummary(this_company, years_ago=year)
        if data:
            yearly_summaries.append({
                'year': data.year,
                'sales': data.sales,
                'gross_profit': data.gross_profit,
                'operating_profit': data.operating_profit,
                'ordinary_profit': data.ordinary_profit
            })
    return yearly_summaries


# 最新から数えて指定した年度数の月次データを取得する
def get_monthly_summaries(this_company, num_years=5):
    # Ensure num_years is at least 1
    num_years = max(1, int(num_years))

    # 年度取得
    latest_years = FiscalSummary_Year.objects.filter(
        company=this_company).values_list('year', flat=True).distinct().order_by('-year')[:num_years]

    # 取得した年度をリストに変換し、新しい順に並べる
    latest_years = sorted(latest_years, reverse=True)

    monthly_summaries = []
    for year in latest_years:
        monthly_data = FiscalSummary_Month.objects.filter(
            fiscal_summary_year__company=this_company,
            fiscal_summary_year__year=year).order_by('period')

        # 月データを辞書に変換
        monthly_data_dict = {month.period: {
            'id': month.id,
            'sales': float(month.sales),
            'gross_profit': float(month.gross_profit),
            'operating_profit': float(month.operating_profit),
            'ordinary_profit': float(month.ordinary_profit),
            'gross_profit_rate': float(month.gross_profit_rate),
            'operating_profit_rate': float(month.operating_profit_rate),
            'ordinary_profit_rate': float(month.ordinary_profit_rate),
        } for month in monthly_data}


        # 12ヶ月分のデータを作成
        full_month_data = []
        actual_months_count = 0  # 実際のデータがある月のカウント
        for period in range(1, 13):
            if period in monthly_data_dict:
                full_month_data.append({**monthly_data_dict[period], 'period': period})
                actual_months_count += 1
            else:
                full_month_data.append({
                    'period': period,
                    'id': f'temp_{random.randint(10000, 99999)}',
                    'sales': 0,
                    'gross_profit': 0,
                    'operating_profit': 0,
                    'ordinary_profit': 0,
                    'gross_profit_rate': 0,
                    'operating_profit_rate': 0,
                    'ordinary_profit_rate': 0,
                })

        monthly_summaries.append({
            'year': year,
            'data': full_month_data,
            'actual_months_count': actual_months_count
        })

    return monthly_summaries


# 選択済みの会社のDebtデータを取得
# 後方互換性のため残されていますが、内部ではDebtServiceを使用します
def get_debt_list(this_company):
    from .services.debt_service import DebtService
    return DebtService.get_debt_list_with_totals(this_company)


##########################################################################
###        取得済みの自社情報をさらに扱いやすいようにまとめる関数                   ###
##########################################################################

# 選択済みの会社のDebtデータを金融機関単位で集計したリスト
def get_debt_list_byAny(summary_field_label, debt_list):
    summary_field = summary_field_label.strip("'")
    debt_list_byAny = {}

    for debt in debt_list:
        if debt[summary_field_label] not in debt_list_byAny:
            debt_list_byAny[debt[summary_field_label]] = {
                'principal': 0,
                'monthly_repayment': 0,
                'balances_monthly': [0] * 12,  # Initialize with 12 zeros
                'interest_amount_monthly': [0] * 12,  # Initialize with 12 zeros
                'balance_fy1': 0,
            }

        debt_list_byAny[debt[summary_field_label]]['principal'] += debt['principal']
        debt_list_byAny[debt[summary_field_label]]['monthly_repayment'] += debt['monthly_repayment']
        debt_list_byAny[debt[summary_field_label]]['balance_fy1'] += debt['balance_fy1']

        # Sum up the monthly balances and interest amounts
        for i in range(12):
            debt_list_byAny[debt[summary_field_label]]['balances_monthly'][i] += debt['balances_monthly'][i]
            debt_list_byAny[debt[summary_field_label]]['interest_amount_monthly'][i] += debt['interest_amount_monthly'][i]
    # Convert the dictionary to a list of dictionaries
    debt_list_byAny = [{ summary_field_label: summary_field, **values} for summary_field, values in debt_list_byAny.items()]

    return debt_list_byAny

def get_debt_list_byBankAndSecuredType(debt_list):
    debt_list_byBankAndSecuredType = {}

    for debt in debt_list:
        key = (debt['financial_institution'], debt['secured_type'])
        if key not in debt_list_byBankAndSecuredType:
            debt_list_byBankAndSecuredType[key] = {
                'principal': 0,
                'monthly_repayment': 0,
                'balances_monthly': [0] * 12,  # Initialize with 12 zeros
                'interest_amount_monthly': [0] * 12,  # Initialize with 12 zeros
                'balance_fy1': 0,
            }

        debt_list_byBankAndSecuredType[key]['principal'] += debt['principal']
        debt_list_byBankAndSecuredType[key]['monthly_repayment'] += debt['monthly_repayment']
        debt_list_byBankAndSecuredType[key]['balance_fy1'] += debt['balance_fy1']

        # Sum up the monthly balances and interest amounts
        for i in range(12):
            debt_list_byBankAndSecuredType[key]['balances_monthly'][i] += debt['balances_monthly'][i]
            debt_list_byBankAndSecuredType[key]['interest_amount_monthly'][i] += debt['interest_amount_monthly'][i]

    # Convert the dictionary to a list of dictionaries
    debt_list_byBankAndSecuredType = [
        {
            'financial_institution': key[0],
            'secured_type': key[1],
            **values
        } for key, values in debt_list_byBankAndSecuredType.items()
    ]

    return debt_list_byBankAndSecuredType



##########################################################################
###                    管理者向け便利関数                                 ###
###                自分の会社以外のデータも扱えるため注意が必要                 ###
##########################################################################
