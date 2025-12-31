"""
Firm設定管理機能のビュー
"""
from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, UpdateView
from django.contrib import messages
from django.shortcuts import redirect
from django.db import transaction
from django import forms

from ..models import Firm
from ..mixins import ErrorHandlingMixin, FirmOwnerMixin


class FirmSettingsForm(forms.ModelForm):
    """Firm設定フォーム"""
    class Meta:
        model = Firm
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Firm名',
        }


class FirmSettingsView(FirmOwnerMixin, UpdateView):
    """Firm設定管理ビュー"""
    model = Firm
    form_class = FirmSettingsForm
    template_name = 'scoreai/firm_settings.html'
    
    def get_object(self):
        """編集対象のFirmを取得"""
        return self.firm
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Firm設定'
        context['firm'] = self.firm
        return context
    
    def form_valid(self, form):
        """フォームが有効な場合の処理"""
        messages.success(self.request, 'Firm設定を更新しました。')
        return super().form_valid(form)
    
    def get_success_url(self):
        """成功時のリダイレクト先"""
        return self.request.path

