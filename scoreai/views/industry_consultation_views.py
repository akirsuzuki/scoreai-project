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

from ..models import IndustryClassification, IzakayaPlan
from ..mixins import SelectedCompanyMixin
from ..izakaya_plan_forms import IzakayaPlanForm
from ..services.izakaya_plan_service import IzakayaPlanService


class IndustryConsultationCenterView(SelectedCompanyMixin, LoginRequiredMixin, TemplateView):
    """業界別相談室のトップページ"""
    template_name = 'scoreai/industry_consultation_center.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # IndustryClassificationを取得
        classifications = IndustryClassification.objects.all().order_by('name')
        context['classifications'] = classifications
        context['title'] = '業界別相談室'
        
        # Companyのmanagerかどうかを判定
        context['is_company_manager'] = self.request.user.is_manager
        
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


class IndustryClassificationDetailView(SelectedCompanyMixin, LoginRequiredMixin, TemplateView):
    """業界分類詳細（プラン選択）ページ"""
    template_name = 'scoreai/industry_classification_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        classification_id = kwargs.get('classification_id')
        # IDが文字列の場合は整数に変換
        try:
            if isinstance(classification_id, str):
                classification_id = int(classification_id)
            classification = get_object_or_404(IndustryClassification, id=classification_id)
        except (ValueError, TypeError):
            # codeで検索を試みる
            classification = get_object_or_404(IndustryClassification, code=classification_id)
        
        # この業界分類に紐づくプランが存在するかチェック
        # 現時点ではIzakayaPlanのみ（飲食業界の場合）
        # 飲食業界の判定（コードや名前で判定、必要に応じて調整）
        # 例: コードが"56"で始まる場合や、名前に"飲食"が含まれる場合
        has_izakaya_plan = False
        # 飲食業界の判定（コードや名前で判定、必要に応じて調整）
        # 例: コードが"56"で始まる場合や、名前に"飲食"が含まれる場合
        if (classification.code and classification.code.startswith('56')) or '飲食' in classification.name or '外食' in classification.name:
            # この業界分類に紐づくIzakayaPlanが存在するかチェック（将来的に他のプランも追加可能）
            has_izakaya_plan = True  # 現時点では飲食業界なら常にTrue（将来的にプランの存在チェックに変更可能）
        
        context['classification'] = classification
        context['has_izakaya_plan'] = has_izakaya_plan
        context['title'] = f'{classification.name} - 業界別相談室'
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
    
    def post(self, request, *args, **kwargs):
        """POSTリクエストの処理"""
        form = self.get_form()
        # save_draftまたはcalculateボタンが押された場合、is_draftを設定
        if 'save_draft' in request.POST:
            form.instance.is_draft = True
        elif 'calculate' in request.POST:
            form.instance.is_draft = False
        
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """フォームが無効な場合の処理"""
        from django.contrib import messages
        messages.error(self.request, '入力内容にエラーがあります。各項目を確認してください。')
        return super().form_invalid(form)
    
    @transaction.atomic
    def form_valid(self, form):
        # 選択中のCompanyを自動設定
        form.instance.company = self.this_company
        form.instance.user = self.request.user
        
        # IndustryClassificationを設定
        # URLパラメータから取得、またはCompanyのindustry_classificationを使用
        classification_id = self.kwargs.get('classification_id') or self.request.GET.get('classification_id')
        if classification_id:
            try:
                # IDが文字列の場合は整数に変換
                if isinstance(classification_id, str):
                    classification_id = int(classification_id)
                classification = IndustryClassification.objects.get(id=classification_id)
                form.instance.industry_classification = classification
            except (IndustryClassification.DoesNotExist, ValueError, TypeError):
                pass
        elif self.this_company.industry_classification:
            form.instance.industry_classification = self.this_company.industry_classification
        
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
    
    def post(self, request, *args, **kwargs):
        """POSTリクエストの処理"""
        self.object = self.get_object()
        form = self.get_form()
        # save_draftまたはcalculateボタンが押された場合、is_draftを設定
        if 'save_draft' in request.POST:
            form.instance.is_draft = True
        elif 'calculate' in request.POST:
            form.instance.is_draft = False
        
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """フォームが無効な場合の処理"""
        from django.contrib import messages
        messages.error(self.request, '入力内容にエラーがあります。各項目を確認してください。')
        return super().form_invalid(form)
    
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
        
        # 12ヶ月分の収支データを生成（グラフ用）- 各月の指数を反映
        monthly_revenue_data = []
        monthly_cost_data = []
        monthly_profit_data = []
        cumulative_profit_data = []
        cumulative_profit = Decimal('0')
        
        # 各月の指数を取得（デフォルトは1.0）
        lunch_coefficients = plan.lunch_monthly_coefficients or {}
        dinner_coefficients = plan.dinner_monthly_coefficients or {}
        
        # 夜の営業日数を取得（24時間営業判定用）
        dinner_operating_days_count = len(plan.dinner_operating_days) if plan.dinner_operating_days else 0
        dinner_is_24hours = dinner_operating_days_count == 7
        
        # 基準となる月間売上（指数1.0の場合）
        base_lunch_revenue = float(IzakayaPlanService.calculate_time_slot_revenue(
            plan=plan,
            operating_days=plan.lunch_operating_days or [],
            price_per_customer=Decimal(str(plan.lunch_price_per_customer or 0)),
            customer_count=plan.lunch_customer_count or 0,
            monthly_coefficients={'1': 1.0},  # 基準値として1.0を使用
            is_24hours=False
        ))
        
        base_dinner_revenue = float(IzakayaPlanService.calculate_time_slot_revenue(
            plan=plan,
            operating_days=plan.dinner_operating_days or [],
            price_per_customer=Decimal(str(plan.dinner_price_per_customer or 0)),
            customer_count=plan.dinner_customer_count or 0,
            monthly_coefficients={'1': 1.0},  # 基準値として1.0を使用
            is_24hours=dinner_is_24hours
        ))
        
        base_revenue = base_lunch_revenue + base_dinner_revenue
        base_cost_of_goods_sold = float(plan.monthly_cost_of_goods_sold or 0)
        base_cost = float(plan.monthly_cost or 0)
        
        for month in range(1, 13):
            month_str = str(month)
            # 各月の指数を取得（デフォルトは1.0）
            lunch_coeff = float(lunch_coefficients.get(month_str, 1.0))
            dinner_coeff = float(dinner_coefficients.get(month_str, 1.0))
            
            # 各月の売上を計算（指数を反映）
            month_lunch_revenue = base_lunch_revenue * lunch_coeff
            month_dinner_revenue = base_dinner_revenue * dinner_coeff
            month_revenue = month_lunch_revenue + month_dinner_revenue
            
            # 各月の売上原価を計算（売上に比例）
            if base_revenue > 0:
                month_cost_of_goods_sold = base_cost_of_goods_sold * (month_revenue / base_revenue)
            else:
                month_cost_of_goods_sold = 0
            
            # 経費は固定（月毎指数の影響を受けない）
            month_cost = base_cost
            
            # 各月の利益を計算
            month_profit = month_revenue - month_cost_of_goods_sold - month_cost
            
            cumulative_profit += Decimal(str(month_profit))
            
            monthly_revenue_data.append(month_revenue)
            monthly_cost_data.append(month_cost)
            monthly_profit_data.append(month_profit)
            cumulative_profit_data.append(float(cumulative_profit))
        
        import json
        
        # 計算根拠データを準備
        # 昼の売上計算根拠
        lunch_operating_days_count = len(plan.lunch_operating_days) if plan.lunch_operating_days else 0
        lunch_monthly_operating_days = Decimal(str(lunch_operating_days_count)) * Decimal('4.33') if lunch_operating_days_count > 0 else Decimal('0')
        lunch_avg_coefficient = Decimal(str(sum(plan.lunch_monthly_coefficients.values()) / len(plan.lunch_monthly_coefficients))) if plan.lunch_monthly_coefficients else Decimal('1.0')
        lunch_revenue_calculation = {
            'price_per_customer': float(plan.lunch_price_per_customer or 0),
            'customer_count': plan.lunch_customer_count or 0,
            'operating_days_count': lunch_operating_days_count,
            'monthly_operating_days': float(lunch_monthly_operating_days),
            'avg_coefficient': float(lunch_avg_coefficient),
            'calculated_revenue': float(IzakayaPlanService.calculate_time_slot_revenue(
                plan=plan,
                operating_days=plan.lunch_operating_days or [],
                price_per_customer=Decimal(str(plan.lunch_price_per_customer or 0)),
                customer_count=plan.lunch_customer_count or 0,
                monthly_coefficients=plan.lunch_monthly_coefficients or {},
                is_24hours=False
            ))
        }
        
        # 夜の売上計算根拠
        dinner_operating_days_count = len(plan.dinner_operating_days) if plan.dinner_operating_days else 0
        dinner_is_24hours = dinner_operating_days_count == 7
        dinner_monthly_operating_days = Decimal('30') if dinner_is_24hours else (Decimal(str(dinner_operating_days_count)) * Decimal('4.33') if dinner_operating_days_count > 0 else Decimal('0'))
        dinner_avg_coefficient = Decimal(str(sum(plan.dinner_monthly_coefficients.values()) / len(plan.dinner_monthly_coefficients))) if plan.dinner_monthly_coefficients else Decimal('1.0')
        dinner_revenue_calculation = {
            'price_per_customer': float(plan.dinner_price_per_customer or 0),
            'customer_count': plan.dinner_customer_count or 0,
            'operating_days_count': dinner_operating_days_count,
            'is_24hours': dinner_is_24hours,
            'monthly_operating_days': float(dinner_monthly_operating_days),
            'avg_coefficient': float(dinner_avg_coefficient),
            'calculated_revenue': float(IzakayaPlanService.calculate_time_slot_revenue(
                plan=plan,
                operating_days=plan.dinner_operating_days or [],
                price_per_customer=Decimal(str(plan.dinner_price_per_customer or 0)),
                customer_count=plan.dinner_customer_count or 0,
                monthly_coefficients=plan.dinner_monthly_coefficients or {},
                is_24hours=dinner_is_24hours
            ))
        }
        
        # 原価計算根拠
        cost_of_goods_sold_calculation = {
            'lunch_revenue': lunch_revenue_calculation['calculated_revenue'],
            'lunch_cost_rate': float(plan.lunch_cost_rate or 0),
            'lunch_cost': lunch_revenue_calculation['calculated_revenue'] * (float(plan.lunch_cost_rate or 0) / 100),
            'dinner_revenue': dinner_revenue_calculation['calculated_revenue'],
            'dinner_cost_rate': float(plan.dinner_cost_rate or 0),
            'dinner_cost': dinner_revenue_calculation['calculated_revenue'] * (float(plan.dinner_cost_rate or 0) / 100),
            'total_cost': (lunch_revenue_calculation['calculated_revenue'] * (float(plan.lunch_cost_rate or 0) / 100)) + 
                         (dinner_revenue_calculation['calculated_revenue'] * (float(plan.dinner_cost_rate or 0) / 100))
        }
        
        # 経費計算根拠
        staff_cost = float(plan.number_of_staff or 0) * float(plan.staff_monthly_salary or 0)
        part_time_cost = float(plan.part_time_hours_per_month or 0) * float(plan.part_time_hourly_wage or 0)
        cost_calculation = {
            'rent': float(plan.monthly_rent or 0),
            'staff_count': plan.number_of_staff or 0,
            'staff_salary': float(plan.staff_monthly_salary or 0),
            'staff_cost': staff_cost,
            'part_time_hours': plan.part_time_hours_per_month or 0,
            'part_time_wage': float(plan.part_time_hourly_wage or 0),
            'part_time_cost': part_time_cost,
            'total_labor_cost': staff_cost + part_time_cost,
            'utilities': float(plan.monthly_utilities or 0),
            'supplies': float(plan.monthly_supplies or 0),
            'advertising': float(plan.monthly_advertising or 0),
            'fees': float(plan.monthly_fees or 0),
            'other_expenses': float(plan.monthly_other_expenses or 0),
            'total_cost': float(plan.monthly_cost or 0)
        }
        
        # 原価率と利益率を計算
        monthly_revenue = float(plan.monthly_revenue or 0)
        monthly_cost_of_goods_sold = float(plan.monthly_cost_of_goods_sold or 0)
        monthly_profit = float(plan.monthly_profit or 0)
        
        cost_rate = (monthly_cost_of_goods_sold / monthly_revenue * 100) if monthly_revenue > 0 else 0
        profit_rate = (monthly_profit / monthly_revenue * 100) if monthly_revenue > 0 else 0
        
        context['monthly_revenue_data'] = json.dumps(monthly_revenue_data)
        context['monthly_cost_data'] = json.dumps(monthly_cost_data)
        context['monthly_profit_data'] = json.dumps(monthly_profit_data)
        context['cumulative_profit_data'] = json.dumps(cumulative_profit_data)
        context['lunch_revenue_calculation'] = lunch_revenue_calculation
        context['dinner_revenue_calculation'] = dinner_revenue_calculation
        context['cost_of_goods_sold_calculation'] = cost_of_goods_sold_calculation
        context['cost_calculation'] = cost_calculation
        context['cost_rate'] = cost_rate
        context['profit_rate'] = profit_rate
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
        ).select_related('industry_classification').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '居酒屋出店計画一覧'
        
        # classification_idを取得（最初のプランから、または飲食業界分類を取得）
        queryset = self.get_queryset()
        if queryset.exists():
            first_plan = queryset.first()
            if first_plan.industry_classification:
                context['classification_id'] = first_plan.industry_classification.id
            else:
                # industry_classificationがない場合は、飲食業界分類を取得
                from ..models import IndustryClassification
                food_classification = IndustryClassification.objects.filter(
                    code__startswith='56'
                ).first()
                if food_classification:
                    context['classification_id'] = food_classification.id
        else:
            # プランがない場合も、飲食業界分類を取得
            from ..models import IndustryClassification
            food_classification = IndustryClassification.objects.filter(
                code__startswith='56'
            ).first()
            if food_classification:
                context['classification_id'] = food_classification.id
        
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

