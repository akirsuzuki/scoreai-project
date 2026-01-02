"""
プラン管理機能のビュー
"""
from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, DetailView, TemplateView
from django.views import View
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.conf import settings
import logging
import stripe

from ..models import Firm, FirmPlan, FirmSubscription, FirmUsageTracking, UserFirm
from ..mixins import ErrorHandlingMixin, FirmOwnerMixin

logger = logging.getLogger(__name__)

# Stripe APIキーの設定
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


class PlanListView(FirmOwnerMixin, ListView):
    """プラン一覧ビュー"""
    model = FirmPlan
    template_name = 'scoreai/plan_list.html'
    context_object_name = 'plans'
    
    def get_queryset(self):
        """有効なプランのみを取得"""
        return FirmPlan.objects.filter(is_active=True).order_by('order', 'plan_type')
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'プラン・サブスクリプション'
        context['show_title_card'] = False
        context['firm'] = self.firm
        
        # 現在のサブスクリプションを取得
        try:
            subscription = self.firm.subscription
            context['current_subscription'] = subscription
        except FirmSubscription.DoesNotExist:
            context['current_subscription'] = None
        
        return context


class PlanDetailView(FirmOwnerMixin, DetailView):
    """プラン詳細ビュー"""
    model = FirmPlan
    template_name = 'scoreai/plan_detail.html'
    context_object_name = 'plan'
    slug_field = 'id'
    slug_url_kwarg = 'plan_id'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'プラン・サブスクリプション'
        context['show_title_card'] = False
        context['firm'] = self.firm
        
        # 現在のサブスクリプションを取得
        try:
            subscription = self.firm.subscription
            context['current_subscription'] = subscription
            context['is_current_plan'] = subscription.plan == self.object
            
            # ダウングレード警告をチェック
            if not context['is_current_plan']:
                from ..utils.plan_downgrade import check_downgrade_warning
                needs_warning, exceed_count, exceeding_companies = check_downgrade_warning(
                    self.firm, self.object
                )
                context['downgrade_warning'] = needs_warning
                context['exceed_count'] = exceed_count
                context['exceeding_companies'] = exceeding_companies
            else:
                context['downgrade_warning'] = False
        except FirmSubscription.DoesNotExist:
            context['current_subscription'] = None
            context['is_current_plan'] = False
            context['downgrade_warning'] = False
        
        return context


class SubscriptionManageView(FirmOwnerMixin, TemplateView):
    """サブスクリプション管理ビュー"""
    template_name = 'scoreai/subscription_manage.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'プラン・サブスクリプション'
        context['show_title_card'] = False
        context['firm'] = self.firm
        
        # 現在のサブスクリプションを取得
        try:
            subscription = self.firm.subscription
            context['subscription'] = subscription
            
            # 現在の利用状況を取得
            now = timezone.now()
            usage_tracking = FirmUsageTracking.objects.filter(
                firm=self.firm,
                year=now.year,
                month=now.month
            ).first()
            
            if not usage_tracking:
                # 今月の利用状況が存在しない場合は作成
                usage_tracking = FirmUsageTracking.objects.create(
                    firm=self.firm,
                    subscription=subscription,
                    year=now.year,
                    month=now.month
                )
            
            context['usage_tracking'] = usage_tracking
            
            # 管理しているCompany数を取得
            from ..models import FirmCompany
            company_count = FirmCompany.objects.filter(
                firm=self.firm,
                active=True
            ).count()
            context['company_count'] = company_count
            
        except FirmSubscription.DoesNotExist:
            context['subscription'] = None
            context['usage_tracking'] = None
            context['company_count'] = 0
        
        return context


class SubscriptionCreateView(FirmOwnerMixin, View):
    """サブスクリプション作成ビュー（Stripe Checkout Session作成）"""
    
    @transaction.atomic
    def post(self, request, firm_id, plan_id):
        """サブスクリプション作成"""
        firm = self.firm
        plan = get_object_or_404(FirmPlan, id=plan_id, is_active=True)
        
        # 無料プランの場合は直接サブスクリプションを作成
        if plan.plan_type == 'free':
            return self._create_free_subscription(firm, plan)
        
        # 有料プランの場合はStripe Checkout Sessionを作成
        billing_cycle = request.POST.get('billing_cycle', 'monthly')
        
        if not stripe.api_key:
            messages.error(request, 'Stripeの設定が完了していません。管理者にお問い合わせください。')
            return redirect('plan_list', firm_id=firm_id)
        
        # Stripe Price IDを取得
        if billing_cycle == 'yearly':
            price_id = plan.stripe_price_id_yearly
        else:
            price_id = plan.stripe_price_id_monthly
        
        if not price_id:
            messages.error(request, 'このプランの価格が設定されていません。管理者にお問い合わせください。')
            return redirect('plan_detail', firm_id=firm_id, plan_id=plan_id)
        
        try:
            # Stripe Customerを作成または取得
            customer_id = self._get_or_create_stripe_customer(firm, request.user)
            
            # Stripe Checkout Sessionを作成
            checkout_session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=request.build_absolute_uri(f'/plans/{firm_id}/subscription/success/'),
                cancel_url=request.build_absolute_uri(f'/plans/{firm_id}/subscription/cancel/'),
                metadata={
                    'firm_id': firm.id,
                    'plan_id': plan.id,
                    'billing_cycle': billing_cycle,
                },
            )
            
            return redirect(checkout_session.url)
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error in SubscriptionCreateView: {e}", exc_info=True)
            messages.error(request, f'決済処理中にエラーが発生しました: {str(e)}')
            return redirect('plan_detail', firm_id=firm_id, plan_id=plan_id)
        except Exception as e:
            logger.error(f"Error in SubscriptionCreateView: {e}", exc_info=True)
            messages.error(request, 'サブスクリプション作成中にエラーが発生しました。')
            return redirect('plan_list', firm_id=firm_id)
    
    def _create_free_subscription(self, firm, plan):
        """無料プランのサブスクリプションを作成"""
        try:
            # 既存のサブスクリプションを取得または作成
            subscription, created = FirmSubscription.objects.get_or_create(
                firm=firm,
                defaults={
                    'plan': plan,
                    'status': 'trial',
                    'trial_ends_at': timezone.now() + timezone.timedelta(days=90),  # 3ヶ月
                }
            )
            
            if not created:
                # 既存のサブスクリプションを更新
                subscription.plan = plan
                subscription.status = 'trial'
                subscription.trial_ends_at = timezone.now() + timezone.timedelta(days=90)
                subscription.save()
            
            messages.success(self.request, f'{plan.name}に登録しました。')
            return redirect('subscription_manage', firm_id=firm.id)
            
        except Exception as e:
            logger.error(f"Error creating free subscription: {e}", exc_info=True)
            messages.error(self.request, 'サブスクリプション作成中にエラーが発生しました。')
            return redirect('plan_list', firm_id=firm.id)
    
    def _get_or_create_stripe_customer(self, firm, user):
        """Stripe Customerを取得または作成"""
        try:
            subscription = firm.subscription
            if subscription.stripe_customer_id:
                return subscription.stripe_customer_id
        except FirmSubscription.DoesNotExist:
            pass
        
        # Stripe Customerを作成
        customer = stripe.Customer.create(
            email=user.email,
            name=firm.name,
            metadata={
                'firm_id': firm.id,
                'user_id': user.id,
            },
        )
        
        return customer.id


class SubscriptionSuccessView(FirmOwnerMixin, TemplateView):
    """サブスクリプション作成成功ビュー"""
    template_name = 'scoreai/subscription_success.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'プラン・サブスクリプション'
        context['show_title_card'] = False
        context['firm'] = self.firm
        return context


class SubscriptionCancelView(FirmOwnerMixin, TemplateView):
    """サブスクリプション作成キャンセルビュー"""
    template_name = 'scoreai/subscription_cancel.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'プラン・サブスクリプション'
        context['show_title_card'] = False
        context['firm'] = self.firm
        return context

