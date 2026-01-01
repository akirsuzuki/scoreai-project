"""
アサインされているクライアント一覧ビュー
"""
from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.db.models import Q

from ..models import UserCompany, UserFirm
from ..mixins import ErrorHandlingMixin


class AssignedClientsListView(LoginRequiredMixin, ErrorHandlingMixin, ListView):
    """自分がアサインされているクライアント一覧"""
    template_name = 'scoreai/assigned_clients_list.html'
    context_object_name = 'assigned_clients'
    
    def get_queryset(self):
        """自分がアサインされているクライアントを取得"""
        # 選択中のFirmを取得
        user_firm = UserFirm.objects.filter(
            user=self.request.user,
            is_selected=True,
            active=True
        ).select_related('firm').first()
        
        if not user_firm:
            return UserCompany.objects.none()
        
        # 自分がアサインされているクライアント（as_consultant=True）を取得
        # かつ、そのCompanyが選択中のFirmに属しているもの
        from ..models import FirmCompany
        firm_company_ids = FirmCompany.objects.filter(
            firm=user_firm.firm,
            active=True
        ).values_list('company_id', flat=True)
        
        assigned_clients = UserCompany.objects.filter(
            user=self.request.user,
            as_consultant=True,
            active=True,
            company_id__in=firm_company_ids
        ).select_related('company').order_by('company__name').distinct()
        
        return assigned_clients
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'アサイン一覧'
        
        # 選択中のFirmを取得
        user_firm = UserFirm.objects.filter(
            user=self.request.user,
            is_selected=True,
            active=True
        ).select_related('firm').first()
        context['user_firm'] = user_firm
        
        return context

