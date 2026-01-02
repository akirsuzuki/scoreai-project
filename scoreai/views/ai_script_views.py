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
        context['show_title_card'] = False
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
        context['title'] = 'AIスクリプト管理（システム）'
        context['show_title_card'] = False
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
        context['title'] = 'AIスクリプト管理（システム）'
        context['show_title_card'] = False
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'AIスクリプト管理（システム）'
        context['show_title_card'] = False
        return context


# ユーザー用ビュー
class UserAIScriptListView(SelectedCompanyMixin, ListView):
    """ユーザー用AIスクリプト一覧"""
    model = UserAIConsultationScript
    template_name = 'scoreai/user_ai_script_list.html'
    context_object_name = 'scripts'
    
    def get_queryset(self):
        from ..models import UserCompany
        
        # 選択中のCompanyに紐づくスクリプトのみを表示
        if not self.this_company:
            # 選択中のCompanyがない場合は空のクエリセットを返す
            return UserAIConsultationScript.objects.none()
        
        # 同じCompanyに属するUserのIDを取得
        company_user_ids = UserCompany.objects.filter(
            company=self.this_company,
            active=True
        ).values_list('user_id', flat=True)
        
        # そのCompanyに紐づくスクリプト（自分が作成したものも含む）
        queryset = UserAIConsultationScript.objects.filter(
            company=self.this_company,
            user_id__in=company_user_ids
        )
        
        return queryset.select_related('consultation_type', 'company', 'user').order_by(
            'consultation_type__order', 'consultation_type__name', 'is_default', 'name'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'マイスクリプト'
        context['show_title_card'] = False
        context['consultation_types'] = AIConsultationType.objects.filter(is_active=True).order_by('order')
        context['selected_company'] = self.this_company
        return context


class UserAIScriptCreateView(SelectedCompanyMixin, CreateView):
    """ユーザー用AIスクリプト作成"""
    model = UserAIConsultationScript
    form_class = UserAIConsultationScriptForm
    template_name = 'scoreai/user_ai_script_form.html'
    success_url = reverse_lazy('user_ai_script_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['selected_company'] = self.this_company
        return kwargs
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        # Companyが指定されていない場合は選択中のCompanyを設定
        if not form.instance.company and self.this_company:
            form.instance.company = self.this_company
        messages.success(self.request, 'スクリプトを作成しました。')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'マイスクリプト'
        context['show_title_card'] = False
        context['selected_company'] = self.this_company
        return context


class UserAIScriptUpdateView(SelectedCompanyMixin, UpdateView):
    """ユーザー用AIスクリプト編集"""
    model = UserAIConsultationScript
    form_class = UserAIConsultationScriptForm
    template_name = 'scoreai/user_ai_script_form.html'
    success_url = reverse_lazy('user_ai_script_list')
    
    def get_queryset(self):
        from ..models import UserCompany
        
        # 自分が作成したスクリプト
        my_scripts = UserAIConsultationScript.objects.filter(user=self.request.user)
        
        # 選択中のCompanyに紐づくスクリプト（自分以外のUserが作成したものも含む）
        if self.this_company:
            # 同じCompanyに属するUserのIDを取得
            company_user_ids = UserCompany.objects.filter(
                company=self.this_company,
                active=True
            ).values_list('user_id', flat=True)
            
            # そのCompanyに紐づくスクリプト（自分が作成したものも含む）
            company_scripts = UserAIConsultationScript.objects.filter(
                company=self.this_company,
                user_id__in=company_user_ids
            )
            
            # 両方を結合（重複を排除）
            from django.db.models import Q
            return UserAIConsultationScript.objects.filter(
                Q(id__in=my_scripts.values_list('id', flat=True)) |
                Q(id__in=company_scripts.values_list('id', flat=True))
            ).distinct()
        else:
            return my_scripts
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['selected_company'] = self.this_company
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'スクリプトを更新しました。')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'マイスクリプト'
        context['show_title_card'] = False
        context['selected_company'] = self.this_company
        return context


class UserAIScriptDeleteView(SelectedCompanyMixin, DeleteView):
    """ユーザー用AIスクリプト削除"""
    model = UserAIConsultationScript
    template_name = 'scoreai/user_ai_script_confirm_delete.html'
    success_url = reverse_lazy('user_ai_script_list')
    
    def get_queryset(self):
        # 自分が作成したスクリプトのみ削除可能
        return UserAIConsultationScript.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'スクリプトを削除しました。')
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'マイスクリプト'
        context['show_title_card'] = False
        return context

