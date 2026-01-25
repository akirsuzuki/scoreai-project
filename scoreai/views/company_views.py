"""
会社関連のビュー
"""
from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import DetailView, UpdateView

from django.contrib.auth.mixins import LoginRequiredMixin
from ..mixins import SelectedCompanyMixin
from ..models import Company, UserCompany, IndustrySubClassification
from ..forms import CompanyForm


class CompanyDetailView(LoginRequiredMixin, DetailView):  # SelectedCompanyMixinは不要（会社選択は不要）
    """会社詳細ビュー"""
    model = Company
    template_name = 'scoreai/company_detail.html'
    context_object_name = 'company'
    slug_field = 'id'
    slug_url_kwarg = 'id'
    
    def dispatch(self, request, *args, **kwargs):
        """アクセス権限をチェック（CompanyのメンバーまたはFirmユーザーとしてアサインされている場合）"""
        response = super().dispatch(request, *args, **kwargs)
        
        # Companyオブジェクトを取得
        company = self.get_object()
        
        # ユーザーがこのCompanyのメンバーかどうかを確認
        user_company = UserCompany.objects.filter(
            user=request.user,
            company=company,
            active=True
        ).first()
        
        # メンバーでない場合、Firmユーザー（コンサルタント）としてアサインされているか確認
        if not user_company:
            from ..models import UserFirm, FirmCompany
            
            # 選択中のFirmを取得
            user_firm = UserFirm.objects.filter(
                user=request.user,
                is_selected=True,
                active=True
            ).first()
            
            if user_firm:
                # このCompanyが選択中のFirmに属しているか確認
                firm_company = FirmCompany.objects.filter(
                    firm=user_firm.firm,
                    company=company,
                    active=True
                ).first()
                
                # コンサルタントとしてアサインされているか確認
                consultant_user_company = UserCompany.objects.filter(
                    user=request.user,
                    company=company,
                    as_consultant=True,
                    active=True
                ).first()
                
                if not firm_company or not consultant_user_company:
                    from django.contrib import messages
                    from django.shortcuts import redirect
                    messages.error(request, 'このCompanyへのアクセス権限がありません。')
                    return redirect('index')
        
        return response

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得
        
        Args:
            **kwargs: 追加のキーワード引数
            
        Returns:
            コンテキストデータの辞書
        """
        from ..models import FirmCompany, CompanyUsageTracking, UserFirm
        from django.utils import timezone
        from django.db.models import Sum
        
        context = super().get_context_data(**kwargs)
        context['title'] = '会社詳細'
        context['show_title_card'] = False
        context['user_count'] = self.object.user_count
        context['users'] = UserCompany.objects.filter(
            company=self.object,
            active=True
        ).select_related('user', 'company')
        
        # 現在のユーザーがこのCompanyのOwnerかどうかを判定
        if self.request.user.is_authenticated:
            user_company = UserCompany.objects.filter(
                user=self.request.user,
                company=self.object,
                active=True
            ).first()
            
            context['is_company_owner'] = user_company.is_owner if user_company else False
            # UserCompanyモデルのis_managerフィールドを使用
            context['is_company_manager'] = user_company.is_manager if user_company else False
            
            # is_managerの場合、利用枠情報を取得
            if user_company and user_company.is_manager:
                # このCompanyに関連するFirmCompanyを取得
                firm_companies = FirmCompany.objects.filter(
                    company=self.object,
                    active=True
                ).select_related('firm')
                
                context['firm_companies'] = firm_companies
                
                # 各Firmごとの利用状況を取得
                usage_info = []
                now = timezone.now()
                current_year = now.year
                current_month = now.month
                
                for firm_company in firm_companies:
                    # 現在の月の利用状況を取得
                    usage_tracking = CompanyUsageTracking.objects.filter(
                        company=self.object,
                        firm=firm_company.firm,
                        year=current_year,
                        month=current_month
                    ).first()
                    
                    usage_info.append({
                        'firm_company': firm_company,
                        'firm': firm_company.firm,
                        'api_limit': firm_company.api_limit,
                        'ocr_limit': firm_company.ocr_limit,
                        'allow_firm_api_usage': firm_company.allow_firm_api_usage,
                        'allow_firm_ocr_usage': firm_company.allow_firm_ocr_usage,
                        'api_used': usage_tracking.api_count if usage_tracking else 0,
                        'ocr_used': usage_tracking.ocr_count if usage_tracking else 0,
                        'api_remaining': max(0, firm_company.api_limit - (usage_tracking.api_count if usage_tracking else 0)) if firm_company.api_limit > 0 else None,
                        'ocr_remaining': max(0, firm_company.ocr_limit - (usage_tracking.ocr_count if usage_tracking else 0)) if firm_company.ocr_limit > 0 else None,
                    })
                
                context['usage_info'] = usage_info
        else:
            context['is_company_owner'] = False
        
        return context


class CompanyUpdateView(LoginRequiredMixin, UpdateView):
    """会社情報更新ビュー"""
    model = Company
    form_class = CompanyForm
    template_name = 'scoreai/company_form.html'
    slug_field = 'id'
    slug_url_kwarg = 'id'

    def dispatch(self, request, *args, **kwargs):
        """アクセス権限をチェック（is_manager=True または is_owner=True のユーザーのみ編集可能）"""
        response = super().dispatch(request, *args, **kwargs)
        
        # Companyオブジェクトを取得
        company = self.get_object()
        
        # ユーザーがこのCompanyのマネージャーまたはオーナーかどうかを確認
        from django.db.models import Q
        user_company = UserCompany.objects.filter(
            user=request.user,
            company=company,
            active=True
        ).filter(
            Q(is_manager=True) | Q(is_owner=True)
        ).first()
        
        if not user_company:
            messages.error(request, 'この会社を編集する権限がありません。')
            from django.shortcuts import redirect
            return redirect('company_detail', id=company.id)
        
        return response

    def form_valid(self, form):
        """フォームバリデーション成功時の処理
        
        Args:
            form: バリデーション済みフォーム
            
        Returns:
            レスポンスオブジェクト
        """
        messages.success(self.request, '会社情報が正常に更新されました。')
        return super().form_valid(form)

    def get_success_url(self):
        """成功時のリダイレクト先URLを取得
        
        Returns:
            リダイレクト先のURL
        """
        return reverse_lazy('company_detail', kwargs={'id': self.object.id})

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得
        
        Args:
            **kwargs: 追加のキーワード引数
            
        Returns:
            コンテキストデータの辞書
        """
        context = super().get_context_data(**kwargs)
        context['title'] = '会社情報編集'
        context['show_title_card'] = False
        context['company'] = self.object
        return context


def load_industry_subclassifications(request):
    """業種小分類をAJAXで取得
    
    会社情報編集時に業種分類の親子関係の入力制御を画面上で行うための処理。
    
    Args:
        request: HTTPリクエストオブジェクト
        
    Returns:
        JSONレスポンス（業種小分類のリスト）
    """
    industry_classification_id = request.GET.get('industry_classification')
    subclassifications = IndustrySubClassification.objects.filter(
        industry_classification_id=industry_classification_id
    ).select_related('industry_classification').order_by('name')
    return JsonResponse(list(subclassifications.values('id', 'name')), safe=False)

