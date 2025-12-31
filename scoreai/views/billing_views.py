"""
請求履歴機能のビュー
"""
from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.http import HttpResponse, Http404
from django.contrib import messages
from django.shortcuts import redirect
from django.conf import settings
import stripe
import logging
import requests

from ..models import Firm, FirmSubscription
from ..mixins import ErrorHandlingMixin, FirmOwnerMixin

logger = logging.getLogger(__name__)

# Stripe APIキーの設定
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


class BillingHistoryView(FirmOwnerMixin, TemplateView):
    """請求履歴一覧ビュー"""
    template_name = 'scoreai/billing_history.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = '請求履歴'
        context['firm'] = self.firm
        
        # サブスクリプションを取得
        try:
            subscription = self.firm.subscription
        except FirmSubscription.DoesNotExist:
            context['invoices'] = []
            context['payment_method'] = None
            return context
        
        # Stripeから請求書を取得
        invoices = []
        if subscription.stripe_customer_id:
            try:
                stripe_invoices = stripe.Invoice.list(
                    customer=subscription.stripe_customer_id,
                    limit=50
                )
                
                for invoice in stripe_invoices.data:
                    invoices.append({
                        'id': invoice.id,
                        'number': invoice.number,
                        'amount_due': invoice.amount_due / 100,  # セントから円に変換
                        'amount_paid': invoice.amount_paid / 100,
                        'status': invoice.status,
                        'created': invoice.created,
                        'period_start': invoice.period_start,
                        'period_end': invoice.period_end,
                        'invoice_pdf': invoice.invoice_pdf,
                        'hosted_invoice_url': invoice.hosted_invoice_url,
                    })
            except stripe.error.StripeError as e:
                logger.error(f"Error fetching invoices: {e}")
                messages.error(self.request, '請求履歴の取得に失敗しました。')
        
        context['invoices'] = invoices
        
        # 支払い方法を取得
        payment_method = None
        if subscription.stripe_customer_id:
            try:
                customer = stripe.Customer.retrieve(subscription.stripe_customer_id)
                if customer.invoice_settings.default_payment_method:
                    pm = stripe.PaymentMethod.retrieve(
                        customer.invoice_settings.default_payment_method
                    )
                    payment_method = {
                        'type': pm.type,
                        'card': pm.card if hasattr(pm, 'card') else None,
                    }
            except stripe.error.StripeError as e:
                logger.error(f"Error fetching payment method: {e}")
        
        context['payment_method'] = payment_method
        
        return context


class BillingInvoiceDetailView(FirmOwnerMixin, View):
    """請求書詳細ビュー（PDFダウンロード）"""
    
    def get(self, request, firm_id, invoice_id):
        """請求書PDFをダウンロード"""
        # サブスクリプションを取得
        try:
            subscription = self.firm.subscription
        except FirmSubscription.DoesNotExist:
            raise Http404("Subscription not found")
        
        if not subscription.stripe_customer_id:
            raise Http404("Stripe customer not found")
        
        try:
            # Stripeから請求書を取得
            invoice = stripe.Invoice.retrieve(invoice_id)
            
            # 顧客IDが一致するか確認
            if invoice.customer != subscription.stripe_customer_id:
                raise Http404("Invoice not found")
            
            # PDFをダウンロード
            if invoice.invoice_pdf:
                import requests
                response = requests.get(invoice.invoice_pdf)
                if response.status_code == 200:
                    http_response = HttpResponse(
                        response.content,
                        content_type='application/pdf'
                    )
                    http_response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.number}.pdf"'
                    return http_response
                else:
                    messages.error(request, '請求書のダウンロードに失敗しました。')
                    return redirect('billing_history', firm_id=firm_id)
            else:
                messages.warning(request, '請求書PDFがまだ生成されていません。')
                return redirect('billing_history', firm_id=firm_id)
                
        except stripe.error.StripeError as e:
            logger.error(f"Error fetching invoice: {e}")
            messages.error(request, '請求書の取得に失敗しました。')
            return redirect('billing_history', firm_id=firm_id)


class PaymentMethodUpdateView(FirmOwnerMixin, View):
    """支払い方法更新ビュー"""
    
    def get(self, request, firm_id):
        """支払い方法更新ページを表示"""
        try:
            subscription = self.firm.subscription
        except FirmSubscription.DoesNotExist:
            messages.error(request, 'サブスクリプションが見つかりません。')
            return redirect('subscription_manage', firm_id=firm_id)
        
        if not subscription.stripe_customer_id:
            messages.error(request, 'Stripe顧客情報が見つかりません。')
            return redirect('subscription_manage', firm_id=firm_id)
        
        try:
            # Stripe Checkout Sessionを作成（支払い方法更新用）
            checkout_session = stripe.checkout.Session.create(
                customer=subscription.stripe_customer_id,
                payment_method_types=['card'],
                mode='setup',
                success_url=request.build_absolute_uri(f'/firm/{firm_id}/billing/payment-method/success/'),
                cancel_url=request.build_absolute_uri(f'/firm/{firm_id}/billing/history/'),
                metadata={
                    'firm_id': firm_id,
                    'action': 'update_payment_method',
                },
            )
            
            return redirect(checkout_session.url)
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating checkout session: {e}")
            messages.error(request, '支払い方法の更新に失敗しました。')
            return redirect('billing_history', firm_id=firm_id)


class PaymentMethodSuccessView(FirmOwnerMixin, TemplateView):
    """支払い方法更新成功ビュー"""
    template_name = 'scoreai/payment_method_success.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = '支払い方法更新完了'
        context['firm'] = self.firm
        return context

