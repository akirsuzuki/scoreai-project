import csv
import logging
from io import TextIOWrapper
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView, TemplateView
from django.urls import reverse_lazy
from django.db import transaction
from django.db.models import Max, ProtectedError
from django.core.exceptions import FieldDoesNotExist

from ..models import (
    FiscalSummary_Year,
    UserCompany,
    TechnicalTerm,
    IndustryBenchmark
)
from ..forms import (
    FiscalSummary_YearForm,
    CsvUploadForm,
    MoneyForwardCsvUploadForm_Year
)
from ..mixins import SelectedCompanyMixin, TransactionMixin
from .utils import (
    get_finance_score,
    get_benchmark_index
)
from ..utils.csv_utils import read_csv_with_auto_encoding, validate_csv_structure

logger = logging.getLogger(__name__)

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
        fiscal_summary_year = form.save(commit=False)
        fiscal_summary_year.company = self.this_company
        fiscal_summary_year.version = 1
        if form.cleaned_data.get('is_budget') is None:
            fiscal_summary_year.is_budget = False

        company = fiscal_summary_year.company
        if company.industry_classification and company.industry_subclassification:
            year = fiscal_summary_year.year
            industry_classification = company.industry_classification
            industry_subclassification = company.industry_subclassification
            company_size = company.company_size

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

        fiscal_summary_year.save()
        self.object = fiscal_summary_year
        messages.success(self.request, f'{fiscal_summary_year.year}年の決算データが正常に登録されました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '年次財務諸表'
        context['show_title_card'] = False
        return context

class FiscalSummary_YearUpdateView(SelectedCompanyMixin, TransactionMixin, UpdateView):
    model = FiscalSummary_Year
    form_class = FiscalSummary_YearForm
    template_name = 'scoreai/fiscal_summary_year_form.html'
    success_url = reverse_lazy('fiscal_summary_year_list')

    def get_queryset(self):
        return FiscalSummary_Year.objects.filter(
            company=self.this_company
        )

    def form_valid(self, form):
        fiscal_summary_year = form.save(commit=False)
        fiscal_summary_year.company = self.this_company
        fiscal_summary_year.version = 1

        company = fiscal_summary_year.company
        if company.industry_classification and company.industry_subclassification:
            year = fiscal_summary_year.year
            industry_classification = company.industry_classification
            industry_subclassification = company.industry_subclassification
            company_size = company.company_size

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

        try:
            fiscal_summary_year.save()
            self.object = fiscal_summary_year
            messages.success(self.request, '財務情報が正常に更新されました。')
            return super().form_valid(form)
        except Exception as e:
            logger.error(f"Error saving FiscalSummary_Year: {e}", exc_info=True)
            messages.error(self.request, f'財務情報の更新中にエラーが発生しました: {str(e)}')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '年次財務諸表'
        context['show_title_card'] = False
        return context

class FiscalSummary_YearDeleteView(SelectedCompanyMixin, DeleteView):
    model = FiscalSummary_Year
    template_name = 'scoreai/fiscal_summary_year_confirm_delete.html'
    success_url = reverse_lazy('fiscal_summary_year_list')

    def form_valid(self, form):
        fiscal_summary_year = self.get_object()
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
        try:
            fiscal_summary_years = [get_object_or_404(FiscalSummary_Year, pk=str(param), company=this_company)]
        except ValueError:
            return HttpResponse("無効なパラメータです。", status=400)
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
            fiscal_summary_year.total_stakeholder_equity,
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
        fiscal_summary_year = self.object
        
        available_years = FiscalSummary_Year.objects.filter(
            company=self.this_company
        ).values_list('year', flat=True).distinct().order_by('-year')
        context['available_years'] = list(available_years)
        context['selected_year'] = fiscal_summary_year.year
        context['is_budget'] = fiscal_summary_year.is_budget
        
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
                current_score = getattr(fiscal_summary_year, f'score_{indicator_name}', None)
                
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
                        setattr(fiscal_summary_year, f'score_{indicator_name}', score)
                        needs_save = True
        
        if needs_save:
            fiscal_summary_year.save()
        
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

        technical_terms = TechnicalTerm.objects.all()
        context['technical_terms'] = technical_terms

        benchmark_index = get_benchmark_index(
            self.this_company.industry_classification,
            self.this_company.industry_subclassification,
            self.this_company.company_size,
            self.object.year
        )
        context['benchmark_index'] = benchmark_index
        
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
        
        context['title'] = '年次財務諸表'
        context['show_title_card'] = False

        return context

class LatestFiscalSummaryYearDetailView(SelectedCompanyMixin, TemplateView):
    template_name = 'scoreai/fiscal_summary_year_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        year_param = self.request.GET.get('year')
        is_budget_param = self.request.GET.get('is_budget', 'false')
        
        available_years = FiscalSummary_Year.objects.filter(
            company=self.this_company
        ).values_list('year', flat=True).distinct().order_by('-year')
        
        context['available_years'] = list(available_years)
        
        if year_param:
            try:
                selected_year = int(year_param)
            except ValueError:
                selected_year = available_years[0] if available_years else None
        else:
            selected_year = available_years[0] if available_years else None
        
        context['selected_year'] = selected_year
        is_budget = is_budget_param.lower() == 'true'
        context['is_budget'] = is_budget
        
        data_not_found = False
        previous_fiscal_summary_year = None
        fiscal_summary_year = None
        
        if selected_year:
            fiscal_summary_year = FiscalSummary_Year.objects.filter(
                company=self.this_company,
                year=selected_year,
                is_budget=is_budget,
                is_draft=False
            ).order_by('-version').first()
            
            if not fiscal_summary_year:
                data_not_found = True
                context['data_not_found'] = True
                context['data_not_found_year'] = selected_year
                context['data_not_found_is_budget'] = is_budget
                
                if available_years:
                    latest_year = available_years[0]
                    previous_fiscal_summary_year = FiscalSummary_Year.objects.filter(
                        company=self.this_company,
                        year=latest_year,
                        is_budget=False,
                        is_draft=False
                    ).order_by('-version').first()
        else:
            data_not_found = True
            context['data_not_found'] = True
        
        if data_not_found and previous_fiscal_summary_year:
            fiscal_summary_year = previous_fiscal_summary_year
        elif not fiscal_summary_year:
            context['data_not_found'] = True
        
        if fiscal_summary_year:
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
                    current_score = getattr(fiscal_summary_year, f'score_{indicator_name}', None)
                    
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
                            setattr(fiscal_summary_year, f'score_{indicator_name}', score)
                            needs_save = True
            
            if needs_save:
                fiscal_summary_year.save()
            
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
            
            technical_terms = TechnicalTerm.objects.all()
            context['technical_terms'] = technical_terms
            
            benchmark_index = get_benchmark_index(
                self.this_company.industry_classification,
                self.this_company.industry_subclassification,
                self.this_company.company_size,
                fiscal_summary_year.year
            )
            context['benchmark_index'] = benchmark_index
            
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

class FiscalSummary_YearListView(SelectedCompanyMixin, ListView):
    model = FiscalSummary_Year
    template_name = 'scoreai/fiscal_summary_year_list.html'
    context_object_name = 'fiscal_summary_years'

    def get_queryset(self):
        is_draft = self.request.GET.get('is_draft', 'false').lower() == 'true'
        page_param = int(self.request.GET.get('page_param', 1))
        years_in_page = int(self.request.GET.get('years_in_page', 5))
        show_all = self.request.GET.get('show_all', 'false').lower() == 'true'
        start_year = self.request.GET.get('start_year')
        end_year = self.request.GET.get('end_year')

        queryset = FiscalSummary_Year.objects.filter(
            company=self.this_company,
            is_budget=False
        ).select_related('company').order_by('-year')
        
        if not is_draft:
            queryset = queryset.filter(is_draft=False)

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

        if show_all:
            return queryset

        start_index = (page_param - 1) * years_in_page
        end_index = start_index + years_in_page

        return queryset[start_index:end_index]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        is_draft = self.request.GET.get('is_draft', 'false').lower() == 'true'
        show_all = self.request.GET.get('show_all', 'false').lower() == 'true'
        start_year = self.request.GET.get('start_year')
        end_year = self.request.GET.get('end_year')
        years_in_page = int(self.request.GET.get('years_in_page', 5))
        
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
        
        total_records = base_queryset.count()
        
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
        
        context['page_param'] = self.request.GET.get('page_param', 1)
        context['years_in_page'] = years_in_page
        context['show_all'] = show_all
        context['start_year'] = start_year
        context['end_year'] = end_year
        context['is_draft'] = is_draft

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
        context['show_title_card'] = False
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
                    existing_data = FiscalSummary_Year.objects.filter(
                        company=self.this_company,
                        year=year,
                        is_budget=False,
                    ).exists()

                    if existing_data and not override_flag:
                        messages.error(
                            self.request,
                            f'{year}年の実績データは既に存在します。上書きする場合は「既存データを上書きする」を選択してください。'
                        )
                        return self.form_invalid(form)
                    else:
                        defaults['is_budget'] = False
                        defaults['is_draft'] = False
                        defaults['version'] = 1
                        FiscalSummary_Year.objects.update_or_create(
                            company=self.this_company,
                            year=year,
                            is_budget=False,
                            defaults=defaults
                        )
                else:
                    messages.warning(self.request, '年度が指定されていない行をスキップしました。')
            
            messages.success(self.request, 'CSVファイルが正常にインポートされました。')
        except Exception as e:
            messages.error(self.request, f'CSVファイルの処理中にエラーが発生しました: {str(e)}')
            return self.form_invalid(form)

        return super().form_valid(form)

class ImportFiscalSummary_Year_FromMoneyforward(SelectedCompanyMixin, TransactionMixin, FormView):
    template_name = "scoreai/import_fiscal_summary_year_MF.html"
    form_class = MoneyForwardCsvUploadForm_Year
    success_url = None

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
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
            csv_data, encoding = read_csv_with_auto_encoding(csv_file)
            
            if not csv_data:
                messages.error(self.request, 'CSVファイルが空です。')
                return self.form_invalid(form)
            
            is_valid, error_msg = validate_csv_structure(
                csv_data,
                min_rows=2
            )
            
            if not is_valid:
                messages.error(self.request, f'CSVファイルの構造が不正です: {error_msg}')
                return self.form_invalid(form)
            
            csv_reader = iter(csv_data)

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
                
                int(fiscal_year)
            except (IndexError, ValueError) as e:
                messages.error(
                    self.request, 
                    f'年度の取得に失敗しました。CSVファイルの1行目3列目に年度情報が含まれているか確認してください。'
                )
                logger.error(f"Fiscal year extraction error: {e}", exc_info=True)
                return self.form_invalid(form)

            existing_actual = FiscalSummary_Year.objects.filter(
                year=fiscal_year, 
                company=self.this_company,
                is_budget=False
            ).first()
            
            if existing_actual:
                if not override_flag:
                    messages.error(
                        self.request,
                        f'{fiscal_year}年の実績データは既に存在します。上書きする場合は「既存データを上書きする」を選択してください。'
                    )
                    return self.form_invalid(form)
            else:
                FiscalSummary_Year.objects.get_or_create(
                    year=fiscal_year,
                    company=self.this_company,
                    is_budget=False,
                    defaults={
                        'is_draft': True,
                    }
                )

            current_line = 0
            sales_line = 0
            gross_profit_line = 0
            operating_profit_line = 0
            ordinary_profit_line = 0

            data_dict = {}

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
                if not row or len(row) < 1:
                    logger.warning(f"空行または不完全な行が検出されました（行番号: {current_line}）")
                    continue

                try:
                    if len(row) >= 5 and row[0] != '':
                        mapping_label = row[0]
                    elif len(row) >= 2 and row[1] != '':
                        mapping_label = row[1]
                    else:
                        logger.warning(f"この行はスキップします（行番号: {current_line}）")
                        continue

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

            data_dict['is_budget'] = False
            fiscal_summary_year, created = FiscalSummary_Year.objects.update_or_create(
                year=fiscal_year,
                company=self.this_company,
                is_budget=False,
                defaults=data_dict
            )

            logger.info("CSVファイルの全行を正常に処理しました。")

            updated_fields_count = len([k for k, v in data_dict.items() if v != 0])
            
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

        form = self.form_class()
        form.fields['fiscal_year'].queryset = FiscalSummary_Year.objects.filter(company=self.this_company).order_by('-year')
        context = self.get_context_data(form=form)
        return render(self.request, self.template_name, context)
