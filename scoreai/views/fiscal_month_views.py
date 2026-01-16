import csv
import logging
import json
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
from django.core.exceptions import PermissionDenied, FieldDoesNotExist
from django import forms

from ..models import (
    FiscalSummary_Year,
    FiscalSummary_Month,
    UserCompany,
)
from ..forms import (
    FiscalSummary_MonthForm,
    CsvUploadForm,
    MoneyForwardCsvUploadForm_Month
)
from ..mixins import SelectedCompanyMixin, TransactionMixin
from ..utils.csv_utils import read_csv_with_auto_encoding, validate_csv_structure

logger = logging.getLogger(__name__)

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
