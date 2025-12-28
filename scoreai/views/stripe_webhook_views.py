"""
Stripe Webhook処理ビュー
"""
from django.views import View
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.db import transaction
from django.utils import timezone
import stripe
import json
import logging

from ..models import Firm, FirmSubscription, FirmPlan

logger = logging.getLogger(__name__)

# Stripe APIキーの設定
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """Stripe Webhookを処理するビュー"""
    
    def post(self, request):
        """Webhookイベントを処理"""
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
        
        if not webhook_secret:
            logger.error("STRIPE_WEBHOOK_SECRET is not set")
            return HttpResponse(status=400)
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {e}")
            return HttpResponse(status=400)
        
        # イベントタイプに応じて処理
        event_type = event['type']
        event_data = event['data']['object']
        
        try:
            if event_type == 'customer.subscription.created':
                self._handle_subscription_created(event_data)
            elif event_type == 'customer.subscription.updated':
                self._handle_subscription_updated(event_data)
            elif event_type == 'customer.subscription.deleted':
                self._handle_subscription_deleted(event_data)
            elif event_type == 'invoice.payment_succeeded':
                self._handle_invoice_payment_succeeded(event_data)
            elif event_type == 'invoice.payment_failed':
                self._handle_invoice_payment_failed(event_data)
            else:
                logger.info(f"Unhandled event type: {event_type}")
        except Exception as e:
            logger.error(f"Error processing webhook event {event_type}: {e}", exc_info=True)
            return HttpResponse(status=500)
        
        return HttpResponse(status=200)
    
    @transaction.atomic
    def _handle_subscription_created(self, subscription_data):
        """サブスクリプション作成時の処理"""
        stripe_subscription_id = subscription_data['id']
        stripe_customer_id = subscription_data['customer']
        
        # metadataから取得を試みる
        metadata = subscription_data.get('metadata', {})
        firm_id = metadata.get('firm_id')
        plan_id = metadata.get('plan_id')
        
        # metadataにない場合は、Customerのmetadataから取得
        if not firm_id:
            try:
                customer = stripe.Customer.retrieve(stripe_customer_id)
                firm_id = customer.metadata.get('firm_id')
            except Exception as e:
                logger.error(f"Error retrieving customer: {e}")
        
        # plan_idがmetadataにない場合は、price_idからプランを特定
        if not plan_id:
            price_id = subscription_data.get('items', {}).get('data', [{}])[0].get('price', {}).get('id', '')
            if price_id:
                try:
                    plan = FirmPlan.objects.filter(
                        stripe_price_id_monthly=price_id
                    ).first() or FirmPlan.objects.filter(
                        stripe_price_id_yearly=price_id
                    ).first()
                    if plan:
                        plan_id = plan.id
                except Exception as e:
                    logger.error(f"Error finding plan by price_id: {e}")
        
        if not firm_id:
            logger.warning(f"Missing firm_id in subscription {stripe_subscription_id}")
            return
        
        if not plan_id:
            logger.warning(f"Missing plan_id in subscription {stripe_subscription_id}")
            return
        
        try:
            firm = Firm.objects.get(id=firm_id)
            plan = FirmPlan.objects.get(id=plan_id)
        except (Firm.DoesNotExist, FirmPlan.DoesNotExist) as e:
            logger.error(f"Firm or Plan not found: {e}")
            return
        
        # サブスクリプションを作成または更新
        subscription, created = FirmSubscription.objects.get_or_create(
            firm=firm,
            defaults={
                'plan': plan,
                'status': 'active',
                'stripe_customer_id': stripe_customer_id,
                'stripe_subscription_id': stripe_subscription_id,
                'stripe_price_id': subscription_data.get('items', {}).get('data', [{}])[0].get('price', {}).get('id', ''),
                'started_at': timezone.now(),
                'current_period_start': timezone.datetime.fromtimestamp(
                    subscription_data.get('current_period_start', 0),
                    tz=timezone.utc
                ) if subscription_data.get('current_period_start') else None,
                'current_period_end': timezone.datetime.fromtimestamp(
                    subscription_data.get('current_period_end', 0),
                    tz=timezone.utc
                ) if subscription_data.get('current_period_end') else None,
            }
        )
        
        if not created:
            # 既存のサブスクリプションを更新
            subscription.plan = plan
            subscription.status = 'active'
            subscription.stripe_customer_id = stripe_customer_id
            subscription.stripe_subscription_id = stripe_subscription_id
            subscription.stripe_price_id = subscription_data.get('items', {}).get('data', [{}])[0].get('price', {}).get('id', '')
            subscription.current_period_start = timezone.datetime.fromtimestamp(
                subscription_data.get('current_period_start', 0),
                tz=timezone.utc
            ) if subscription_data.get('current_period_start') else None
            subscription.current_period_end = timezone.datetime.fromtimestamp(
                subscription_data.get('current_period_end', 0),
                tz=timezone.utc
            ) if subscription_data.get('current_period_end') else None
            subscription.save()
        
        logger.info(f"Subscription created/updated: {subscription.id} for firm {firm_id}")
    
    @transaction.atomic
    def _handle_subscription_updated(self, subscription_data):
        """サブスクリプション更新時の処理"""
        stripe_subscription_id = subscription_data['id']
        
        try:
            subscription = FirmSubscription.objects.get(
                stripe_subscription_id=stripe_subscription_id
            )
        except FirmSubscription.DoesNotExist:
            logger.warning(f"Subscription not found: {stripe_subscription_id}")
            return
        
        # ステータスを更新
        stripe_status = subscription_data.get('status', '')
        status_mapping = {
            'active': 'active',
            'trialing': 'trial',
            'past_due': 'past_due',
            'canceled': 'canceled',
            'unpaid': 'unpaid',
            'incomplete': 'incomplete',
            'incomplete_expired': 'incomplete_expired',
        }
        subscription.status = status_mapping.get(stripe_status, subscription.status)
        
        # 期間を更新
        if subscription_data.get('current_period_start'):
            subscription.current_period_start = timezone.datetime.fromtimestamp(
                subscription_data['current_period_start'],
                tz=timezone.utc
            )
        if subscription_data.get('current_period_end'):
            subscription.current_period_end = timezone.datetime.fromtimestamp(
                subscription_data['current_period_end'],
                tz=timezone.utc
            )
        
        # キャンセル日時
        if subscription_data.get('canceled_at'):
            subscription.canceled_at = timezone.datetime.fromtimestamp(
                subscription_data['canceled_at'],
                tz=timezone.utc
            )
        
        # 終了日時
        if subscription_data.get('ended_at'):
            subscription.ends_at = timezone.datetime.fromtimestamp(
                subscription_data['ended_at'],
                tz=timezone.utc
            )
        
        subscription.save()
        logger.info(f"Subscription updated: {subscription.id}")
    
    @transaction.atomic
    def _handle_subscription_deleted(self, subscription_data):
        """サブスクリプション削除時の処理"""
        stripe_subscription_id = subscription_data['id']
        
        try:
            subscription = FirmSubscription.objects.get(
                stripe_subscription_id=stripe_subscription_id
            )
        except FirmSubscription.DoesNotExist:
            logger.warning(f"Subscription not found: {stripe_subscription_id}")
            return
        
        subscription.status = 'canceled'
        if subscription_data.get('ended_at'):
            subscription.ends_at = timezone.datetime.fromtimestamp(
                subscription_data['ended_at'],
                tz=timezone.utc
            )
        subscription.canceled_at = timezone.now()
        subscription.save()
        
        logger.info(f"Subscription deleted: {subscription.id}")
    
    @transaction.atomic
    def _handle_invoice_payment_succeeded(self, invoice_data):
        """請求書の支払い成功時の処理"""
        stripe_subscription_id = invoice_data.get('subscription')
        
        if not stripe_subscription_id:
            logger.warning("Invoice has no subscription")
            return
        
        try:
            subscription = FirmSubscription.objects.get(
                stripe_subscription_id=stripe_subscription_id
            )
        except FirmSubscription.DoesNotExist:
            logger.warning(f"Subscription not found: {stripe_subscription_id}")
            return
        
        # サブスクリプションを有効化
        subscription.status = 'active'
        
        # 期間を更新
        if invoice_data.get('period_start'):
            subscription.current_period_start = timezone.datetime.fromtimestamp(
                invoice_data['period_start'],
                tz=timezone.utc
            )
        if invoice_data.get('period_end'):
            subscription.current_period_end = timezone.datetime.fromtimestamp(
                invoice_data['period_end'],
                tz=timezone.utc
            )
        
        subscription.save()
        logger.info(f"Invoice payment succeeded for subscription: {subscription.id}")
    
    @transaction.atomic
    def _handle_invoice_payment_failed(self, invoice_data):
        """請求書の支払い失敗時の処理"""
        stripe_subscription_id = invoice_data.get('subscription')
        
        if not stripe_subscription_id:
            logger.warning("Invoice has no subscription")
            return
        
        try:
            subscription = FirmSubscription.objects.get(
                stripe_subscription_id=stripe_subscription_id
            )
        except FirmSubscription.DoesNotExist:
            logger.warning(f"Subscription not found: {stripe_subscription_id}")
            return
        
        # サブスクリプションを支払い遅延状態に
        subscription.status = 'past_due'
        subscription.save()
        
        logger.info(f"Invoice payment failed for subscription: {subscription.id}")

