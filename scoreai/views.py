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

class DebtsOverviewView(SelectedCompanyMixin, TemplateView):
    """借入概要ビュー"""
    template_name = 'scoreai/debt_overview.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debt_list, debt_list_totals, debt_list_nodisplay, debt_list_rescheduled, debt_list_finished = get_debt_list(self.this_company)
        
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
            'show_title_card': False,
        })
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
        context['title'] = '株主名登録'
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
        context['title'] = '株式発行登録'
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
        
        # Firmのオーナーかどうかを確認（user_firmが存在しない場合もFalseに設定）
        context['is_firm_owner'] = user_firm.is_owner if user_firm else False
        # 既にアサインされているCompanyのIDセット（初期値は空セット）
        context['assigned_company_ids'] = set()
        # プラン制限関連の初期値
        context['can_add_company'] = False
        context['current_company_count'] = 0
        context['max_companies'] = None
        context['is_unlimited'] = False
        
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
            
            # 既にアサインされているCompanyのIDセットを作成（テンプレートで使用）
            assigned_company_ids = set(clients_assigned.values_list('company_id', flat=True))
            context['assigned_company_ids'] = assigned_company_ids
            
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
    from .models import UserFirm, FirmCompany
    
    client = Company.objects.get(id=client_id)
    
    # Firmを取得（Ownerであることを確認）
    user_firm = UserFirm.objects.filter(
        user=request.user,
        is_selected=True,
        is_owner=True,
        active=True
    ).first()
    
    if not user_firm:
        messages.error(request, 'この操作を実行するにはFirmのOwner権限が必要です。')
        return redirect('firm_clientslist')
    
    # 既にFirmに登録されているCompanyかどうかを確認
    firm_company = FirmCompany.objects.filter(
        firm=user_firm.firm,
        company=client,
        active=True
    ).first()
    
    if not firm_company:
        messages.error(request, f'クライアント "{client.name}" はこのFirmに登録されていません。')
        return redirect('firm_clientslist')
    
    # 既に自分にアサインされているか確認
    existing_user_company = UserCompany.objects.filter(
        user=request.user, 
        company=client,
        active=True
    ).first()
    
    if existing_user_company:
        messages.warning(request, f'クライアント "{client.name}" は既にアサインされています。')
    else:
        # 自分にアサイン（as_consultant=True）
        UserCompany.objects.create(
            user=request.user, 
            company=client, 
            as_consultant=True,
            active=True
        )
        
        messages.success(request, f'クライアント "{client.name}" を自分にアサインしました。')
    
    return redirect('firm_clientslist')

@login_required
def remove_client(request, client_id):
    from .models import UserFirm
    from django.contrib import messages
    
    client = Company.objects.get(id=client_id)
    
    # FirmのOwnerであることを確認
    user_firm = UserFirm.objects.filter(
        user=request.user,
        is_selected=True,
        is_owner=True,
        active=True
    ).first()
    
    if not user_firm:
        messages.error(request, 'この操作を実行するにはFirmのOwner権限が必要です。')
        return redirect('firm_clientslist')
    
    # アサイン解除対象のUserCompanyを取得
    user_company = UserCompany.objects.filter(
        user=request.user, 
        company=client,
        active=True
    ).first()
    
    if not user_company:
        messages.error(request, f'クライアント "{client.name}" はアサインされていません。')
        return redirect('firm_clientslist')
    
    # FirmのOwnerが自分自身のアサイン解除をしようとした場合は禁止
    # FirmのOwnerは強制的に全Companyにアサインされているため、自分自身のアサイン解除はできない
    if user_firm.is_owner and user_company.user == request.user:
        messages.error(request, f'FirmのOwnerは、自分自身のアサイン解除はできません。')
        return redirect('firm_clientslist')
    
    # アサイン解除（論理削除）
    user_company.active = False
    user_company.as_consultant = False
    user_company.save()
    
    messages.success(request, f'クライアント "{client.name}" のアサインを解除しました。')
    return redirect('firm_clientslist')


##########################################################################
###                 テキスト情報中心のシンプルなView                         ###
##########################################################################


class AboutView(generic.TemplateView):
    template_name = 'scoreai/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'SCore_AIについて'
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

class ManualListView(generic.TemplateView):
    """マニュアル一覧ページ（準備中）"""
    template_name = 'scoreai/manual_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'マニュアル'
        context['show_title_card'] = False
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
