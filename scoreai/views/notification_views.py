"""
通知機能のビュー
"""
from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, View
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from django.http import JsonResponse

from ..models import Firm, FirmNotification
from ..mixins import ErrorHandlingMixin, FirmOwnerMixin


class NotificationListView(FirmOwnerMixin, ListView):
    """通知一覧ビュー"""
    model = FirmNotification
    template_name = 'scoreai/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        """Firmの通知を取得"""
        return FirmNotification.objects.filter(
            firm=self.firm
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = '通知一覧'
        context['firm'] = self.firm
        
        # 未読通知数
        context['unread_count'] = FirmNotification.objects.filter(
            firm=self.firm,
            is_read=False
        ).count()
        
        return context


class NotificationDetailView(FirmOwnerMixin, DetailView):
    """通知詳細ビュー"""
    model = FirmNotification
    template_name = 'scoreai/notification_detail.html'
    context_object_name = 'notification'
    
    def get_queryset(self):
        """Firmの通知のみを取得"""
        return FirmNotification.objects.filter(firm=self.firm)
    
    def get_object(self, queryset=None):
        """通知を取得し、既読にする"""
        notification = super().get_object(queryset)
        
        # 未読の場合は既読にする
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()
        
        return notification
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = self.object.title
        context['firm'] = self.firm
        return context


class NotificationMarkReadView(FirmOwnerMixin, View):
    """通知を既読にするビュー（AJAX用）"""
    
    def post(self, request, firm_id, notification_id):
        """通知を既読にする"""
        notification = get_object_or_404(
            FirmNotification,
            id=notification_id,
            firm=self.firm
        )
        
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()
        
        return JsonResponse({
            'success': True,
            'message': '通知を既読にしました。'
        })


class NotificationMarkAllReadView(FirmOwnerMixin, View):
    """すべての通知を既読にするビュー"""
    
    def post(self, request, firm_id):
        """すべての未読通知を既読にする"""
        count = FirmNotification.objects.filter(
            firm=self.firm,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        messages.success(request, f'{count}件の通知を既読にしました。')
        return redirect('notification_list', firm_id=firm_id)

