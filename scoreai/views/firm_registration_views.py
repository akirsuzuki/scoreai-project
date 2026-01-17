"""
Firm登録関連のビュー
"""
from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView
from django.utils import timezone

from ..models import Firm, UserFirm, Company, UserCompany, FirmCompany
from ..forms import FirmRegistrationForm, FirmCompanyRegistrationForm
from ..mixins import ErrorHandlingMixin


class FirmRegistrationView(LoginRequiredMixin, ErrorHandlingMixin, CreateView):
    """Firm登録ビュー
    
    ユーザーがFirmを登録する際に使用します。
    最初に登録するユーザーは自動的にOwnerとして設定されます。
    """
    model = Firm
    form_class = FirmRegistrationForm
    template_name = 'scoreai/firm_registration.html'
    success_url = reverse_lazy('firm_registration_success')
    
    def dispatch(self, request, *args, **kwargs):
        """既にFirmに所属している場合は登録を許可しない"""
        # 既にFirmに所属しているか確認
        existing_firm = UserFirm.objects.filter(
            user=request.user,
            active=True
        ).first()
        
        if existing_firm:
            messages.info(request, '既にFirmに所属しています。')
            return redirect('index')
        
        return super().dispatch(request, *args, **kwargs)
    
    @transaction.atomic
    def form_valid(self, form):
        """フォームバリデーション成功時の処理
        
        Firmを作成し、登録ユーザーをOwnerとして自動アサインします。
        """
        # Firmを作成（ownerフィールドに現在のユーザーを設定）
        firm = form.save(commit=False)
        firm.owner = self.request.user
        firm.save()
        
        # UserFirmを作成（Ownerとして）
        UserFirm.objects.create(
            user=self.request.user,
            firm=firm,
            active=True,
            is_selected=True,
            is_owner=True
        )
        
        messages.success(
            self.request,
            f'Firm「{firm.name}」を登録しました。あなたはOwnerとして設定されました。'
        )
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Firm登録'
        context['show_title_card'] = True
        return context


class FirmRegistrationSuccessView(LoginRequiredMixin, TemplateView):
    """Firm登録成功画面"""
    template_name = 'scoreai/firm_registration_success.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Firm登録完了'
        context['show_title_card'] = True
        
        # 登録されたFirmを取得
        user_firm = UserFirm.objects.filter(
            user=self.request.user,
            active=True,
            is_selected=True
        ).first()
        
        if user_firm:
            context['firm'] = user_firm.firm
        
        return context


class FirmCompanyRegistrationView(LoginRequiredMixin, ErrorHandlingMixin, CreateView):
    """Firm配下のCompany登録ビュー
    
    Firmユーザーが顧客企業（Company）を登録する際に使用します。
    登録者は自動的にそのCompanyのOwnerとしてアサインされます。
    """
    model = Company
    form_class = FirmCompanyRegistrationForm
    template_name = 'scoreai/firm_company_registration.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Firmに所属しているか確認"""
        from ..models import UserFirm
        
        user_firm = UserFirm.objects.filter(
            user=request.user,
            active=True,
            is_selected=True
        ).first()
        
        if not user_firm:
            messages.error(request, 'Firmに所属していません。')
            return redirect('index')
        
        self.user_firm = user_firm
        return super().dispatch(request, *args, **kwargs)
    
    @transaction.atomic
    def form_valid(self, form):
        """フォームバリデーション成功時の処理
        
        Companyを作成し、FirmCompanyで紐づけ、登録者をOwnerとして自動アサインします。
        """
        import ulid
        
        # Companyを作成
        company = form.save(commit=False)
        # codeを生成（ULIDベース）
        company.code = ulid.new().str[:20]
        company.save()
        
        # FirmCompanyを作成（FirmとCompanyを紐づけ）
        FirmCompany.objects.create(
            firm=self.user_firm.firm,
            company=company,
            active=True,
            start_date=timezone.now().date()
        )
        
        # UserCompanyを作成（登録者をOwnerとして）
        # is_selected=Trueにより、このCompanyが自動的に選択状態になる
        UserCompany.objects.create(
            user=self.request.user,
            company=company,
            active=True,
            is_selected=True,
            is_owner=True,
            as_consultant=True  # Firmユーザーとして
        )
        
        messages.success(
            self.request,
            f'顧客企業「{company.name}」を登録しました。あなたはOwnerとして設定されました。'
        )
        
        # 成功後のリダイレクト先を設定
        self.success_url = reverse_lazy('company_registration_success', kwargs={'company_id': company.id})
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = '顧客企業登録'
        context['show_title_card'] = True
        context['firm'] = self.user_firm.firm
        return context


class CompanyRegistrationSuccessView(LoginRequiredMixin, TemplateView):
    """Company登録成功画面
    
    登録後の次のステップ（決算数字や借入の登録）への導線を提供します。
    """
    template_name = 'scoreai/company_registration_success.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Companyの存在確認とアクセス権限チェック"""
        company_id = kwargs.get('company_id')
        
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            messages.error(request, '指定された会社が見つかりません。')
            return redirect('index')
        
        # ユーザーがこのCompanyのOwnerか確認
        user_company = UserCompany.objects.filter(
            user=request.user,
            company=company,
            active=True,
            is_owner=True
        ).first()
        
        if not user_company:
            messages.error(request, 'この会社へのアクセス権限がありません。')
            return redirect('index')
        
        self.company = company
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = '顧客企業登録完了'
        context['show_title_card'] = True
        context['company'] = self.company
        
        # 次のステップへのリンクを提供
        context['next_steps'] = [
            {
                'title': '決算数字を登録',
                'description': '年度別の決算数字を登録します',
                'url': reverse_lazy('fiscal_summary_year_create'),
                'icon': 'ti ti-chart-line',
                'button_text': '登録する'
            },
            {
                'title': '借入情報を登録',
                'description': '借入金の情報を登録します',
                'url': reverse_lazy('debt_create'),
                'icon': 'ti ti-building-bank',
                'button_text': '登録する'
            },
            {
                'title': 'ダッシュボードを確認',
                'description': '登録した情報をダッシュボードで確認します',
                'url': reverse_lazy('index'),
                'icon': 'ti ti-dashboard',
                'button_text': '確認する'
            },
        ]
        
        return context
