"""
業界別相談室設定管理のビュー（Companyのmanager用）
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.core.exceptions import PermissionDenied

from ..models import IndustryCategory, IndustryConsultationType
from ..mixins import SelectedCompanyMixin


class CompanyManagerMixin(LoginRequiredMixin):
    """Companyのmanagerかどうかをチェックするミックスイン"""
    
    def dispatch(self, request, *args, **kwargs):
        """Companyのmanagerかどうかを確認"""
        # LoginRequiredMixinのチェックを先に実行
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Userのis_managerフラグをチェック
        if not request.user.is_manager:
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, 'この機能はCompanyのmanagerのみが利用できます。')
            return redirect('industry_consultation_center')
        
        return super().dispatch(request, *args, **kwargs)


class IndustryCategoryListView(CompanyManagerMixin, SelectedCompanyMixin, LoginRequiredMixin, ListView):
    """業界カテゴリー一覧ビュー"""
    model = IndustryCategory
    template_name = 'scoreai/industry_category_list.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        return IndustryCategory.objects.all().order_by('order', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '業界カテゴリー管理'
        return context


class IndustryCategoryCreateView(CompanyManagerMixin, SelectedCompanyMixin, LoginRequiredMixin, CreateView):
    """業界カテゴリー作成ビュー"""
    model = IndustryCategory
    template_name = 'scoreai/industry_category_form.html'
    fields = ['name', 'description', 'icon', 'order', 'is_active']
    success_url = reverse_lazy('industry_category_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '業界カテゴリー作成'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, '業界カテゴリーを作成しました。')
        return super().form_valid(form)


class IndustryCategoryUpdateView(CompanyManagerMixin, SelectedCompanyMixin, LoginRequiredMixin, UpdateView):
    """業界カテゴリー更新ビュー"""
    model = IndustryCategory
    template_name = 'scoreai/industry_category_form.html'
    fields = ['name', 'description', 'icon', 'order', 'is_active']
    success_url = reverse_lazy('industry_category_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '業界カテゴリー編集'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, '業界カテゴリーを更新しました。')
        return super().form_valid(form)


class IndustryCategoryDeleteView(CompanyManagerMixin, SelectedCompanyMixin, LoginRequiredMixin, DeleteView):
    """業界カテゴリー削除ビュー"""
    model = IndustryCategory
    template_name = 'scoreai/industry_category_confirm_delete.html'
    success_url = reverse_lazy('industry_category_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '業界カテゴリー削除'
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, '業界カテゴリーを削除しました。')
        return super().delete(request, *args, **kwargs)


class IndustryConsultationTypeListView(CompanyManagerMixin, SelectedCompanyMixin, LoginRequiredMixin, ListView):
    """業界別相談タイプ一覧ビュー"""
    model = IndustryConsultationType
    template_name = 'scoreai/industry_consultation_type_list.html'
    context_object_name = 'consultation_types'
    
    def get_queryset(self):
        return IndustryConsultationType.objects.all().select_related('industry_category').order_by('industry_category__order', 'industry_category__name', 'order', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '業界別相談タイプ管理'
        return context


class IndustryConsultationTypeCreateView(CompanyManagerMixin, SelectedCompanyMixin, LoginRequiredMixin, CreateView):
    """業界別相談タイプ作成ビュー"""
    model = IndustryConsultationType
    template_name = 'scoreai/industry_consultation_type_form.html'
    fields = ['industry_category', 'name', 'description', 'template_type', 'order', 'is_active']
    success_url = reverse_lazy('industry_consultation_type_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '業界別相談タイプ作成'
        # 業界カテゴリーの選択肢を取得
        context['categories'] = IndustryCategory.objects.filter(is_active=True).order_by('order', 'name')
        return context
    
    def form_valid(self, form):
        messages.success(self.request, '業界別相談タイプを作成しました。')
        return super().form_valid(form)


class IndustryConsultationTypeUpdateView(CompanyManagerMixin, SelectedCompanyMixin, LoginRequiredMixin, UpdateView):
    """業界別相談タイプ更新ビュー"""
    model = IndustryConsultationType
    template_name = 'scoreai/industry_consultation_type_form.html'
    fields = ['industry_category', 'name', 'description', 'template_type', 'order', 'is_active']
    success_url = reverse_lazy('industry_consultation_type_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '業界別相談タイプ編集'
        # 業界カテゴリーの選択肢を取得
        context['categories'] = IndustryCategory.objects.filter(is_active=True).order_by('order', 'name')
        return context
    
    def form_valid(self, form):
        messages.success(self.request, '業界別相談タイプを更新しました。')
        return super().form_valid(form)


class IndustryConsultationTypeDeleteView(CompanyManagerMixin, SelectedCompanyMixin, LoginRequiredMixin, DeleteView):
    """業界別相談タイプ削除ビュー"""
    model = IndustryConsultationType
    template_name = 'scoreai/industry_consultation_type_confirm_delete.html'
    success_url = reverse_lazy('industry_consultation_type_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '業界別相談タイプ削除'
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, '業界別相談タイプを削除しました。')
        return super().delete(request, *args, **kwargs)

