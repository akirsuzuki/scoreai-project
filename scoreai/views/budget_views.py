"""
予算管理機能のビュー
"""
from typing import Any, Dict
from django import forms
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, FormView, TemplateView
from django.db.models import Q, Max
from django.utils import timezone
from datetime import datetime

from ..models import FiscalSummary_Year, FiscalSummary_Month, Company
from ..forms import FiscalSummary_YearForm, FiscalSummary_MonthForm
from ..mixins import SelectedCompanyMixin, TransactionMixin
import logging

logger = logging.getLogger(__name__)


class FiscalSummary_YearBudgetCreateView(SelectedCompanyMixin, TransactionMixin, CreateView):
    """年次予算作成ビュー"""
    model = FiscalSummary_Year
    form_class = FiscalSummary_YearForm
    template_name = 'scoreai/fiscal_summary_year_budget_form.html'
    success_url = reverse_lazy('fiscal_summary_year_list')

    def get_initial(self):
        initial = super().get_initial()
        max_year = FiscalSummary_Year.objects.filter(
            company=self.this_company
        ).aggregate(Max('year'))['year__max']
        if max_year is not None:
            initial['year'] = max_year + 1
        # 予算フラグを設定
        initial['is_budget'] = True
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['year'].initial = self.get_initial().get('year')
        return form

    def form_valid(self, form):
        form.instance.company = self.this_company
        form.instance.is_budget = True  # 予算として設定
        form.instance.is_draft = False  # 予算は下書きではない
        messages.success(self.request, f'{form.instance.year}年の予算データが正常に登録されました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '年次予算作成'
        context['is_budget'] = True
        return context


class FiscalSummary_YearBudgetUpdateView(SelectedCompanyMixin, TransactionMixin, UpdateView):
    """年次予算更新ビュー"""
    model = FiscalSummary_Year
    form_class = FiscalSummary_YearForm
    template_name = 'scoreai/fiscal_summary_year_budget_form.html'
    success_url = reverse_lazy('fiscal_summary_year_list')

    def get_queryset(self):
        return FiscalSummary_Year.objects.filter(
            company=self.this_company,
            is_budget=True
        )

    def form_valid(self, form):
        form.instance.is_budget = True  # 予算として設定
        messages.success(self.request, f'{form.instance.year}年の予算データが正常に更新されました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '年次予算更新'
        context['is_budget'] = True
        context['show_title_card'] = False  # タイトルカードを非表示
        return context


class FiscalSummary_MonthBudgetCreateView(SelectedCompanyMixin, CreateView):
    """月次予算作成ビュー"""
    model = FiscalSummary_Month
    form_class = FiscalSummary_MonthForm
    template_name = 'scoreai/fiscal_summary_month_budget_form.html'
    success_url = reverse_lazy('fiscal_summary_month_list')

    def get_initial(self):
        initial = super().get_initial()
        company = self.this_company
        # 予算の年度を取得（実績の最新年度+1、または予算が既にある場合はその年度）
        latest_budget_year = FiscalSummary_Year.objects.filter(
            company=company,
            is_budget=True
        ).order_by('-year').first()
        
        if latest_budget_year:
            initial['fiscal_summary_year'] = latest_budget_year
        else:
            # 予算がない場合は実績の最新年度+1を取得
            latest_actual_year = FiscalSummary_Year.objects.filter(
                company=company,
                is_budget=False
            ).order_by('-year').first()
            if latest_actual_year:
                # 予算年度を作成（存在しない場合）
                budget_year, created = FiscalSummary_Year.objects.get_or_create(
                    company=company,
                    year=latest_actual_year.year + 1,
                    is_budget=True,
                    defaults={'is_draft': False}
                )
                initial['fiscal_summary_year'] = budget_year
        # 予算フラグを設定
        initial['is_budget'] = True
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        company = self.this_company
        # 予算の年度のみを表示
        form.fields['fiscal_summary_year'].queryset = FiscalSummary_Year.objects.filter(
            company=company,
            is_budget=True
        )
        return form

    def form_valid(self, form):
        form.instance.is_budget = True  # 予算として設定
        messages.success(self.request, f'月次予算データが正常に登録されました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '月次予算作成'
        context['is_budget'] = True
        context['show_title_card'] = False  # タイトルカードを非表示
        return context


class FiscalSummary_MonthBudgetUpdateView(SelectedCompanyMixin, UpdateView):
    """月次予算更新ビュー"""
    model = FiscalSummary_Month
    form_class = FiscalSummary_MonthForm
    template_name = 'scoreai/fiscal_summary_month_budget_form.html'
    success_url = reverse_lazy('fiscal_summary_month_list')

    def get_queryset(self):
        return FiscalSummary_Month.objects.filter(
            fiscal_summary_year__company=self.this_company,
            is_budget=True
        )

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        company = self.this_company
        # 予算の年度のみを表示
        form.fields['fiscal_summary_year'].queryset = FiscalSummary_Year.objects.filter(
            company=company,
            is_budget=True
        )
        return form

    def form_valid(self, form):
        form.instance.is_budget = True  # 予算として設定
        messages.success(self.request, f'月次予算データが正常に更新されました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '月次予算更新'
        context['is_budget'] = True
        context['show_title_card'] = False  # タイトルカードを非表示
        return context


class BudgetVsActualComparisonView(SelectedCompanyMixin, TemplateView):
    """予算と実績の比較ビュー"""
    template_name = 'scoreai/budget_vs_actual_comparison.html'

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        company = self.this_company
        
        # 年度を取得（デフォルトは最新年度）
        year = int(self.request.GET.get('year', timezone.now().year))
        
        # 予算データを取得
        budget_year = FiscalSummary_Year.objects.filter(
            company=company,
            year=year,
            is_budget=True
        ).first()
        
        # 実績データを取得
        actual_year = FiscalSummary_Year.objects.filter(
            company=company,
            year=year,
            is_budget=False,
            is_draft=False
        ).first()
        
        # 月次データを取得
        budget_monthly = []
        actual_monthly = []
        
        if budget_year:
            budget_monthly = FiscalSummary_Month.objects.filter(
                fiscal_summary_year=budget_year,
                is_budget=True
            ).order_by('period')
        
        if actual_year:
            actual_monthly = FiscalSummary_Month.objects.filter(
                fiscal_summary_year=actual_year,
                is_budget=False
            ).order_by('period')
        
        context.update({
            'title': '予算実績比較',
            'year': year,
            'budget_year': budget_year,
            'actual_year': actual_year,
            'budget_monthly': budget_monthly,
            'actual_monthly': actual_monthly,
            'available_years': FiscalSummary_Year.objects.filter(
                company=company
            ).values_list('year', flat=True).distinct().order_by('-year'),
        })
        
        return context


class BudgetVsActualYearlyComparisonView(SelectedCompanyMixin, TemplateView):
    """年次予算と実績の詳細比較ビュー（経営指標含む）"""
    template_name = 'scoreai/budget_vs_actual_yearly.html'

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        company = self.this_company
        
        # 利用可能な年度を取得
        available_years_list = list(FiscalSummary_Year.objects.filter(
            company=company
        ).values_list('year', flat=True).distinct().order_by('-year'))
        
        # デフォルト年度を取得
        default_year = None
        if available_years_list:
            default_year = available_years_list[0]
        else:
            default_year = timezone.now().year
        
        # 年度を取得
        year_param = self.request.GET.get('year')
        if year_param:
            try:
                year = int(year_param)
            except ValueError:
                year = default_year
        else:
            year = default_year
        
        # 予算データを取得
        budget_year = FiscalSummary_Year.objects.filter(
            company=company,
            year=year,
            is_budget=True
        ).first()
        
        # 実績データを取得（is_draftの条件を緩和）
        actual_year = FiscalSummary_Year.objects.filter(
            company=company,
            year=year,
            is_budget=False
        ).order_by('-is_draft').first()
        
        # 経営指標を計算
        financial_indicators = {}
        if budget_year and actual_year:
            # 売上高関連
            financial_indicators['sales'] = {
                'budget': budget_year.sales,
                'actual': actual_year.sales,
                'diff': actual_year.sales - budget_year.sales,
                'diff_rate': ((actual_year.sales - budget_year.sales) / budget_year.sales * 100) if budget_year.sales > 0 else 0,
            }
            
            # 利益関連
            financial_indicators['gross_profit'] = {
                'budget': budget_year.gross_profit,
                'actual': actual_year.gross_profit,
                'diff': actual_year.gross_profit - budget_year.gross_profit,
                'diff_rate': ((actual_year.gross_profit - budget_year.gross_profit) / budget_year.gross_profit * 100) if budget_year.gross_profit != 0 else 0,
            }
            
            financial_indicators['operating_profit'] = {
                'budget': budget_year.operating_profit,
                'actual': actual_year.operating_profit,
                'diff': actual_year.operating_profit - budget_year.operating_profit,
                'diff_rate': ((actual_year.operating_profit - budget_year.operating_profit) / budget_year.operating_profit * 100) if budget_year.operating_profit != 0 else 0,
            }
            
            financial_indicators['ordinary_profit'] = {
                'budget': budget_year.ordinary_profit,
                'actual': actual_year.ordinary_profit,
                'diff': actual_year.ordinary_profit - budget_year.ordinary_profit,
                'diff_rate': ((actual_year.ordinary_profit - budget_year.ordinary_profit) / budget_year.ordinary_profit * 100) if budget_year.ordinary_profit != 0 else 0,
            }
            
            financial_indicators['net_profit'] = {
                'budget': budget_year.net_profit,
                'actual': actual_year.net_profit,
                'diff': actual_year.net_profit - budget_year.net_profit,
                'diff_rate': ((actual_year.net_profit - budget_year.net_profit) / budget_year.net_profit * 100) if budget_year.net_profit != 0 else 0,
            }
            
            # 経営指標
            financial_indicators['gross_profit_margin'] = {
                'budget': float(budget_year.gross_profit_margin) if budget_year.gross_profit_margin else 0,
                'actual': float(actual_year.gross_profit_margin) if actual_year.gross_profit_margin else 0,
                'diff': (float(actual_year.gross_profit_margin) if actual_year.gross_profit_margin else 0) - (float(budget_year.gross_profit_margin) if budget_year.gross_profit_margin else 0),
            }
            
            financial_indicators['operating_profit_margin'] = {
                'budget': float(budget_year.operating_profit_margin) if budget_year.operating_profit_margin else 0,
                'actual': float(actual_year.operating_profit_margin) if actual_year.operating_profit_margin else 0,
                'diff': (float(actual_year.operating_profit_margin) if actual_year.operating_profit_margin else 0) - (float(budget_year.operating_profit_margin) if budget_year.operating_profit_margin else 0),
            }
            
            financial_indicators['ROA'] = {
                'budget': float(budget_year.ROA) if budget_year.ROA else 0,
                'actual': float(actual_year.ROA) if actual_year.ROA else 0,
                'diff': (float(actual_year.ROA) if actual_year.ROA else 0) - (float(budget_year.ROA) if budget_year.ROA else 0),
            }
            
            financial_indicators['equity_ratio'] = {
                'budget': float(budget_year.equity_ratio) if budget_year.equity_ratio else 0,
                'actual': float(actual_year.equity_ratio) if actual_year.equity_ratio else 0,
                'diff': (float(actual_year.equity_ratio) if actual_year.equity_ratio else 0) - (float(budget_year.equity_ratio) if budget_year.equity_ratio else 0),
            }
            
            financial_indicators['current_ratio'] = {
                'budget': float(budget_year.current_ratio) if budget_year.current_ratio else 0,
                'actual': float(actual_year.current_ratio) if actual_year.current_ratio else 0,
                'diff': (float(actual_year.current_ratio) if actual_year.current_ratio else 0) - (float(budget_year.current_ratio) if budget_year.current_ratio else 0),
            }
            
            # グラフ用データ
            chart_data = {
                'labels': ['売上高', '粗利益', '営業利益', '経常利益', '当期純利益'],
                'budget': [
                    budget_year.sales,
                    budget_year.gross_profit,
                    budget_year.operating_profit,
                    budget_year.ordinary_profit,
                    budget_year.net_profit,
                ],
                'actual': [
                    actual_year.sales,
                    actual_year.gross_profit,
                    actual_year.operating_profit,
                    actual_year.ordinary_profit,
                    actual_year.net_profit,
                ],
            }
            
            # 経営指標グラフ用データ
            indicators_chart_data = {
                'labels': ['売上総利益率', '営業利益率', 'ROA', '自己資本比率', '流動比率'],
                'budget': [
                    float(budget_year.gross_profit_margin) if budget_year.gross_profit_margin else 0,
                    float(budget_year.operating_profit_margin) if budget_year.operating_profit_margin else 0,
                    float(budget_year.ROA) if budget_year.ROA else 0,
                    float(budget_year.equity_ratio) if budget_year.equity_ratio else 0,
                    float(budget_year.current_ratio) if budget_year.current_ratio else 0,
                ],
                'actual': [
                    float(actual_year.gross_profit_margin) if actual_year.gross_profit_margin else 0,
                    float(actual_year.operating_profit_margin) if actual_year.operating_profit_margin else 0,
                    float(actual_year.ROA) if actual_year.ROA else 0,
                    float(actual_year.equity_ratio) if actual_year.equity_ratio else 0,
                    float(actual_year.current_ratio) if actual_year.current_ratio else 0,
                ],
            }
            
            # BS（貸借対照表）データを計算
            bs_indicators = {}
            
            # 資産の部
            bs_indicators['cash_and_deposits'] = {
                'budget': budget_year.cash_and_deposits,
                'actual': actual_year.cash_and_deposits,
                'diff': actual_year.cash_and_deposits - budget_year.cash_and_deposits,
                'diff_rate': ((actual_year.cash_and_deposits - budget_year.cash_and_deposits) / budget_year.cash_and_deposits * 100) if budget_year.cash_and_deposits != 0 else 0,
            }
            
            bs_indicators['accounts_receivable'] = {
                'budget': budget_year.accounts_receivable,
                'actual': actual_year.accounts_receivable,
                'diff': actual_year.accounts_receivable - budget_year.accounts_receivable,
                'diff_rate': ((actual_year.accounts_receivable - budget_year.accounts_receivable) / budget_year.accounts_receivable * 100) if budget_year.accounts_receivable != 0 else 0,
            }
            
            bs_indicators['inventory'] = {
                'budget': budget_year.inventory,
                'actual': actual_year.inventory,
                'diff': actual_year.inventory - budget_year.inventory,
                'diff_rate': ((actual_year.inventory - budget_year.inventory) / budget_year.inventory * 100) if budget_year.inventory != 0 else 0,
            }
            
            bs_indicators['total_current_assets'] = {
                'budget': budget_year.total_current_assets,
                'actual': actual_year.total_current_assets,
                'diff': actual_year.total_current_assets - budget_year.total_current_assets,
                'diff_rate': ((actual_year.total_current_assets - budget_year.total_current_assets) / budget_year.total_current_assets * 100) if budget_year.total_current_assets != 0 else 0,
            }
            
            bs_indicators['total_fixed_assets'] = {
                'budget': budget_year.total_fixed_assets,
                'actual': actual_year.total_fixed_assets,
                'diff': actual_year.total_fixed_assets - budget_year.total_fixed_assets,
                'diff_rate': ((actual_year.total_fixed_assets - budget_year.total_fixed_assets) / budget_year.total_fixed_assets * 100) if budget_year.total_fixed_assets != 0 else 0,
            }
            
            bs_indicators['total_assets'] = {
                'budget': budget_year.total_assets,
                'actual': actual_year.total_assets,
                'diff': actual_year.total_assets - budget_year.total_assets,
                'diff_rate': ((actual_year.total_assets - budget_year.total_assets) / budget_year.total_assets * 100) if budget_year.total_assets != 0 else 0,
            }
            
            # 負債の部
            bs_indicators['accounts_payable'] = {
                'budget': budget_year.accounts_payable,
                'actual': actual_year.accounts_payable,
                'diff': actual_year.accounts_payable - budget_year.accounts_payable,
                'diff_rate': ((actual_year.accounts_payable - budget_year.accounts_payable) / budget_year.accounts_payable * 100) if budget_year.accounts_payable != 0 else 0,
            }
            
            bs_indicators['short_term_loans_payable'] = {
                'budget': budget_year.short_term_loans_payable,
                'actual': actual_year.short_term_loans_payable,
                'diff': actual_year.short_term_loans_payable - budget_year.short_term_loans_payable,
                'diff_rate': ((actual_year.short_term_loans_payable - budget_year.short_term_loans_payable) / budget_year.short_term_loans_payable * 100) if budget_year.short_term_loans_payable != 0 else 0,
            }
            
            bs_indicators['total_current_liabilities'] = {
                'budget': budget_year.total_current_liabilities,
                'actual': actual_year.total_current_liabilities,
                'diff': actual_year.total_current_liabilities - budget_year.total_current_liabilities,
                'diff_rate': ((actual_year.total_current_liabilities - budget_year.total_current_liabilities) / budget_year.total_current_liabilities * 100) if budget_year.total_current_liabilities != 0 else 0,
            }
            
            bs_indicators['long_term_loans_payable'] = {
                'budget': budget_year.long_term_loans_payable,
                'actual': actual_year.long_term_loans_payable,
                'diff': actual_year.long_term_loans_payable - budget_year.long_term_loans_payable,
                'diff_rate': ((actual_year.long_term_loans_payable - budget_year.long_term_loans_payable) / budget_year.long_term_loans_payable * 100) if budget_year.long_term_loans_payable != 0 else 0,
            }
            
            bs_indicators['total_liabilities'] = {
                'budget': budget_year.total_liabilities,
                'actual': actual_year.total_liabilities,
                'diff': actual_year.total_liabilities - budget_year.total_liabilities,
                'diff_rate': ((actual_year.total_liabilities - budget_year.total_liabilities) / budget_year.total_liabilities * 100) if budget_year.total_liabilities != 0 else 0,
            }
            
            # 純資産の部
            bs_indicators['capital_stock'] = {
                'budget': budget_year.capital_stock,
                'actual': actual_year.capital_stock,
                'diff': actual_year.capital_stock - budget_year.capital_stock,
                'diff_rate': ((actual_year.capital_stock - budget_year.capital_stock) / budget_year.capital_stock * 100) if budget_year.capital_stock != 0 else 0,
            }
            
            bs_indicators['retained_earnings'] = {
                'budget': budget_year.retained_earnings,
                'actual': actual_year.retained_earnings,
                'diff': actual_year.retained_earnings - budget_year.retained_earnings,
                'diff_rate': ((actual_year.retained_earnings - budget_year.retained_earnings) / budget_year.retained_earnings * 100) if budget_year.retained_earnings != 0 else 0,
            }
            
            bs_indicators['total_net_assets'] = {
                'budget': budget_year.total_net_assets,
                'actual': actual_year.total_net_assets,
                'diff': actual_year.total_net_assets - budget_year.total_net_assets,
                'diff_rate': ((actual_year.total_net_assets - budget_year.total_net_assets) / budget_year.total_net_assets * 100) if budget_year.total_net_assets != 0 else 0,
            }
            
            # BSグラフ用データ
            bs_chart_data = {
                'labels': ['現金及び預金', '売上債権', '棚卸資産', '流動資産合計', '固定資産合計', '資産合計', '仕入債務', '短期借入金', '流動負債合計', '長期借入金', '負債合計', '資本金', '利益剰余金', '純資産合計'],
                'budget': [
                    budget_year.cash_and_deposits,
                    budget_year.accounts_receivable,
                    budget_year.inventory,
                    budget_year.total_current_assets,
                    budget_year.total_fixed_assets,
                    budget_year.total_assets,
                    budget_year.accounts_payable,
                    budget_year.short_term_loans_payable,
                    budget_year.total_current_liabilities,
                    budget_year.long_term_loans_payable,
                    budget_year.total_liabilities,
                    budget_year.capital_stock,
                    budget_year.retained_earnings,
                    budget_year.total_net_assets,
                ],
                'actual': [
                    actual_year.cash_and_deposits,
                    actual_year.accounts_receivable,
                    actual_year.inventory,
                    actual_year.total_current_assets,
                    actual_year.total_fixed_assets,
                    actual_year.total_assets,
                    actual_year.accounts_payable,
                    actual_year.short_term_loans_payable,
                    actual_year.total_current_liabilities,
                    actual_year.long_term_loans_payable,
                    actual_year.total_liabilities,
                    actual_year.capital_stock,
                    actual_year.retained_earnings,
                    actual_year.total_net_assets,
                ],
            }
        else:
            chart_data = {
                'labels': [],
                'budget': [],
                'actual': [],
            }
            indicators_chart_data = {
                'labels': [],
                'budget': [],
                'actual': [],
            }
            bs_indicators = {}
            bs_chart_data = {
                'labels': [],
                'budget': [],
                'actual': [],
            }
        
        # グラフデータをJSON形式に変換
        import json
        chart_data_json = json.dumps(chart_data)
        indicators_chart_data_json = json.dumps(indicators_chart_data)
        bs_chart_data_json = json.dumps(bs_chart_data)
        
        context.update({
            'title': '年次予算vs実績比較',
            'year': year,
            'budget_year': budget_year,
            'actual_year': actual_year,
            'financial_indicators': financial_indicators,
            'bs_indicators': bs_indicators,
            'chart_data': chart_data,
            'chart_data_json': chart_data_json,
            'indicators_chart_data': indicators_chart_data,
            'indicators_chart_data_json': indicators_chart_data_json,
            'bs_chart_data': bs_chart_data,
            'bs_chart_data_json': bs_chart_data_json,
            'available_years': available_years_list,
        })
        
        return context


class BudgetVsActualMonthlyComparisonView(SelectedCompanyMixin, TemplateView):
    """月次予算と実績の推移比較ビュー"""
    template_name = 'scoreai/budget_vs_actual_monthly.html'

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        company = self.this_company
        
        # 利用可能な年度を取得（予算または実績データが存在する年度）
        available_years_list = list(FiscalSummary_Year.objects.filter(
            company=company
        ).values_list('year', flat=True).distinct().order_by('-year'))
        
        # デフォルト年度を取得（データが存在する最新年度、または現在年度）
        default_year = None
        if available_years_list:
            default_year = available_years_list[0]
        else:
            default_year = timezone.now().year
        
        # 年度を取得（デフォルトはデータが存在する最新年度）
        # URLパラメータから年度を取得、なければデフォルト年度を使用
        year_param = self.request.GET.get('year')
        if year_param:
            try:
                year = int(year_param)
            except ValueError:
                year = default_year
        else:
            year = default_year
        
        # 月次データから直接取得（FiscalSummary_Yearに依存しない）
        # 指定年度の予算月次データを取得
        budget_monthly_all = FiscalSummary_Month.objects.filter(
            fiscal_summary_year__company=company,
            fiscal_summary_year__year=year,
            is_budget=True
        ).select_related('fiscal_summary_year').order_by('period')
        
        # 指定年度の実績月次データを取得
        actual_monthly_all = FiscalSummary_Month.objects.filter(
            fiscal_summary_year__company=company,
            fiscal_summary_year__year=year,
            is_budget=False
        ).select_related('fiscal_summary_year').order_by('period')
        
        # 年度データは取得しない（月次データのみを使用）
        # デバッグログ
        logger.info(f"BudgetVsActualMonthlyComparisonView: year={year}")
        logger.info(f"budget_monthly_all count: {budget_monthly_all.count()}")
        logger.info(f"actual_monthly_all count: {actual_monthly_all.count()}")
        
        # 月次データを取得（12ヶ月分）
        monthly_comparison = []
        chart_data = {
            'labels': [],
            'budget_sales': [],
            'actual_sales': [],
            'budget_operating_profit': [],
            'actual_operating_profit': [],
        }
        
        # 会社の決算月を取得
        fiscal_month = company.fiscal_month  # 1-12の値（1=1月、2=2月、...、12=12月）
        
        # 月次データが存在する場合、12ヶ月分のデータを準備
        if budget_monthly_all.exists() or actual_monthly_all.exists():
            # 予算と実績の月次データを辞書に変換（periodをキーに）
            budget_monthly_dict = {m.period: m for m in budget_monthly_all}
            actual_monthly_dict = {m.period: m for m in actual_monthly_all}
            
            # 決算月を考慮した月度順序を計算
            # 決算月の次の月から始まる（例：決算月が5月の場合、6月から始まる）
            # periodは1-12の値で、決算月の次の月が1、その次が2、...、決算月が12となる
            def get_display_month(period):
                """period（1-12）を決算月を考慮した表示月に変換"""
                # periodは決算月の次の月を1として始まる
                # 例：決算月が5月の場合、period=1は6月、period=2は7月、...、period=12は5月
                display_month = (fiscal_month + period) % 12
                if display_month == 0:
                    display_month = 12
                return display_month
            
            # 12ヶ月分のデータを準備（決算月の次の月から順に）
            for period in range(1, 13):
                budget_month = budget_monthly_dict.get(period)
                actual_month = actual_monthly_dict.get(period)
                
                # デバッグログ
                if period == 1:
                    logger.info(f"Period {period}: budget_month={budget_month}, actual_month={actual_month}")
                
                if budget_month and actual_month:
                    # 両方のデータがある場合：実績vs予算を表示
                    display_month = get_display_month(period)
                    sales_diff = float(actual_month.sales) - float(budget_month.sales)
                    sales_achievement_rate = (float(actual_month.sales) / float(budget_month.sales) * 100) if float(budget_month.sales) > 0 else 0
                    
                    operating_profit_diff = float(actual_month.operating_profit) - float(budget_month.operating_profit)
                    operating_profit_achievement_rate = (float(actual_month.operating_profit) / float(budget_month.operating_profit) * 100) if float(budget_month.operating_profit) != 0 else 0
                    
                    monthly_comparison.append({
                        'period': period,
                        'display_month': display_month,  # 表示用の月（決算月を考慮）
                        'budget_sales': budget_month.sales,
                        'actual_sales': actual_month.sales,
                        'sales_diff': sales_diff,
                        'sales_achievement_rate': sales_achievement_rate,
                        'budget_operating_profit': budget_month.operating_profit,
                        'actual_operating_profit': actual_month.operating_profit,
                        'operating_profit_diff': operating_profit_diff,
                        'operating_profit_achievement_rate': operating_profit_achievement_rate,
                        'budget_gross_profit': budget_month.gross_profit,
                        'actual_gross_profit': actual_month.gross_profit,
                        'gross_profit_diff': float(actual_month.gross_profit) - float(budget_month.gross_profit),
                        'budget_ordinary_profit': budget_month.ordinary_profit,
                        'actual_ordinary_profit': actual_month.ordinary_profit,
                        'ordinary_profit_diff': float(actual_month.ordinary_profit) - float(budget_month.ordinary_profit),
                        'has_actual': True,  # 実績データがあることを示すフラグ
                    })
                    
                    # グラフ用データ
                    chart_data['labels'].append(f'{display_month}月')
                    chart_data['budget_sales'].append(float(budget_month.sales))
                    chart_data['actual_sales'].append(float(actual_month.sales))
                    chart_data['budget_operating_profit'].append(float(budget_month.operating_profit))
                    chart_data['actual_operating_profit'].append(float(actual_month.operating_profit))
                elif budget_month:
                    # 予算のみの場合：予算のみを表示
                    display_month = get_display_month(period)
                    monthly_comparison.append({
                        'period': period,
                        'display_month': display_month,  # 表示用の月（決算月を考慮）
                        'budget_sales': budget_month.sales,
                        'actual_sales': None,  # 実績データなし
                        'sales_diff': None,
                        'sales_achievement_rate': None,
                        'budget_operating_profit': budget_month.operating_profit,
                        'actual_operating_profit': None,
                        'operating_profit_diff': None,
                        'operating_profit_achievement_rate': None,
                        'budget_gross_profit': budget_month.gross_profit,
                        'actual_gross_profit': None,
                        'gross_profit_diff': None,
                        'budget_ordinary_profit': budget_month.ordinary_profit,
                        'actual_ordinary_profit': None,
                        'ordinary_profit_diff': None,
                        'has_actual': False,  # 実績データがないことを示すフラグ
                    })
                    
                    # グラフ用データ（予算のみ）
                    chart_data['labels'].append(f'{display_month}月')
                    chart_data['budget_sales'].append(float(budget_month.sales))
                    chart_data['actual_sales'].append(None)  # 実績データなし
                    chart_data['budget_operating_profit'].append(float(budget_month.operating_profit))
                    chart_data['actual_operating_profit'].append(None)  # 実績データなし
                elif actual_month:
                    # 実績のみの場合（通常は発生しないが、念のため）
                    display_month = get_display_month(period)
                    monthly_comparison.append({
                        'period': period,
                        'display_month': display_month,  # 表示用の月（決算月を考慮）
                        'budget_sales': None,
                        'actual_sales': actual_month.sales,
                        'sales_diff': None,
                        'sales_achievement_rate': None,
                        'budget_operating_profit': None,
                        'actual_operating_profit': actual_month.operating_profit,
                        'operating_profit_diff': None,
                        'operating_profit_achievement_rate': None,
                        'budget_gross_profit': None,
                        'actual_gross_profit': actual_month.gross_profit,
                        'gross_profit_diff': None,
                        'budget_ordinary_profit': None,
                        'actual_ordinary_profit': actual_month.ordinary_profit,
                        'ordinary_profit_diff': None,
                        'has_actual': True,
                    })
                    
                    chart_data['labels'].append(f'{display_month}月')
                    chart_data['budget_sales'].append(None)
                    chart_data['actual_sales'].append(float(actual_month.sales))
                    chart_data['budget_operating_profit'].append(None)
                    chart_data['actual_operating_profit'].append(float(actual_month.operating_profit))
        
        # 月次データから合計を計算（年度データがない場合に備えて）
        total_budget_sales = sum(float(m['budget_sales']) for m in monthly_comparison if m.get('budget_sales') is not None)
        total_actual_sales = sum(float(m['actual_sales']) for m in monthly_comparison if m.get('actual_sales') is not None)
        total_budget_operating_profit = sum(float(m['budget_operating_profit']) for m in monthly_comparison if m.get('budget_operating_profit') is not None)
        total_actual_operating_profit = sum(float(m['actual_operating_profit']) for m in monthly_comparison if m.get('actual_operating_profit') is not None)
        
        # グラフデータをJSON形式に変換
        import json
        chart_data_json = json.dumps(chart_data)
        
        # デバッグログ
        logger.info(f"BudgetVsActualMonthlyComparisonView: year={year}, monthly_comparison_count={len(monthly_comparison)}")
        
        context.update({
            'title': '月次予算vs実績推移表',
            'year': year,
            'monthly_comparison': monthly_comparison,
            'chart_data': chart_data,
            'chart_data_json': chart_data_json,
            'available_years': available_years_list,
            # 月次データから計算した合計
            'total_budget_sales': total_budget_sales,
            'total_actual_sales': total_actual_sales,
            'total_budget_operating_profit': total_budget_operating_profit,
            'total_actual_operating_profit': total_actual_operating_profit,
        })
        
        return context


class BudgetSuggestForm(forms.Form):
    """予算サジェストフォーム"""
    target_year = forms.IntegerField(
        label='対象年度',
        min_value=2000,
        max_value=2100,
        help_text='予算を作成する年度を選択してください'
    )
    sales_growth_rate = forms.DecimalField(
        label='対前期売上高成長率（%）',
        max_digits=10,
        decimal_places=2,
        initial=0.0,
        help_text='前期比の売上高成長率を入力してください（例: 10.5）'
    )
    investment_amount = forms.IntegerField(
        label='今期投資予定額（千円）',
        min_value=0,
        initial=0,
        required=False,
        help_text='設備投資などの予定額を入力してください'
    )
    borrowing_amount = forms.IntegerField(
        label='今期借入予定額（千円）',
        min_value=0,
        initial=0,
        required=False,
        help_text='新規借入の予定額を入力してください'
    )
    capital_increase = forms.IntegerField(
        label='今期資本金増加予定額（千円）',
        min_value=0,
        initial=0,
        required=False,
        help_text='資本金の増加予定額を入力してください'
    )


class BudgetSuggestView(SelectedCompanyMixin, TransactionMixin, FormView):
    """予算サジェストビュー（AI生成）"""
    template_name = 'scoreai/budget_suggest.html'
    form_class = BudgetSuggestForm
    success_url = reverse_lazy('fiscal_summary_year_list')

    def get_initial(self):
        initial = super().get_initial()
        # 最新年度+1をデフォルトに設定
        max_year = FiscalSummary_Year.objects.filter(
            company=self.this_company,
            is_budget=False,
            is_draft=False
        ).aggregate(Max('year'))['year__max']
        if max_year is not None:
            initial['target_year'] = max_year + 1
        else:
            initial['target_year'] = timezone.now().year + 1
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '予算サジェスト（AI生成）'
        
        # 前期実績を取得
        company = self.this_company
        latest_actual = FiscalSummary_Year.objects.filter(
            company=company,
            is_budget=False,
            is_draft=False
        ).order_by('-year').first()
        
        context['latest_actual'] = latest_actual
        return context

    def form_valid(self, form):
        """フォームバリデーション成功時の処理"""
        company = self.this_company
        target_year = form.cleaned_data['target_year']
        sales_growth_rate = form.cleaned_data['sales_growth_rate']
        investment_amount = form.cleaned_data.get('investment_amount', 0)
        borrowing_amount = form.cleaned_data.get('borrowing_amount', 0)
        capital_increase = form.cleaned_data.get('capital_increase', 0)
        
        # 前期実績を取得
        previous_year = target_year - 1
        previous_actual = FiscalSummary_Year.objects.filter(
            company=company,
            year=previous_year,
            is_budget=False,
            is_draft=False
        ).first()
        
        if not previous_actual:
            messages.error(
                self.request,
                f'{previous_year}年の実績データが見つかりません。先に実績データを登録してください。'
            )
            return self.form_invalid(form)
        
        try:
            # AIを使用して予算を生成
            budget_data = self._generate_budget_with_ai(
                previous_actual,
                target_year,
                sales_growth_rate,
                investment_amount,
                borrowing_amount,
                capital_increase
            )
            
            # 予算データを作成
            budget_year, created = FiscalSummary_Year.objects.update_or_create(
                company=company,
                year=target_year,
                is_budget=True,
                defaults=budget_data
            )
            
            if created:
                messages.success(
                    self.request,
                    f'{target_year}年の予算がAIによって生成されました。必要に応じて修正してください。'
                )
            else:
                messages.success(
                    self.request,
                    f'{target_year}年の予算が更新されました。'
                )
            
            return redirect('fiscal_summary_year_update', pk=budget_year.pk)
            
        except Exception as e:
            logger.error(f"Budget generation error: {e}", exc_info=True)
            messages.error(
                self.request,
                f'予算の生成中にエラーが発生しました: {str(e)}'
            )
            return self.form_invalid(form)

    def _generate_budget_with_ai(self, previous_actual, target_year, sales_growth_rate, 
                                 investment_amount, borrowing_amount, capital_increase,
                                 user_script=None):
        """AIを使用して予算を生成"""
        from ..utils.budget_ai import generate_budget_with_ai
        
        # AIを使用して予算を生成
        budget_data = generate_budget_with_ai(
            company=self.this_company,
            target_year=target_year,
            sales_growth_rate=sales_growth_rate,
            investment_amount=investment_amount,
            borrowing_amount=borrowing_amount,
            capital_increase=capital_increase,
            previous_actual=previous_actual,
            user_script=user_script
        )
        
        # その他のフィールドは前期実績をコピー（AIが生成しなかった場合）
        if 'land' not in budget_data:
            budget_data['land'] = previous_actual.land
        if 'buildings' not in budget_data:
            budget_data['buildings'] = previous_actual.buildings
        if 'machinery_equipment' not in budget_data:
            budget_data['machinery_equipment'] = previous_actual.machinery_equipment
        if 'vehicles' not in budget_data:
            budget_data['vehicles'] = previous_actual.vehicles
        if 'accumulated_depreciation' not in budget_data:
            budget_data['accumulated_depreciation'] = previous_actual.accumulated_depreciation
        if 'accounts_payable' not in budget_data:
            budget_data['accounts_payable'] = previous_actual.accounts_payable
        if 'total_current_liabilities' not in budget_data:
            budget_data['total_current_liabilities'] = previous_actual.total_current_liabilities
        if 'number_of_employees_EOY' not in budget_data:
            budget_data['number_of_employees_EOY'] = previous_actual.number_of_employees_EOY
        if 'issued_shares_EOY' not in budget_data:
            budget_data['issued_shares_EOY'] = previous_actual.issued_shares_EOY
        
        return budget_data


class BudgetSuggest_MonthForm(forms.Form):
    """月次予算作成フォーム"""
    budget_year = forms.ModelChoiceField(
        queryset=FiscalSummary_Year.objects.none(),
        label='年次予算',
        help_text='月次予算を作成する年次予算を選択してください'
    )
    method = forms.ChoiceField(
        label='作成方法',
        choices=[
            ('equal', '1. 単純に12分割する'),
            ('previous_ratio', '2. 前年の実績をもとに、各月の売り上げなどを算出'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        help_text='月次予算の作成方法を選択してください'
    )
    override_flag = forms.BooleanField(
        label='既存データを上書きする',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='既に月次予算データが存在する場合、上書きします'
    )

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['budget_year'].queryset = FiscalSummary_Year.objects.filter(
                company=company,
                is_budget=True
            ).order_by('-year')


class BudgetSuggest_MonthView(SelectedCompanyMixin, TransactionMixin, FormView):
    """年次予算から月次予算を作成するビュー"""
    template_name = 'scoreai/budget_suggest_month.html'
    form_class = BudgetSuggest_MonthForm
    success_url = reverse_lazy('fiscal_summary_month_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['budget_year'].queryset = FiscalSummary_Year.objects.filter(
            company=self.this_company,
            is_budget=True
        ).order_by('-year')
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '月次予算作成（年次予算から）'
        context['show_title_card'] = False
        
        # 前年の実績データを取得（方法2で使用）
        budget_years = FiscalSummary_Year.objects.filter(
            company=self.this_company,
            is_budget=True
        ).order_by('-year')
        
        if budget_years.exists():
            latest_budget = budget_years.first()
            previous_year = latest_budget.year - 1
            previous_actual = FiscalSummary_Year.objects.filter(
                company=self.this_company,
                year=previous_year,
                is_budget=False,
                is_draft=False
            ).first()
            context['previous_actual'] = previous_actual
            context['previous_year'] = previous_year
            
            # 前年の月次実績データを取得
            if previous_actual:
                previous_monthly = FiscalSummary_Month.objects.filter(
                    fiscal_summary_year=previous_actual,
                    is_budget=False
                ).order_by('period')
                context['previous_monthly'] = previous_monthly
        
        return context

    def form_valid(self, form):
        """フォームバリデーション成功時の処理"""
        company = self.this_company
        budget_year = form.cleaned_data['budget_year']
        method = form.cleaned_data['method']
        override_flag = form.cleaned_data.get('override_flag', False)
        
        # 既存データのチェック
        existing_budget = FiscalSummary_Month.objects.filter(
            fiscal_summary_year=budget_year,
            is_budget=True
        ).exists()
        
        if existing_budget and not override_flag:
            messages.error(
                self.request,
                f'{budget_year.year}年の月次予算データが既に存在します。「既存データを上書きする」にチェックを入れて再度実行してください。'
            )
            return self.form_invalid(form)
        
        try:
            if method == 'equal':
                # 方法1: 単純に12分割
                monthly_data = self._create_monthly_budget_equal(budget_year)
            else:
                # 方法2: 前年の実績の割合を基に算出
                previous_year = budget_year.year - 1
                previous_actual = FiscalSummary_Year.objects.filter(
                    company=company,
                    year=previous_year,
                    is_budget=False,
                    is_draft=False
                ).first()
                
                if not previous_actual:
                    messages.error(
                        self.request,
                        f'{previous_year}年の実績データが見つかりません。先に実績データを登録してください。'
                    )
                    return self.form_invalid(form)
                
                previous_monthly = FiscalSummary_Month.objects.filter(
                    fiscal_summary_year=previous_actual,
                    is_budget=False
                ).order_by('period')
                
                if not previous_monthly.exists():
                    messages.error(
                        self.request,
                        f'{previous_year}年の月次実績データが見つかりません。先に月次実績データを登録してください。'
                    )
                    return self.form_invalid(form)
                
                monthly_data = self._create_monthly_budget_from_previous_ratio(
                    budget_year, previous_monthly
                )
            
            # 上書きフラグがTrueの場合、既存の月次予算を削除
            if override_flag:
                deleted_count, _ = FiscalSummary_Month.objects.filter(
                    fiscal_summary_year=budget_year,
                    is_budget=True
                ).delete()
                logger.info(f"Deleted {deleted_count} existing monthly budget records for year {budget_year.year}")
            
            # 月次予算データを作成
            # 上書きフラグがFalseの場合、既存データをチェックしてスキップ
            created_count = 0
            updated_count = 0
            skipped_count = 0
            
            for period, data in monthly_data.items():
                # 既存データをチェック（is_budgetに関わらず、同じ年度・月度のデータをチェック）
                # unique_togetherが('fiscal_summary_year', 'period')なので、is_budgetに関わらず1つしか存在できない
                existing = FiscalSummary_Month.objects.filter(
                    fiscal_summary_year=budget_year,
                    period=period
                ).first()
                
                if existing:
                    if override_flag:
                        # 上書きフラグがTrueの場合、既存データを更新または削除して再作成
                        if existing.is_budget:
                            # 予算データの場合は更新
                            existing.sales = data['sales']
                            existing.gross_profit = data['gross_profit']
                            existing.operating_profit = data['operating_profit']
                            existing.ordinary_profit = data['ordinary_profit']
                            existing.save()
                            updated_count += 1
                        else:
                            # 実績データの場合は削除して予算データを作成
                            existing.delete()
                            FiscalSummary_Month.objects.create(
                                fiscal_summary_year=budget_year,
                                period=period,
                                is_budget=True,
                                sales=data['sales'],
                                gross_profit=data['gross_profit'],
                                operating_profit=data['operating_profit'],
                                ordinary_profit=data['ordinary_profit'],
                            )
                            created_count += 1
                    else:
                        # 上書きフラグがFalseの場合、スキップ
                        skipped_count += 1
                else:
                    # 新規作成
                    FiscalSummary_Month.objects.create(
                        fiscal_summary_year=budget_year,
                        period=period,
                        is_budget=True,
                        sales=data['sales'],
                        gross_profit=data['gross_profit'],
                        operating_profit=data['operating_profit'],
                        ordinary_profit=data['ordinary_profit'],
                    )
                    created_count += 1
            
            if override_flag:
                messages.success(
                    self.request,
                    f'{budget_year.year}年の月次予算を{created_count + updated_count}ヶ月分作成しました（既存データを上書きしました）。'
                )
            else:
                if skipped_count > 0:
                    messages.warning(
                        self.request,
                        f'{budget_year.year}年の月次予算を{created_count}ヶ月分作成しました。{skipped_count}ヶ月分は既存データのためスキップしました。上書きする場合は「既存データを上書きする」にチェックを入れてください。'
                    )
                else:
                    messages.success(
                        self.request,
                        f'{budget_year.year}年の月次予算を{created_count}ヶ月分作成しました。'
                    )
            
            return redirect('fiscal_summary_month_list')
            
        except Exception as e:
            logger.error(f"Monthly budget creation error: {e}", exc_info=True)
            messages.error(
                self.request,
                f'月次予算の作成中にエラーが発生しました: {str(e)}'
            )
            return self.form_invalid(form)

    def _create_monthly_budget_equal(self, budget_year):
        """方法1: 年次予算を12で分割"""
        from decimal import Decimal, ROUND_DOWN
        
        monthly_data = {}
        
        # 年次予算の値を12で割る（Decimal型に変換、小数点以下2桁で切り捨て）
        # max_digits=12, decimal_places=2 なので、整数部分は10桁まで
        quantize_value = Decimal('0.01')  # 小数点以下2桁
        
        for period in range(1, 13):
            monthly_data[period] = {
                'sales': (Decimal(str(budget_year.sales)) / Decimal('12')).quantize(quantize_value, rounding=ROUND_DOWN),
                'gross_profit': (Decimal(str(budget_year.gross_profit)) / Decimal('12')).quantize(quantize_value, rounding=ROUND_DOWN),
                'operating_profit': (Decimal(str(budget_year.operating_profit)) / Decimal('12')).quantize(quantize_value, rounding=ROUND_DOWN),
                'ordinary_profit': (Decimal(str(budget_year.ordinary_profit)) / Decimal('12')).quantize(quantize_value, rounding=ROUND_DOWN),
            }
        
        return monthly_data

    def _create_monthly_budget_from_previous_ratio(self, budget_year, previous_monthly):
        """方法2: 前年の実績の割合を基に算出"""
        from decimal import Decimal, ROUND_DOWN
        
        monthly_data = {}
        
        # 前年の年次合計を計算
        previous_year_total = {
            'sales': sum(Decimal(str(m.sales)) for m in previous_monthly),
            'gross_profit': sum(Decimal(str(m.gross_profit)) for m in previous_monthly),
            'operating_profit': sum(Decimal(str(m.operating_profit)) for m in previous_monthly),
            'ordinary_profit': sum(Decimal(str(m.ordinary_profit)) for m in previous_monthly),
        }
        
        # 小数点以下2桁で切り捨て
        quantize_value = Decimal('0.01')
        
        # 各月の割合を計算し、年次予算に適用
        for month in previous_monthly:
            period = month.period
            if period > 12:  # 13（決算整理）はスキップ
                continue
            
            # 前年の各月が年次合計に占める割合
            sales_ratio = Decimal(str(month.sales)) / previous_year_total['sales'] if previous_year_total['sales'] > 0 else Decimal('1') / Decimal('12')
            gross_profit_ratio = Decimal(str(month.gross_profit)) / previous_year_total['gross_profit'] if previous_year_total['gross_profit'] > 0 else Decimal('1') / Decimal('12')
            operating_profit_ratio = Decimal(str(month.operating_profit)) / previous_year_total['operating_profit'] if previous_year_total['operating_profit'] > 0 else Decimal('1') / Decimal('12')
            ordinary_profit_ratio = Decimal(str(month.ordinary_profit)) / previous_year_total['ordinary_profit'] if previous_year_total['ordinary_profit'] > 0 else Decimal('1') / Decimal('12')
            
            # 年次予算に割合を適用（Decimal型に変換、小数点以下2桁で切り捨て）
            monthly_data[period] = {
                'sales': (Decimal(str(budget_year.sales)) * sales_ratio).quantize(quantize_value, rounding=ROUND_DOWN),
                'gross_profit': (Decimal(str(budget_year.gross_profit)) * gross_profit_ratio).quantize(quantize_value, rounding=ROUND_DOWN),
                'operating_profit': (Decimal(str(budget_year.operating_profit)) * operating_profit_ratio).quantize(quantize_value, rounding=ROUND_DOWN),
                'ordinary_profit': (Decimal(str(budget_year.ordinary_profit)) * ordinary_profit_ratio).quantize(quantize_value, rounding=ROUND_DOWN),
            }
        
        # 12ヶ月分が作成されていない場合、残りを均等に分配
        if len(monthly_data) < 12:
            created_periods = set(monthly_data.keys())
            missing_periods = [p for p in range(1, 13) if p not in created_periods]
            
            if missing_periods:
                quantize_value = Decimal('0.01')
                # 既存のデータの平均を計算
                if monthly_data:
                    avg_sales = (sum(d['sales'] for d in monthly_data.values()) / len(monthly_data)).quantize(quantize_value, rounding=ROUND_DOWN)
                    avg_gross_profit = (sum(d['gross_profit'] for d in monthly_data.values()) / len(monthly_data)).quantize(quantize_value, rounding=ROUND_DOWN)
                    avg_operating_profit = (sum(d['operating_profit'] for d in monthly_data.values()) / len(monthly_data)).quantize(quantize_value, rounding=ROUND_DOWN)
                    avg_ordinary_profit = (sum(d['ordinary_profit'] for d in monthly_data.values()) / len(monthly_data)).quantize(quantize_value, rounding=ROUND_DOWN)
                else:
                    avg_sales = (Decimal(str(budget_year.sales)) / Decimal('12')).quantize(quantize_value, rounding=ROUND_DOWN)
                    avg_gross_profit = (Decimal(str(budget_year.gross_profit)) / Decimal('12')).quantize(quantize_value, rounding=ROUND_DOWN)
                    avg_operating_profit = (Decimal(str(budget_year.operating_profit)) / Decimal('12')).quantize(quantize_value, rounding=ROUND_DOWN)
                    avg_ordinary_profit = (Decimal(str(budget_year.ordinary_profit)) / Decimal('12')).quantize(quantize_value, rounding=ROUND_DOWN)
                
                for period in missing_periods:
                    monthly_data[period] = {
                        'sales': avg_sales,
                        'gross_profit': avg_gross_profit,
                        'operating_profit': avg_operating_profit,
                        'ordinary_profit': avg_ordinary_profit,
                    }
        
        return monthly_data


class BudgetAnalysisView(SelectedCompanyMixin, TemplateView):
    """予算と実績のAI分析ビュー"""
    template_name = 'scoreai/budget_analysis.html'

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        company = self.this_company
        
        # 年度を取得（デフォルトは最新年度）
        year = int(self.request.GET.get('year', timezone.now().year))
        
        # 予算データを取得
        budget_year = FiscalSummary_Year.objects.filter(
            company=company,
            year=year,
            is_budget=True
        ).first()
        
        # 実績データを取得
        actual_year = FiscalSummary_Year.objects.filter(
            company=company,
            year=year,
            is_budget=False,
            is_draft=False
        ).first()
        
        if not budget_year or not actual_year:
            context['error'] = '予算または実績データが見つかりません。'
            return context
        
        # AI分析を実行
        analysis_result = self._analyze_budget_vs_actual(budget_year, actual_year)
        
        context.update({
            'title': '予算実績AI分析',
            'year': year,
            'budget_year': budget_year,
            'actual_year': actual_year,
            'analysis_result': analysis_result,
            'available_years': FiscalSummary_Year.objects.filter(
                company=company
            ).values_list('year', flat=True).distinct().order_by('-year'),
        })
        
        return context

    def _analyze_budget_vs_actual(self, budget_year, actual_year):
        """予算と実績の差異をAIで分析"""
        # 差異を計算
        sales_diff = actual_year.sales - budget_year.sales
        sales_diff_rate = (sales_diff / budget_year.sales * 100) if budget_year.sales > 0 else 0
        
        operating_profit_diff = actual_year.operating_profit - budget_year.operating_profit
        operating_profit_diff_rate = (operating_profit_diff / budget_year.operating_profit * 100) if budget_year.operating_profit > 0 else 0
        
        ordinary_profit_diff = actual_year.ordinary_profit - budget_year.ordinary_profit
        ordinary_profit_diff_rate = (ordinary_profit_diff / budget_year.ordinary_profit * 100) if budget_year.ordinary_profit > 0 else 0
        
        net_profit_diff = actual_year.net_profit - budget_year.net_profit
        net_profit_diff_rate = (net_profit_diff / budget_year.net_profit * 100) if budget_year.net_profit > 0 else 0
        
        # 分析結果を構築
        analysis = {
            'sales': {
                'budget': budget_year.sales,
                'actual': actual_year.sales,
                'diff': sales_diff,
                'diff_rate': sales_diff_rate,
                'status': 'good' if sales_diff > 0 else 'bad' if sales_diff < 0 else 'neutral',
            },
            'operating_profit': {
                'budget': budget_year.operating_profit,
                'actual': actual_year.operating_profit,
                'diff': operating_profit_diff,
                'diff_rate': operating_profit_diff_rate,
                'status': 'good' if operating_profit_diff > 0 else 'bad' if operating_profit_diff < 0 else 'neutral',
            },
            'ordinary_profit': {
                'budget': budget_year.ordinary_profit,
                'actual': actual_year.ordinary_profit,
                'diff': ordinary_profit_diff,
                'diff_rate': ordinary_profit_diff_rate,
                'status': 'good' if ordinary_profit_diff > 0 else 'bad' if ordinary_profit_diff < 0 else 'neutral',
            },
            'net_profit': {
                'budget': budget_year.net_profit,
                'actual': actual_year.net_profit,
                'diff': net_profit_diff,
                'diff_rate': net_profit_diff_rate,
                'status': 'good' if net_profit_diff > 0 else 'bad' if net_profit_diff < 0 else 'neutral',
            },
        }
        
        # 改善提案を生成（簡易版）
        recommendations = []
        
        if sales_diff < 0:
            recommendations.append({
                'type': 'warning',
                'title': '売上高が予算を下回っています',
                'message': f'売上高が予算より{sales_diff_rate:.2f}%低くなっています。販売戦略の見直しを検討してください。',
            })
        
        if operating_profit_diff < 0:
            recommendations.append({
                'type': 'warning',
                'title': '営業利益が予算を下回っています',
                'message': f'営業利益が予算より{operating_profit_diff_rate:.2f}%低くなっています。コスト管理の見直しを検討してください。',
            })
        
        if sales_diff > 0 and operating_profit_diff < 0:
            recommendations.append({
                'type': 'info',
                'title': '売上は増加しているが利益が減少',
                'message': '売上高は予算を上回っていますが、営業利益は下回っています。利益率の改善が必要です。',
            })
        
        if sales_diff > 0 and operating_profit_diff > 0:
            recommendations.append({
                'type': 'success',
                'title': '良好な業績',
                'message': '売上高と営業利益の両方が予算を上回っています。この調子で継続してください。',
            })
        
        analysis['recommendations'] = recommendations
        
        return analysis

