from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect

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
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils.decorators import method_decorator

from django.urls import reverse_lazy

from django.db.models import Max, Sum, Q, ProtectedError
from django.template.loader import render_to_string
from django.views import generic
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from django.views.decorators.csrf import csrf_exempt
from itertools import groupby
from operator import itemgetter
from io import TextIOWrapper

from .mixins import SelectedCompanyMixin
from .models import *
from .forms import *
from .tokens import *
import random
import csv, io
import calendar
import json
import requests
from django.core.serializers import serialize
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import FieldDoesNotExist

# デバッグ用
import logging
logger = logging.getLogger(__name__)


class IndexView(LoginRequiredMixin, SelectedCompanyMixin, generic.TemplateView):
    template_name = 'scoreai/index.html'

    def get(self, request, *args, **kwargs):
        try:
            context = self.get_context_data()
            context['form'] = ChatForm()
            return render(request, self.template_name, context)
        except Exception as e:
            # データを取得できない場合は help.html に遷移
            return render(request, 'scoreai/help.html')

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        form = ChatForm(request.POST)
        if form.is_valid():
            user_message = form.cleaned_data['message']
            selected_company = self.get_selected_company()
            debts = Debt.objects.filter(company=self.this_company)

            # 債務情報を文字列にフォーマット
            debt_info = "\n".join([f"債務{i+1}: {debt.principal}円 (金利: {debt.interest_rate}%)" for i, debt in enumerate(debts)])

            # プロンプトを作成
            prompt = f"""以下の債務情報に基づいて、最適な返済計画についてアドバイスしてください：
            {debt_info}
            ユーザーの質問: {user_message}
            総債務額、平均金利、そして最も効果的な返済方法を提案してください。"""

            # Prepare the API request to ChatGPT
            headers = {
                'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
                'Content-Type': 'application/json',
            }
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "あなたは財務アドバイザーです。与えられた債務情報に基づいて、最適な返済計画を提案してください。"},
                    {"role": "user", "content": prompt}
                ],
            }

            # requestsをrequestに変更するか
            api_response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)

            if api_response.status_code == 200:
                context['response_message'] = api_response.json()['choices'][0]['message']['content']
            else:
                context['response_message'] = f"Error: {api_response.status_code} - {api_response.text}"

        context['form'] = form
        return render(request, self.template_name, context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        monthly_summaries = get_monthly_summaries(self.this_company, 3)
        monthly_summaries_total = calculate_total_monthly_summaries(monthly_summaries, year_index=0, period_count=13)
        monthly_summaries_total_last_year = calculate_total_monthly_summaries(monthly_summaries, year_index=1, period_count=monthly_summaries[0]['actual_months_count'])

        # ラベル情報
        fiscal_month = self.this_company.fiscal_month
        months_label = [(fiscal_month + i) % 12 or 12 for i in range(1,13)]

        # 借入情報の取得
        debt_list, debt_list_totals, debt_list_nodisplay, debt_list_rescheduled, debt_list_finished = get_debt_list(self.this_company)
        debt_list = sorted(debt_list, key=lambda x: x['balances_monthly'][0], reverse=True)
        debt_list_byBank = get_debt_list_byAny('financial_institution', debt_list)
        debt_list_bySecuredType = get_debt_list_byAny('secured_type', debt_list)

        # Calculate weighted_average_interest for each month
        weighted_average_interest = [
            interest / balance if balance != 0 else 0
            for interest, balance in zip(12*debt_list_totals['total_interest_amount_monthly'], debt_list_totals['total_balances_monthly'])
        ]

        context.update({
            'title': 'Dash Board',
            'today': timezone.now().date(),
            'months_label': months_label,
            'monthly_summaries': monthly_summaries,
            'monthly_summaries_total': monthly_summaries_total,
            'monthly_summaries_total_last_year': monthly_summaries_total_last_year,
            'debt_list': debt_list,
            'debt_list_totals': debt_list_totals,
            'debt_list_byBank': debt_list_byBank,
            'debt_list_bySecuredType': debt_list_bySecuredType,
            'weighted_average_interest': weighted_average_interest,
            'today': timezone.now().date(),
        })
        return context


class LoginView(LoginView):
    form_class = LoginForm
    template_name = 'scoreai/login.html'


class ScoreLogoutView(LoginRequiredMixin, LogoutView):
    template_name = 'scoreai/logout.html'  # カスタムテンプレートを使用


##########################################################################
###                    User の View                                 ###
# 基本的な考え方
# 初期登録こちらで行う
# メール認証の後、VanCreworth側でCompanhyを登録し、その後Userに通知する
# 既存ユーザーが自社の社員を登録できるようにする
##########################################################################

# ユーザー登録機能は作らない
class UserCreateView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'scoreai/user_create_form.html'
    success_url = reverse_lazy('')  # ユーザー作成後のリダイレクト先

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.save()
        login(self.request, user)
        messages.success(self.request, 'アカウントが正常に作成されました。')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'アカウントの作成に失敗しました。入力内容を確認してください。')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'ユーザー登録'
        return context

class UserProfileView(LoginRequiredMixin, SelectedCompanyMixin, generic.TemplateView):
    template_name = 'scoreai/user_profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        username = self.request.user.username
        context['title'] = f'{username}のユーザー情報'
        context['user_companies'] = UserCompany.objects.filter(user=self.request.user)
        return context


class UserProfileUpdateView(LoginRequiredMixin, SelectedCompanyMixin, UpdateView):
    form_class = UserProfileUpdateForm
    template_name = 'scoreai/user_profile_update.html'
    success_url = reverse_lazy('user_profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'プロフィールが正常に更新されました。')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'プロフィール更新'
        context['user_companies'] = UserCompany.objects.filter(user=self.request.user)
        return context
##########################################################################
###                    Company の View                                 ###
##########################################################################

class CompanyDetailView(LoginRequiredMixin, DetailView):
    model = Company
    template_name = 'scoreai/company_detail.html'
    context_object_name = 'company'
    slug_field = 'id'
    slug_url_kwarg = 'id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'{self.object.name} の詳細'
        context['user_count'] = self.object.user_count
        context['users'] = UserCompany.objects.filter(company=self.object, active=True).select_related('user')
        return context

class CompanyUpdateView(LoginRequiredMixin, SelectedCompanyMixin, UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = 'scoreai/company_form.html'
    success_url = reverse_lazy('company_detail')

    def get_object(self, queryset=None):
        # SelectedCompanyMixin から選択された会社を取得
        return self.this_company

    def form_valid(self, form):
        messages.success(self.request, '会社情報が正常に更新されました。')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('company_detail', kwargs={'id': self.object.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '会社情報編集'
        return context

# 会社情報編集時に業種分類の親子関係の入力制御を画面上で行うための処理
def load_industry_subclassifications(request):
    industry_classification_id = request.GET.get('industry_classification')
    subclassifications = IndustrySubClassification.objects.filter(industry_classification_id=industry_classification_id).order_by('name')
    return JsonResponse(list(subclassifications.values('id', 'name')), safe=False)

##########################################################################
###                   FiscalSummary Yearの View                        ###
##########################################################################

class FiscalSummary_YearCreateView(LoginRequiredMixin, SelectedCompanyMixin, CreateView):
    model = FiscalSummary_Year
    form_class = FiscalSummary_YearForm
    template_name = 'scoreai/fiscal_summary_year_form.html'
    success_url = reverse_lazy('fiscal_summary_year_list')

    def get_initial(self):
        initial = super().get_initial()
        max_year = FiscalSummary_Year.objects.filter(company=self.this_company).aggregate(Max('year'))['year__max']
        if max_year is not None:
            initial['year'] = max_year + 1
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['year'].initial = self.get_initial().get('year')
        return form

    def form_valid(self, form):
        form.instance.company = self.this_company
        messages.success(self.request, f'{form.instance.year}年の決算データが正常に登録されました。' )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '年次財務サマリー作成'
        return context

class FiscalSummary_YearUpdateView(LoginRequiredMixin, SelectedCompanyMixin, UpdateView):
    model = FiscalSummary_Year
    form_class = FiscalSummary_YearForm
    template_name = 'scoreai/fiscal_summary_year_form.html'
    success_url = reverse_lazy('fiscal_summary_year_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        # フォームからインスタンスを取得（まだ保存はしない）
        fiscal_summary_year = form.save(commit=False)

        # 必要な情報を取得
        year = fiscal_summary_year.year
        industry_classification = fiscal_summary_year.company.industry_classification.id
        industry_subclassification = fiscal_summary_year.company.industry_subclassification.id
        company_size = fiscal_summary_year.company.company_size

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

        # インスタンスを再保存
        fiscal_summary_year.save()
        messages.success(self.request, '財務情報が正常に更新されました。')
        return HttpResponseRedirect(self.get_success_url())


def get_finance_score(year, industry_classification, industry_subclassification, company_size, indicator_name, value):
    """    
    Args:
        year (int): 対象の年度
        industry_classification (IndustryClassification): The industry classification instance.
        industry_subclassification (IndustrySubClassification): The industry subclassification instance.
        company_size (str): Company size ('s', 'm', or 'l').
        indicator_name: modelsで定義している指標を対応させる
        value (Decimal): The value to be scored.

    Returns:
        int: Score from 1 to 5, or None if benchmark data is not found.
    """
    # Group A indicators (高ければ高いほど良い指標)
    group_a_indicators = ["sales_growth_rate", "operating_profit_margin", "labor_productivity", "equity_ratio"]
    # Group B indicators (低ければ低いほど良い指標)
    group_b_indicators = ["operating_working_capital_turnover_period", "EBITDA_interest_bearing_debt_ratio"]

    try:
        indicator_instance = IndustryIndicator.objects.get(name=indicator_name)

        # Check for negative EBITDA
        if indicator_name == 'EBITDA_interest_bearing_debt_ratio' and (value is not None or value < 0):
            return 1
        
        # 最初の検索
        benchmark = IndustryBenchmark.objects.filter(
            year=year,
            industry_classification=industry_classification,
            industry_subclassification=industry_subclassification,
            company_size=company_size,
            indicator=indicator_instance
        ).first()
        # 見つからない場合は year-1 で再検索
        if not benchmark:
            benchmark = IndustryBenchmark.objects.filter(
                year=year-1,
                industry_classification=industry_classification,
                industry_subclassification=industry_subclassification,
                company_size=company_size,
                indicator=indicator_instance
            ).first()

        # それでも見つからない場合は year=2022 で再検索
        if not benchmark:
            benchmark = IndustryBenchmark.objects.filter(
                year=2022,
                industry_classification=industry_classification,
                industry_subclassification=industry_subclassification,
                company_size=company_size,
                indicator=indicator_instance
            ).first()

        # それでも見つからなければ None を返す
        if not benchmark:
            return None

    except (IndustryBenchmark.DoesNotExist, IndustryIndicator.DoesNotExist):
        return None

    # Retrieve benchmark ranges
    iv = Decimal(benchmark.range_iv)
    iii = Decimal(benchmark.range_iii)
    ii = Decimal(benchmark.range_ii)
    i = Decimal(benchmark.range_i)

    # Ensure value is a Decimal for accurate comparison
    value = Decimal(value)

    if indicator_instance.name in group_a_indicators:
        # Higher is better
        if value <= iv:
            return 1
        elif iv < value <= iii:
            return 2
        elif iii < value <= ii:
            return 3
        elif ii < value <= i:
            return 4
        elif value > i:
            return 5
    elif indicator_instance.name in group_b_indicators:
        # Lower is better
        if value >= iv:
            return 1
        elif iii <= value < iv:
            return 2
        elif ii <= value < iii:
            return 3
        elif i <= value < ii:
            return 4
        elif value < i:
            return 5
    else:
        return None


class FiscalSummary_YearDeleteView(LoginRequiredMixin, SelectedCompanyMixin, DeleteView):
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
        context['title'] = '決算データ削除確認'
        return context


@login_required
def download_fiscal_summary_year_csv(request, param=None):
   # SelectedCompanyMixinのget_selected_company方法を再現
    def get_selected_company():
        return UserCompany.objects.filter(user=request.user, is_selected=True).first()
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
        fiscal_summary_years = FiscalSummary_Year.objects.filter(company=this_company).order_by('year')
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


class FiscalSummary_YearDetailView(LoginRequiredMixin, SelectedCompanyMixin, DetailView):
    model = FiscalSummary_Year
    template_name = 'scoreai/fiscal_summary_year_detail.html'
    context_object_name = 'fiscal_summary_year'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 前年のデータを取得してcontextに追加
        # previous_year = self.object.year - 1
        previous_data = FiscalSummary_Year.objects.filter(year__lt=self.object.year).order_by('-year').first()
        next_data = FiscalSummary_Year.objects.filter(year__gt=self.object.year).order_by('year').first()
        context['previous_year_data'] = previous_data
        context['next_year_data'] = next_data

        # TechnicalTermの全データを取得し、nameをキーにして辞書を作成
        technical_terms = TechnicalTerm.objects.all()
        context['technical_terms'] = technical_terms

        # ベンチマーク指数を取得
        benchmark_index = get_benchmark_index(self.this_company.industry_classification, self.this_company.industry_subclassification, self.this_company.company_size, self.object.year)
        context['benchmark_index'] = benchmark_index
        context['title'] = '年次決算情報'

        return context

class LatestFiscalSummaryYearDetailView(LoginRequiredMixin, SelectedCompanyMixin, DetailView):
    def get(self, request, *args, **kwargs):
        # Get the most recent FiscalSummary_Year for the selected company
        latest_fiscal_summary_year = FiscalSummary_Year.objects.filter(
            company=self.this_company, 
            is_draft=False
        ).order_by('-year').first()
        
        if not latest_fiscal_summary_year:
            messages.error(request, "No fiscal summary year data available.")
            return redirect('fiscal_summary_year_list')  # Redirect to list view if no data is found

        # Redirect to the existing detail view with the latest fiscal summary year's ID
        return redirect('fiscal_summary_year_detail', pk=latest_fiscal_summary_year.pk)


# 決算年次推移
class FiscalSummary_YearListView(LoginRequiredMixin, SelectedCompanyMixin, ListView):
    model = FiscalSummary_Year
    template_name = 'scoreai/fiscal_summary_year_list.html'
    context_object_name = 'fiscal_summary_years'

    def get_queryset(self):
        is_draft = self.request.GET.get('is_draft', 'false').lower() == 'true'
        page_param = int(self.request.GET.get('page_param', 1))
        years_in_page = int(self.request.GET.get('years_in_page', 5))  # Default to 5 if not specified

        queryset = FiscalSummary_Year.objects.filter(company=self.this_company).order_by('-year')
        
        if not is_draft:
            queryset = queryset.filter(is_draft=False)

        # Calculate the start and end indices for slicing the queryset
        start_index = (page_param - 1) * years_in_page
        end_index = start_index + years_in_page

        return queryset[start_index:end_index]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate total pages
        total_records = FiscalSummary_Year.objects.filter(company=self.this_company).count()
        years_in_page = int(self.request.GET.get('years_in_page', 5))
        context['total_pages'] = (total_records + years_in_page - 1) // years_in_page  # Calculate total pages, rounding up

        # Add page_param and years_in_page to the context
        context['page_param'] = self.request.GET.get('page_param', 1)
        context['years_in_page'] = years_in_page

        context['title'] = '決算年次推移'
        return context


class ImportFiscalSummary_Year(LoginRequiredMixin, SelectedCompanyMixin, FormView):
    template_name = "scoreai/import_fiscal_summary_year.html"
    form_class = CsvUploadForm
    success_url = reverse_lazy('fiscal_summary_year_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '年度別財務サマリーのインポート'
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
                    existing_data = FiscalSummary_Year.objects.filter(
                        company=self.this_company,
                        year=year,
                        version='1',
                    ).exists()

                    if existing_data and not override_flag:
                        messages.error(
                            self.request,
                            f'{year}年の決算データは既に存在します。上書きする場合は「既存データを上書きする」を選択してください。'
                        )
                        return self.form_invalid(form)
                    else:
                        FiscalSummary_Year.objects.update_or_create(
                            company=self.this_company,
                            year=year,
                            version='1',
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

class FiscalSummary_MonthCreateView(LoginRequiredMixin, SelectedCompanyMixin, CreateView):
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
        form.fields['fiscal_summary_year'].queryset = FiscalSummary_Year.objects.filter(company=company)
        return form

    def form_valid(self, form):
        form.instance.fiscal_summary_year.company = self.this_company
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '月次財務サマリー作成'
        return context


class FiscalSummary_MonthUpdateView(LoginRequiredMixin, SelectedCompanyMixin, UpdateView):
    model = FiscalSummary_Month
    form_class = FiscalSummary_MonthForm
    template_name = 'scoreai/fiscal_summary_month_form.html'
    success_url = reverse_lazy('fiscal_summary_month_list')

    def get_queryset(self):
        return FiscalSummary_Month.objects.filter(fiscal_summary_year__company=self.this_company).order_by('-fiscal_summary_year__year', 'period')

    def get_object(self, queryset=None):
        obj = super(UpdateView, self).get_object(queryset)
        if obj.fiscal_summary_year.company != self.this_company:
            raise PermissionDenied("このデータを更新する権限がありません。")
        return obj

    def form_valid(self, form):
        # fiscal_summary_yearの変更を防ぐ
        form.instance.fiscal_summary_year = self.object.fiscal_summary_year
        response = super().form_valid(form)
        messages.success(self.request, f'{self.object.fiscal_summary_year.year}年{self.object.period}月の月次データを更新しました。')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '月次財務サマリー編集'
        context['fiscal_summary_year'] = self.object.fiscal_summary_year
        return context


class FiscalSummary_MonthDeleteView(LoginRequiredMixin, SelectedCompanyMixin, DeleteView):
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
        context['title'] = '月次財務サマリー削除確認'
        return context

class FiscalSummary_MonthDetailView(LoginRequiredMixin, SelectedCompanyMixin, DetailView):
    model = FiscalSummary_Month
    template_name = 'scoreai/fiscal_summary_month_detail.html'
    context_object_name = 'fiscal_summary_month'

    def get_queryset(self):
        return FiscalSummary_Month.objects.filter(fiscal_summary_year__company=self.this_company).order_by('-fiscal_summary_year__year', 'period')

    def get_object(self, queryset=None):
        # Override get_object to check if the object belongs to the selected company
        obj = super(DetailView, self).get_object(queryset)
        if obj.fiscal_summary_year.company != self.this_company:
            raise PermissionDenied("You don't have permission to access this object.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '月次財務詳細'
        return context

class FiscalSummary_MonthListView(LoginRequiredMixin, SelectedCompanyMixin, ListView):
    model = FiscalSummary_Month
    template_name = 'scoreai/fiscal_summary_month_list.html'
    context_object_name = 'fiscal_summary_months'

    def get_queryset(self):
        return FiscalSummary_Month.objects.filter(fiscal_summary_year__company=self.this_company).order_by('-fiscal_summary_year__year', 'period')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # URLパラメータから年数を取得。デフォルトは5年
        num_years = self.request.GET.get('years', 5)
        try:
            num_years = int(num_years)
            num_years = max(1, num_years)  # 最小値を1に設定
        except ValueError:
            num_years = 5  # 数値に変換できない場合はデフォルト値を使用
        
        # 月次サマリーデータを取得
        monthly_data = get_monthly_summaries(self.this_company, num_years)
        
        # 各年度の合計値を計算
        summary_data = [
            calculate_total_monthly_summaries(monthly_data, year_index=i)
            for i in range(num_years)
        ]
        
        # Calculate totals and rates for each metric
        for summary in monthly_data:
            total_sales = sum(item['sales'] for item in summary['data'])
            total_gross_profit = sum(item['gross_profit'] for item in summary['data'])
            total_operating_profit = sum(item['operating_profit'] for item in summary['data'])
            total_ordinary_profit = sum(item['ordinary_profit'] for item in summary['data'])

            summary['total_sales'] = total_sales
            summary['total_gross_profit'] = total_gross_profit
            summary['total_operating_profit'] = total_operating_profit
            summary['total_ordinary_profit'] = total_ordinary_profit

            # Calculate rates
            summary['total_gross_profit_rate'] = (total_gross_profit / total_sales * 100) if total_sales > 0 else 0
            summary['total_operating_profit_rate'] = (total_operating_profit / total_sales * 100) if total_sales > 0 else 0
            summary['total_ordinary_profit_rate'] = (total_ordinary_profit / total_sales * 100) if total_sales > 0 else 0

        # monthly_summaries_with_summaryにデータを格納
        monthly_summaries_with_summary = {
            'monthly_data': monthly_data,
            'summary_data': summary_data
        }
        
        # ラベル情報
        fiscal_month = self.this_company.fiscal_month
        months_label = [(fiscal_month + i) % 12 or 12 for i in range(1, 13)]

        context.update({
            'title': '月次財務サマリー一覧',
            'monthly_summaries_with_summary': monthly_summaries_with_summary,
            'months_label': months_label,
            'num_years': num_years,  # テンプレートで現在の年数を表示するために追加
        })
        return context


@login_required
def download_fiscal_summary_month_csv(request, param=None):
    def get_selected_company():
        return UserCompany.objects.filter(user=request.user, is_selected=True).first()
    
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
class ImportFiscalSummary_Month(LoginRequiredMixin, SelectedCompanyMixin, FormView):
    template_name = "scoreai/import_fiscal_summary_month.html"
    form_class = CsvUploadForm
    success_url = reverse_lazy('fiscal_summary_month_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '月次推移PLのインポート'
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
                
                fiscal_summary_year, created = FiscalSummary_Year.objects.get_or_create(
                    company=self.this_company,
                    year=fiscal_year
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
        except Exception as e:
            messages.error(self.request, f'CSVファイルの処理中にエラーが発生しました: {str(e)}')
            return self.form_invalid(form)

        return super().form_valid(form)


# Moneyfowardの月次推移表をアップしたらそのまま変換してインポートする
class ImportFiscalSummary_Month_FromMoneyforward(LoginRequiredMixin, SelectedCompanyMixin, FormView):
    template_name = "scoreai/import_fiscal_summary_month_MF.html"
    form_class = MoneyForwardCsvUploadForm_Month
    success_url = reverse_lazy('fiscal_summary_month_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['fiscal_year'].queryset = FiscalSummary_Year.objects.filter(company=self.this_company).order_by('-year')
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '月次推移PLのインポート（MoneyForwardから）'
        context['fiscal_years'] = FiscalSummary_Year.objects.filter(company=self.this_company)
        return context

    def form_valid(self, form):
        fiscal_year = form.cleaned_data['fiscal_year']
        csv_file = form.cleaned_data['csv_file']
        override_flag = form.cleaned_data.get('override_flag', False)

        try:
            # CSV解析
            file_data = csv_file.read().decode('shift-jis')
            csv_reader = csv.reader(file_data.splitlines())
            header = next(csv_reader)  # ヘッダー行を読み飛ばす

            # ヘッダーから月度情報を取得
            # 最初の2列をスキップ ("科目", "行")
            header_columns = header[2:]
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
            for month, sales, gross_profit, operating_profit, ordinary_profit in zip(
                months, sales_data, gross_profit_data, operating_profit_data, ordinary_profit_data
            ):
                existing_data = FiscalSummary_Month.objects.filter(
                    fiscal_summary_year=fiscal_year,
                    period=month
                ).exists()

                if existing_data and not override_flag:
                    messages.error(
                        self.request,
                        f'{fiscal_year.year}年の{month}月のデータは既に存在します。上書きする場合は「既存データを上書きする」を選択してください。'
                    )
                    return self.form_invalid(form)
                else:
                    FiscalSummary_Month.objects.update_or_create(
                        fiscal_summary_year=fiscal_year,
                        period=month,
                        defaults={
                            'sales': sales,
                            'gross_profit': gross_profit,
                            'operating_profit': operating_profit,
                            'ordinary_profit': ordinary_profit
                        }
                    )

            messages.success(self.request, 'CSVファイルが正常にインポートされました。')
        except Exception as e:
            messages.error(self.request, f'CSVファイルの処理中にエラーが発生しました: {str(e)}')
            return self.form_invalid(form)

        return super().form_valid(form)



# Moneyfowardの試算表（貸借対照表と損益計算書）をアップしたらそのまま変換してインポートする
class ImportFiscalSummary_Year_FromMoneyforward(LoginRequiredMixin, SelectedCompanyMixin, FormView):
    template_name = "scoreai/import_fiscal_summary_year_MF.html"
    form_class = MoneyForwardCsvUploadForm_Year
    success_url = reverse_lazy('fiscal_summary_year_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '残高試算表のインポート（MoneyForwardから）'
        return context

    def form_valid(self, form):
        csv_file = form.cleaned_data['csv_file']
        override_flag = form.cleaned_data.get('override_flag', False)

        try:
            # CSV解析
            file_data = csv_file.read().decode('shift-jis')
            csv_reader = csv.reader(file_data.splitlines())

            # 1行目の3列目から年度を取得
            first_row = next(csv_reader)
            fiscal_year = first_row[2][4:8]

            # 既に存在する場合は上書きチェック、存在しない場合は新規作成
            fiscal_summary_years = FiscalSummary_Year.objects.filter(year=fiscal_year, company=self.this_company)
            if fiscal_summary_years.exists():
                if not override_flag:
                    messages.error(
                        self.request,
                        f'{fiscal_year}年のデータは既に存在します。上書きする場合は「既存データを上書きする」を選択してください。'
                    )
                    return self.form_invalid(form)
            else:
                # Create a new record if none exists
                FiscalSummary_Year.objects.create(
                    year=fiscal_year,
                    company=self.this_company,
                    is_draft=True,
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

            for row in csv_reader:
                current_line += 1
                label_1 = row[0] # 1列目に項目名があるものから処理（勘定科目グループ）
                label_2 = row[1] # 2列目に項目名があるものから処理（勘定科目）
                mapping_label=f'{label_1}{label_2}'

                value = int(Decimal(row[5].replace(',', '')) // 1000) if row[5] else 0
                
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

            # データを更新
            FiscalSummary_Year.objects.update_or_create(
                year=fiscal_year,
                company=self.this_company,
                defaults=data_dict
            )

            # ループ終了後の処理
            logger.info("CSVファイルの全行を正常に処理しました。")

            messages.success(self.request, 'CSVファイルが正常にインポートされました。下書きデータとして保存されていますので、適宜必要な情報を追加してください。')

        except Exception as e:
            errors_label = f'{label_1}{label_2}'
            messages.error(
                self.request, 
                f'CSVファイルの処理中にエラーが発生しました: {str(e)} '
                f'(行番号: {current_line}, 項目名：{errors_label}、行データ：{row})'
            )
            return self.form_invalid(form)

        return super().form_valid(form)


##########################################################################
###                    Debt の View                                    ###
##########################################################################

class DebtCreateView(LoginRequiredMixin, SelectedCompanyMixin, CreateView):
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
        return context


class DebtDetailView(LoginRequiredMixin, SelectedCompanyMixin, DetailView):
    model = Debt
    template_name = 'scoreai/debt_detail.html'
    context_object_name = 'debt'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debt_list, debt_list_totals, debt_list_nodisplay, debt_list_rescheduled, debt_list_finished = get_debt_list(self.this_company)
        debt_list_byBank = get_debt_list_byAny('financial_institution', debt_list)
        debt_list_bySecuredType = get_debt_list_byAny('secured_type', debt_list)

        # 自分のデータのfinancial_institutionでフィルタをかけたdebt_list
        self_debt = self.get_object()
        debt_list_sameBank = [debt for debt in debt_list if debt['financial_institution'] == self_debt.financial_institution]

        context.update({            
            'title': '借入詳細',
            'debt_list': debt_list_sameBank,
            'debt_list_totals': debt_list_totals,
            'debt_list_rescheduled': debt_list_rescheduled,
            'debt_list_finished': debt_list_finished,
            'debt_list_nodisplay': debt_list_nodisplay,
            'today': timezone.now().date(),
        })
        return context


class DebtUpdateView(LoginRequiredMixin, SelectedCompanyMixin, UpdateView):
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
        context['title'] = '借入情報編集'
        return context


class DebtDeleteView(LoginRequiredMixin, SelectedCompanyMixin, DeleteView):
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
        context['title'] = '借入削除確認'
        return context

class DebtsAllListView(LoginRequiredMixin, SelectedCompanyMixin, ListView):
    model = Debt
    template_name = 'scoreai/debt_list_all.html'
    context_object_name = 'debt_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debt_list, debt_list_totals, debt_list_nodisplay, debt_list_rescheduled, debt_list_finished = get_debt_list(self.this_company)
        debt_list_byBank = get_debt_list_byAny('financial_institution', debt_list)
        debt_list_bySecuredType = get_debt_list_byAny('secured_type', debt_list)
        debt_list_bySecuredByManagement = get_debt_list_byAny('is_securedby_management', debt_list)
        debt_list_byCollateraled = get_debt_list_byAny('is_collateraled', debt_list)
        debt_list_byBankAndSecuredType = get_debt_list_byBankAndSecuredType(debt_list)
        # Calculate weighted_average_interest for each month
        weighted_average_interest = [
            interest / balance if balance != 0 else 0
            for interest, balance in zip(12*debt_list_totals['total_interest_amount_monthly'], debt_list_totals['total_balances_monthly'])
        ]

        context.update({
            'title': '全借入一覧',
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
        })
        return context


class DebtsByBankListView(LoginRequiredMixin, SelectedCompanyMixin, ListView):
    model = Debt
    template_name = 'scoreai/debt_list_byBank.html'
    context_object_name = 'debt_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debt_list, debt_list_totals, debt_list_nodisplay, debt_list_rescheduled, debt_list_finished = get_debt_list(self.this_company)
        debt_list_byBank = get_debt_list_byAny('financial_institution', debt_list)
        debt_list_bySecuredType = get_debt_list_byAny('secured_type', debt_list)
        debt_list_byBankAndSecuredType = get_debt_list_byBankAndSecuredType(debt_list)

        context.update({
            'title': '金融機関別借入一覧',
            'debt_list': debt_list,
            'debt_list_totals': debt_list_totals,
            'debt_list_byBank': debt_list_byBank,
        })
        return context


class DebtsBySecuredTypeListView(LoginRequiredMixin, SelectedCompanyMixin, ListView):
    model = Debt
    template_name = 'scoreai/debt_list_bySecuredType.html'
    context_object_name = 'debt_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debt_list, debt_list_totals, debt_list_nodisplay, debt_list_rescheduled, debt_list_finished = get_debt_list(self.this_company)
        debt_list_bySecuredType = get_debt_list_byAny('secured_type', debt_list)
        debt_list_byBankAndSecuredType = get_debt_list_byBankAndSecuredType(debt_list)

        context.update({
            'title': '保証別借入一覧',
            'debt_list_totals': debt_list_totals,
            'debt_list_bySecuredType': debt_list_bySecuredType,
            'debt_list_byBankAndSecuredType': debt_list_byBankAndSecuredType,
        })
        return context


class DebtsArchivedListView(LoginRequiredMixin, SelectedCompanyMixin, ListView):
    model = Debt
    template_name = 'scoreai/debt_list_archived.html'
    context_object_name = 'debt_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debt_list, debt_list_totals, debt_list_nodisplay, debt_list_rescheduled, debt_list_finished = get_debt_list(self.this_company)
        context.update({
            'title': 'アーカイブ済み借入一覧',
            'debt_list_nodisplay': debt_list_nodisplay,
        })
        return context

##########################################################################
###                 MeetingMinutes の View                             ###
##########################################################################

class MeetingMinutesCreateView(LoginRequiredMixin, SelectedCompanyMixin, CreateView):
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

class MeetingMinutesUpdateView(LoginRequiredMixin, SelectedCompanyMixin, UpdateView):
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


class MeetingMinutesListView(LoginRequiredMixin, SelectedCompanyMixin, ListView):
    model = MeetingMinutes
    template_name = 'scoreai/meeting_minutes_list.html'
    context_object_name = 'meeting_minutes'
    paginate_by = 10

    def get_queryset(self):
        queryset = MeetingMinutes.objects.filter(company=self.this_company).order_by('-meeting_date')
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
        context['title'] = 'ノート一覧'
        return context
        


class MeetingMinutesDetailView(LoginRequiredMixin, SelectedCompanyMixin, DetailView):
    model = MeetingMinutes
    template_name = 'scoreai/meeting_minutes_detail.html'
    context_object_name = 'meeting_minutes'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company_id'] = self.this_company.id
        context['title'] = 'ノート詳細' 
        # 現在の議事録を取得
        current_meeting = self.object
        
        # 同じ会社の直近5件の議事録を取得（現在の議事録を除く）
        recent_meetings = MeetingMinutes.objects.filter(
            company=current_meeting.company
        ).exclude(
            id=current_meeting.id
        ).order_by('-meeting_date')[:5]
        
        context['recent_meetings'] = recent_meetings
        return context


class MeetingMinutesDeleteView(LoginRequiredMixin, SelectedCompanyMixin, DeleteView):
    model = MeetingMinutes
    template_name = 'scoreai/meeting_minutes_confirm_delete.html'
    success_url = reverse_lazy('meeting_minutes_list')

    def get_queryset(self):
        return MeetingMinutes.objects.filter(company=self.this_company)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company_id'] = self.this_company.id
        context['title'] = 'ノート削除確認'
        return context


##########################################################################
###                 Stakeholder_name の View                         ###
##########################################################################

class Stakeholder_nameCreateView(LoginRequiredMixin, SelectedCompanyMixin, CreateView):
    model = Stakeholder_name
    form_class = Stakeholder_nameForm
    template_name = 'scoreai/stakeholder_name_form.html'
    success_url = reverse_lazy('stakeholder_name_list')

    def form_valid(self, form):
        form.instance.company = self.this_company
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '新規株主名登録'
        return context

class Stakeholder_nameUpdateView(LoginRequiredMixin, SelectedCompanyMixin, UpdateView):
    model = Stakeholder_name
    form_class = Stakeholder_nameForm
    template_name = 'scoreai/stakeholder_name_form.html'
    success_url = reverse_lazy('stakeholder_name_list')

    def get_queryset(self):
        # 選択された会社のStakeholder_nameオブジェクトのみを返す
        return Stakeholder_name.objects.filter(company=self.this_company)

    def get_success_url(self):
        return reverse_lazy('stakeholder_name_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, '株主情報を更新しました。')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stakeholder_name'] = self.object
        context['title'] = '株主情報編集'
        return context

class Stakeholder_nameListView(LoginRequiredMixin, SelectedCompanyMixin, ListView):
    model = Stakeholder_name
    template_name = 'scoreai/stakeholder_name_list.html'
    context_object_name = 'stakeholder_names'

    def get_queryset(self):
        return Stakeholder_name.objects.filter(company=self.this_company)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '株主名一覧'
        return context

class Stakeholder_nameDeleteView(LoginRequiredMixin, SelectedCompanyMixin, DeleteView):
    model = Stakeholder_name
    template_name = 'scoreai/stakeholder_name_confirm_delete.html'
    success_url = reverse_lazy('stakeholder_name_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, '株主名を削除しました。')
        return response


class Stakeholder_nameDetailView(LoginRequiredMixin, SelectedCompanyMixin, DetailView):
    model = Stakeholder_name
    template_name = 'scoreai/stakeholder_name_detail.html'
    context_object_name = 'stakeholder_name'

    def get_queryset(self):
        return Stakeholder_name.objects.filter(company=self.this_company)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '株主詳細'
        context['company_id'] = self.this_company.id
        return context


##########################################################################
###                 StockEvent の View                               ###
##########################################################################
class StockEventCreateView(LoginRequiredMixin, SelectedCompanyMixin, CreateView):
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
        context['title'] = '株式発行作成'
        return context


class StockEventUpdateView(LoginRequiredMixin, SelectedCompanyMixin, UpdateView):
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
        context['title'] = '株式発行編集'
        context['fiscal_summary_year'] = self.object.fiscal_summary_year
        return context


class StockEventListView(LoginRequiredMixin, SelectedCompanyMixin, ListView):
    model = StockEvent
    template_name = 'scoreai/stock_event_list.html'
    context_object_name = 'stock_events'

    def get_queryset(self):
        queryset = StockEvent.objects.filter(fiscal_summary_year__company=self.this_company).order_by('-event_date')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': '株式発行一覧',
        })
        return context

class StockEventDetailView(LoginRequiredMixin, SelectedCompanyMixin, DetailView):
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
        context['title'] = '株式発行詳細'
        # これに紐づくStockEventLineのデータを取得し、contextに含める
        context['stock_event_line'] = self.object.details.all()
        return context

class StockEventDeleteView(LoginRequiredMixin, SelectedCompanyMixin, DeleteView):
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
        context['title'] = '株式発行削除確認'
        return context


##########################################################################
###                 StockEventLine の View                              ###
##########################################################################
# StockEventから登録編集ができるようにする。

class StockEventLineCreateView(LoginRequiredMixin, SelectedCompanyMixin, CreateView):
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
        context['title'] = '株式イベント明細の追加'
        context['stock_event'] = self.stock_event
        return context


class StockEventLineUpdateView(LoginRequiredMixin, SelectedCompanyMixin, UpdateView):
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

    def form_valid(self, form):
        # fiscal_summary_yearの変更を防ぐ
        form.instance.stock_event = self.object.stock_event
        response = super().form_valid(form)
        messages.success(self.request, f'株式発行明細データを更新しました。')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stock_event'] = self.object.stock_event
        context['title'] = '株式イベント明細の編集'
        return context

##########################################################################
###                 FinancialInstitution の View                       ###
##########################################################################

class ImportFinancialInstitutionView(LoginRequiredMixin, DetailView):
    template_name = 'scoreai/import_financial_institution.html'

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, 'No file was uploaded.')
            return redirect('import_financial_institution')

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'File is not CSV type.')
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


class ImportIndustrySubClassificationView(FormView):
    form_class = IndustrySubClassificationImportForm
    template_name = 'scoreai/industry_subclassification_import.html'
    success_url = reverse_lazy('industry_subclassification_list')

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


class ImportIndustryBenchmarkView(LoginRequiredMixin, FormView):
    template_name = 'scoreai/import_industry_benchmark.html'
    form_class = IndustryBenchmarkImportForm
    success_url = reverse_lazy('industry_benchmark_list')  # 適切なリスト表示のURLに変更してください

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
        context['title'] = '業界別ベンチマーク一覧'
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
        context = super().get_context_data(**kwargs)
        clients_assigned = UserCompany.objects.filter(user=self.request.user, as_consultant=True)
        context['clients_assigned'] = clients_assigned
        context['title'] = 'クライアント一覧'
        return context



@login_required
def add_client(request, client_id):
    client = Company.objects.get(id=client_id)
    # 既に追加されているか確認（任意）
    if UserCompany.objects.filter(user=request.user, company=client).exists():
        messages.warning(request, f'クライアント "{client.name}" は既に追加されています。')
    else:
        UserCompany.objects.create(user=request.user, company=client, as_consultant=True)
        messages.success(request, f'クライアント "{client.name}" を正常に追加しました。')
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
        return context

class NewsListView(generic.TemplateView):
    template_name = 'scoreai/news_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'お知らせ'
        return context

class CompanyProfileView(generic.TemplateView):
    template_name = 'scoreai/score_company_profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '会社概要'
        return context

class HelpView(generic.TemplateView):
    template_name = 'scoreai/help.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'ヘルプ'
        return context

class ManualView(generic.TemplateView):
    template_name = 'scoreai/manual.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'マニュアル'
        return context

class TermsOfServiceView(generic.TemplateView):
    template_name = 'scoreai/terms_of_service.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '利用規約'
        return context

class PrivacyPolicyView(generic.TemplateView):
    template_name = 'scoreai/privacy_policy.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'プライバシーポリシー'
        return context

class LegalNoticeView(generic.TemplateView):
    template_name = 'scoreai/legal_notice.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '特定商取引法に基づく表示'
        return context

class SecurityPolicyView(generic.TemplateView):
    template_name = 'scoreai/security_policy.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'セキュリティポリシー'
        return context


class SampleView(generic.TemplateView):
    template_name = 'scoreai/ui-forms.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Sample Page'
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

def chat_view(request):
    response_message = None
    debts = Debt.objects.all()

    if request.method == 'POST':
        form = ChatForm(request.POST)
        if form.is_valid():
            user_message = form.cleaned_data['message']

            # Prepare the API request to ChatGPT
            headers = {
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json',
            }
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": user_message}],
            }
            # requestsをrequestに変更か
            api_response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)

            if api_response.status_code == 200:
                response_message = api_response.json()['choices'][0]['message']['content']
            else:
                response_message = f"Error: {api_response.status_code} - {api_response.text}"

    else:
        form = ChatForm()

    return render(request, 'scoreai/chat.html', {'form': form, 'response_message': response_message})



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
def get_debt_list(this_company):
    # 対象となる借入の絞り込み
    debts = Debt.objects.filter(company=this_company)

    debt_list = []
    debt_list_rescheduled = []
    debt_list_nodisplay = []
    debt_list_finished = []
    total_monthly_repayment = 0
    total_balances_monthly = [0] * 12  # Initialize with 12 zeros
    total_interest_amount_monthly = [0] * 12  # Initialize with 12 zeros
    total_balance_fy1 = 0
    total_balance_fy2 = 0
    total_balance_fy3 = 0
    total_balance_fy4 = 0
    total_balance_fy5 = 0
    # 返済開始している or していないで処理を分ける
    for debt in debts:
        if debt.is_nodisplay == True:
            debt_list_nodisplay.append(debt)
        elif debt.is_rescheduled == True:
            debt_list_rescheduled.append(debt)
        elif debt.remaining_months < 1:
            debt_list_finished.append(debt)
        else:

            total_monthly_repayment += debt.monthly_repayment
            total_balance_fy1 += debt.balance_fy1
            total_balance_fy2 += debt.balance_fy2
            total_balance_fy3 += debt.balance_fy3
            total_balance_fy4 += debt.balance_fy4
            total_balance_fy5 += debt.balance_fy5
            for i in range(12):
                total_balances_monthly[i] += debt.balances_monthly[i]
                total_interest_amount_monthly[i] += debt.interest_amount_monthly[i]
            debt_data = {
                'id': debt.id,
                'company': debt.company.name,
                'financial_institution': debt.financial_institution,
                'financial_institution_short_name': debt.financial_institution.short_name,
                'principal': debt.principal,
                'issue_date': debt.issue_date,
                'start_date': debt.start_date,
                'interest_rate': debt.interest_rate,
                'monthly_repayment': debt.monthly_repayment,
                'payment_terms': debt.payment_terms,
                'secured_type': debt.secured_type,
                'remaining_months': debt.remaining_months,
                'adjusted_amount_first': debt.adjusted_amount_first,
                'adjusted_amount_last': debt.adjusted_amount_last,
                'balances_monthly': debt.balances_monthly,
                'interest_amount_monthly': debt.interest_amount_monthly,
                'is_securedby_management': debt.is_securedby_management,
                'is_collateraled': debt.is_collateraled,
                'is_rescheduled': debt.is_rescheduled,
                'reschedule_date': debt.reschedule_date,
                'reschedule_balance': debt.reschedule_balance,
                'is_nodisplay': debt.is_nodisplay,
                'balance_fy1': debt.balance_fy1,
                'balance_fy2': debt.balance_fy2,
                'balance_fy3': debt.balance_fy3,
                'balance_fy4': debt.balance_fy4,
                'balance_fy5': debt.balance_fy5
            }
            debt_list.append(debt_data)

    # Sort debt_list by financial_institution and secured_type
    debt_list.sort(key=lambda x: (x['financial_institution'].name, x['secured_type'].name))
    # Add totals to the result
    debt_list_totals = {
        'total_monthly_repayment': total_monthly_repayment,
        'total_balances_monthly': total_balances_monthly,
        'total_interest_amount_monthly': total_interest_amount_monthly,
        'total_balance_fy1': total_balance_fy1,
        'total_balance_fy2': total_balance_fy2,
        'total_balance_fy3': total_balance_fy3,
        'total_balance_fy4': total_balance_fy4,
        'total_balance_fy5': total_balance_fy5,

    }

    return debt_list, debt_list_totals, debt_list_nodisplay, debt_list_rescheduled, debt_list_finished


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
                'balance_fy1': 0,
            }

        debt_list_byAny[debt[summary_field_label]]['principal'] += debt['principal']
        debt_list_byAny[debt[summary_field_label]]['monthly_repayment'] += debt['monthly_repayment']
        debt_list_byAny[debt[summary_field_label]]['balance_fy1'] += debt['balance_fy1']

        # Sum up the monthly balances
        for i in range(12):
            debt_list_byAny[debt[summary_field_label]]['balances_monthly'][i] += debt['balances_monthly'][i]
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
                'balance_fy1': 0,
            }

        debt_list_byBankAndSecuredType[key]['principal'] += debt['principal']
        debt_list_byBankAndSecuredType[key]['monthly_repayment'] += debt['monthly_repayment']
        debt_list_byBankAndSecuredType[key]['balance_fy1'] += debt['balance_fy1']

        # Sum up the monthly balances
        for i in range(12):
            debt_list_byBankAndSecuredType[key]['balances_monthly'][i] += debt['balances_monthly'][i]

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
