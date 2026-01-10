"""
業界別専門相談室のビュー
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, CreateView, UpdateView, DetailView, ListView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.urls import reverse, reverse_lazy
from decimal import Decimal

from ..models import IndustryCategory, IndustryConsultationType, IzakayaPlan
from ..mixins import SelectedCompanyMixin
from scoreai.izakaya_plan_forms import IzakayaPlanForm
from ..services.izakaya_plan_service import IzakayaPlanService


class IndustryConsultationCenterView(SelectedCompanyMixin, LoginRequiredMixin, TemplateView):
    """業界別相談室のトップページ"""
    template_name = 'scoreai/industry_consultation_center.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categories = IndustryCategory.objects.filter(is_active=True).order_by('order', 'name')
        context['categories'] = categories
        context['title'] = '業界別相談室'
        
        # 選択中のCompanyの相談履歴を取得
        # 居酒屋出店計画の履歴（下書き含む）
        izakaya_plans_queryset = IzakayaPlan.objects.filter(
            company=self.this_company,
            user=self.request.user
        ).order_by('-created_at')
        
        # 最新10件を取得
        recent_plans = list(izakaya_plans_queryset[:10])
        
        # 下書きと確定済みを分けて取得（最新10件の中から）
        draft_plans = [plan for plan in recent_plans if plan.is_draft]
        completed_plans = [plan for plan in recent_plans if not plan.is_draft]
        
        context['recent_plans'] = recent_plans
        context['draft_plans'] = draft_plans
        context['completed_plans'] = completed_plans
        
        return context


class IndustryCategoryDetailView(SelectedCompanyMixin, LoginRequiredMixin, TemplateView):
    """業界カテゴリー詳細（メニュー）ページ"""
    template_name = 'scoreai/industry_category_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category_id = kwargs.get('category_id')
        category = get_object_or_404(IndustryCategory, id=category_id, is_active=True)
        consultation_types = IndustryConsultationType.objects.filter(
            industry_category=category,
            is_active=True
        ).order_by('order', 'name')
        
        context['category'] = category
        context['consultation_types'] = consultation_types
        context['title'] = f'{category.name} - 業界別相談室'
        return context


class IzakayaPlanCreateView(SelectedCompanyMixin, LoginRequiredMixin, CreateView):
    """居酒屋出店計画作成ビュー"""
    model = IzakayaPlan
    form_class = IzakayaPlanForm
    template_name = 'scoreai/izakaya_plan_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '居酒屋出店計画作成'
        return context
    
    @transaction.atomic
    def form_valid(self, form):
        # 選択中のCompanyを自動設定
        form.instance.company = self.this_company
        form.instance.user = self.request.user
        
        # 月毎指数が空の場合はデフォルト値を設定
        if not form.instance.lunch_monthly_coefficients:
            form.instance.lunch_monthly_coefficients = IzakayaPlanService.get_default_monthly_coefficients()
        if not form.instance.dinner_monthly_coefficients:
            form.instance.dinner_monthly_coefficients = IzakayaPlanService.get_default_monthly_coefficients()
        
        response = super().form_valid(form)
        
        # 下書きでない場合は計算を実行
        if not form.instance.is_draft:
            try:
                IzakayaPlanService.calculate_all(form.instance)
                messages.success(self.request, '計画を作成し、計算を完了しました。')
                return redirect('izakaya_plan_preview', pk=self.object.id)
            except Exception as e:
                messages.error(self.request, f'計算中にエラーが発生しました: {str(e)}')
        else:
            messages.info(self.request, '下書きとして保存しました。')
        
        return response
    
    def get_success_url(self):
        from django.urls import reverse
        if self.object.is_draft:
            return reverse('izakaya_plan_update', kwargs={'pk': self.object.id})
        else:
            return reverse('izakaya_plan_preview', kwargs={'pk': self.object.id})


class IzakayaPlanUpdateView(SelectedCompanyMixin, LoginRequiredMixin, UpdateView):
    """居酒屋出店計画更新ビュー"""
    model = IzakayaPlan
    form_class = IzakayaPlanForm
    template_name = 'scoreai/izakaya_plan_form.html'
    context_object_name = 'plan'
    
    def get_queryset(self):
        return IzakayaPlan.objects.filter(
            company=self.this_company,
            user=self.request.user
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '居酒屋出店計画編集'
        return context
    
    @transaction.atomic
    def form_valid(self, form):
        # 月毎指数が空の場合はデフォルト値を設定
        if not form.instance.lunch_monthly_coefficients:
            form.instance.lunch_monthly_coefficients = IzakayaPlanService.get_default_monthly_coefficients()
        if not form.instance.dinner_monthly_coefficients:
            form.instance.dinner_monthly_coefficients = IzakayaPlanService.get_default_monthly_coefficients()
        
        response = super().form_valid(form)
        
        # 下書きでない場合は計算を実行
        if not form.instance.is_draft:
            try:
                IzakayaPlanService.calculate_all(form.instance)
                messages.success(self.request, '計画を更新し、計算を完了しました。')
                return redirect('izakaya_plan_preview', pk=self.object.id)
            except Exception as e:
                messages.error(self.request, f'計算中にエラーが発生しました: {str(e)}')
        else:
            messages.info(self.request, '下書きとして保存しました。')
        
        return response
    
    def get_success_url(self):
        from django.urls import reverse
        if self.object.is_draft:
            return reverse('izakaya_plan_update', kwargs={'plan_id': self.object.id})
        else:
            return reverse('izakaya_plan_preview', kwargs={'pk': self.object.id})


class IzakayaPlanPreviewView(SelectedCompanyMixin, LoginRequiredMixin, DetailView):
    """居酒屋出店計画プレビュービュー"""
    model = IzakayaPlan
    template_name = 'scoreai/izakaya_plan_preview.html'
    context_object_name = 'plan'
    
    def get_queryset(self):
        return IzakayaPlan.objects.filter(company=self.this_company)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan = self.object
        
        # 計算が未実行の場合は実行
        if plan.is_draft or not plan.monthly_revenue:
            try:
                IzakayaPlanService.calculate_all(plan)
                plan.refresh_from_db()
            except Exception as e:
                messages.error(self.request, f'計算中にエラーが発生しました: {str(e)}')
        
        # 12ヶ月分の収支データを生成（グラフ用）
        monthly_revenue_data = []
        monthly_cost_data = []
        monthly_profit_data = []
        cumulative_profit_data = []
        cumulative_profit = Decimal('0')
        
        for month in range(1, 13):
            revenue = float(plan.monthly_revenue or 0)
            cost = float(plan.monthly_cost or 0)
            profit = float(plan.monthly_profit or 0)
            cumulative_profit += Decimal(str(profit))
            
            monthly_revenue_data.append(revenue)
            monthly_cost_data.append(cost)
            monthly_profit_data.append(profit)
            cumulative_profit_data.append(float(cumulative_profit))
        
        import json
        context['monthly_revenue_data'] = json.dumps(monthly_revenue_data)
        context['monthly_cost_data'] = json.dumps(monthly_cost_data)
        context['monthly_profit_data'] = json.dumps(monthly_profit_data)
        context['cumulative_profit_data'] = json.dumps(cumulative_profit_data)
        context['title'] = '居酒屋出店計画 - プレビュー'
        return context


class IzakayaPlanListView(SelectedCompanyMixin, LoginRequiredMixin, ListView):
    """居酒屋出店計画一覧ビュー"""
    model = IzakayaPlan
    template_name = 'scoreai/izakaya_plan_list.html'
    context_object_name = 'plans'
    
    def get_queryset(self):
        return IzakayaPlan.objects.filter(
            company=self.this_company,
            user=self.request.user
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '居酒屋出店計画一覧'
        return context


class IzakayaPlanDeleteView(SelectedCompanyMixin, LoginRequiredMixin, DeleteView):
    """居酒屋出店計画削除ビュー"""
    model = IzakayaPlan
    template_name = 'scoreai/izakaya_plan_confirm_delete.html'
    context_object_name = 'plan'
    success_url = reverse_lazy('izakaya_plan_list')
    
    def get_queryset(self):
        return IzakayaPlan.objects.filter(
            company=self.this_company,
            user=self.request.user
        )
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, '居酒屋出店計画を削除しました。')
        return super().delete(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '居酒屋出店計画削除'
        return context

