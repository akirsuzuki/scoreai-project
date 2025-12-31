"""
プラン変更履歴機能のビュー
"""
from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.db.models import Q

from ..models import Firm, SubscriptionHistory
from ..mixins import ErrorHandlingMixin, FirmOwnerMixin


class SubscriptionHistoryView(FirmOwnerMixin, ListView):
    """プラン変更履歴一覧ビュー"""
    model = SubscriptionHistory
    template_name = 'scoreai/subscription_history.html'
    context_object_name = 'histories'
    paginate_by = 20
    
    def get_queryset(self):
        """Firmのプラン変更履歴を取得"""
        return SubscriptionHistory.objects.filter(
            firm=self.firm
        ).select_related(
            'old_plan',
            'new_plan',
            'changed_by'
        ).order_by('-changed_at')
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'プラン変更履歴'
        context['firm'] = self.firm
        return context

