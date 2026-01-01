"""
FirmCompanyの利用枠設定ビュー
"""
from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import UpdateView
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy

from ..models import FirmCompany, Firm
from ..forms import FirmCompanyLimitForm
from ..mixins import FirmOwnerMixin, ErrorHandlingMixin


class FirmCompanyLimitUpdateView(FirmOwnerMixin, ErrorHandlingMixin, UpdateView):
    """FirmCompanyの利用枠設定ビュー"""
    model = FirmCompany
    form_class = FirmCompanyLimitForm
    template_name = 'scoreai/firm_company_limit_form.html'
    context_object_name = 'firm_company'
    
    def get_object(self, queryset=None):
        """更新対象のFirmCompanyを取得"""
        firm_id = self.kwargs.get('firm_id')
        company_id = self.kwargs.get('company_id')
        
        firm = get_object_or_404(Firm, id=firm_id)
        firm_company = get_object_or_404(
            FirmCompany,
            firm=firm,
            company_id=company_id,
            active=True
        )
        
        # Firmオーナーであることを確認（FirmOwnerMixinで既に確認済み）
        return firm_company
    
    def get_form_kwargs(self):
        """フォームにfirmを渡す"""
        kwargs = super().get_form_kwargs()
        kwargs['firm'] = self.firm
        return kwargs
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = f'{self.object.company.name} の利用枠設定'
        context['firm'] = self.firm
        context['company'] = self.object.company
        
        # プラン情報を取得
        try:
            subscription = self.firm.subscription
            plan = subscription.plan
            context['subscription'] = subscription
            context['plan'] = plan
            
            # 現在の割り当て合計を取得
            from django.db.models import Sum
            current_api_total = FirmCompany.objects.filter(
                firm=self.firm,
                active=True
            ).exclude(id=self.object.id).aggregate(
                total=Sum('api_limit')
            )['total'] or 0
            
            current_ocr_total = FirmCompany.objects.filter(
                firm=self.firm,
                active=True
            ).exclude(id=self.object.id).aggregate(
                total=Sum('ocr_limit')
            )['total'] or 0
            
            context['current_api_total'] = current_api_total
            context['current_ocr_total'] = current_ocr_total
            context['plan_api_limit'] = subscription.api_limit if subscription.api_limit > 0 else '無制限'
            context['plan_ocr_limit'] = plan.max_ocr_per_month if plan.max_ocr_per_month > 0 else '無制限'
        except Exception:
            pass
        
        return context
    
    def form_valid(self, form):
        """フォームが有効な場合の処理"""
        messages.success(self.request, '利用枠設定を更新しました。')
        return super().form_valid(form)
    
    def get_success_url(self):
        """成功時のリダイレクト先"""
        return reverse_lazy('firm_clientslist')


