"""
AIスクリプト管理機能のビュー
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy

from ..models import (
    AIConsultationType,
    AIConsultationScript,
    UserAIConsultationScript,
)
from ..mixins import SelectedCompanyMixin
from ..forms import AIConsultationScriptForm, UserAIConsultationScriptForm


# 管理者用ビュー
class AdminAIScriptListView(UserPassesTestMixin, ListView):
    """管理者用AIスクリプト一覧"""
    model = AIConsultationScript
    template_name = 'scoreai/admin_ai_script_list.html'
    context_object_name = 'scripts'
    
    def test_func(self):
        return self.request.user.is_superuser
    
    def get_queryset(self):
        return AIConsultationScript.objects.select_related(
            'consultation_type', 'created_by'
        ).order_by('consultation_type__order', 'consultation_type__name', 'is_default', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'AIスクリプト管理（システム）'
        context['consultation_types'] = AIConsultationType.objects.filter(is_active=True).order_by('order')
        return context


class AdminAIScriptCreateView(UserPassesTestMixin, CreateView):
    """管理者用AIスクリプト作成"""
    model = AIConsultationScript
    form_class = AIConsultationScriptForm
    template_name = 'scoreai/admin_ai_script_form.html'
    success_url = reverse_lazy('admin_ai_script_list')
    
    def test_func(self):
        return self.request.user.is_superuser
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'スクリプトを作成しました。')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'AIスクリプト作成（システム）'
        return context


class AdminAIScriptUpdateView(UserPassesTestMixin, UpdateView):
    """管理者用AIスクリプト編集"""
    model = AIConsultationScript
    form_class = AIConsultationScriptForm
    template_name = 'scoreai/admin_ai_script_form.html'
    success_url = reverse_lazy('admin_ai_script_list')
    
    def test_func(self):
        return self.request.user.is_superuser
    
    def form_valid(self, form):
        messages.success(self.request, 'スクリプトを更新しました。')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'AIスクリプト編集（システム）'
        return context


class AdminAIScriptDeleteView(UserPassesTestMixin, DeleteView):
    """管理者用AIスクリプト削除"""
    model = AIConsultationScript
    template_name = 'scoreai/admin_ai_script_confirm_delete.html'
    success_url = reverse_lazy('admin_ai_script_list')
    
    def test_func(self):
        return self.request.user.is_superuser
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'スクリプトを削除しました。')
        return super().delete(request, *args, **kwargs)


# ユーザー用ビュー
class UserAIScriptListView(LoginRequiredMixin, ListView):
    """ユーザー用AIスクリプト一覧"""
    model = UserAIConsultationScript
    template_name = 'scoreai/user_ai_script_list.html'
    context_object_name = 'scripts'
    
    def get_queryset(self):
        return UserAIConsultationScript.objects.filter(
            user=self.request.user
        ).select_related('consultation_type').order_by(
            'consultation_type__order', 'consultation_type__name', 'is_default', 'name'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'マイスクリプト'
        context['consultation_types'] = AIConsultationType.objects.filter(is_active=True).order_by('order')
        return context


class UserAIScriptCreateView(LoginRequiredMixin, CreateView):
    """ユーザー用AIスクリプト作成"""
    model = UserAIConsultationScript
    form_class = UserAIConsultationScriptForm
    template_name = 'scoreai/user_ai_script_form.html'
    success_url = reverse_lazy('user_ai_script_list')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'スクリプトを作成しました。')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'マイスクリプト作成'
        return context


class UserAIScriptUpdateView(LoginRequiredMixin, UpdateView):
    """ユーザー用AIスクリプト編集"""
    model = UserAIConsultationScript
    form_class = UserAIConsultationScriptForm
    template_name = 'scoreai/user_ai_script_form.html'
    success_url = reverse_lazy('user_ai_script_list')
    
    def get_queryset(self):
        return UserAIConsultationScript.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, 'スクリプトを更新しました。')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'マイスクリプト編集'
        return context


class UserAIScriptDeleteView(LoginRequiredMixin, DeleteView):
    """ユーザー用AIスクリプト削除"""
    model = UserAIConsultationScript
    template_name = 'scoreai/user_ai_script_confirm_delete.html'
    success_url = reverse_lazy('user_ai_script_list')
    
    def get_queryset(self):
        return UserAIConsultationScript.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'スクリプトを削除しました。')
        return super().delete(request, *args, **kwargs)

