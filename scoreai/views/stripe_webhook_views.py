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
        logger.info("=== Webhook endpoint called ===")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request path: {request.path}")
        logger.info(f"Content-Type: {request.content_type}")
        
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
        
        logger.info(f"Webhook secret exists: {bool(webhook_secret)}")
        logger.info(f"Signature header exists: {bool(sig_header)}")
        logger.info(f"Payload length: {len(payload)} bytes")
        
        if not webhook_secret:
            logger.error("STRIPE_WEBHOOK_SECRET is not set")
            return HttpResponse(status=400)
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            logger.info(f"Webhook event constructed successfully. Event ID: {event.get('id', 'unknown')}")
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {e}")
            logger.error(f"Expected secret: {webhook_secret[:10]}...")
            return HttpResponse(status=400)
        
        # イベントタイプに応じて処理
        event_type = event['type']
        event_data = event['data']['object']
        
        logger.info(f"Webhook event received: {event_type} (ID: {event.get('id', 'unknown')})")
        
        try:
            if event_type == 'customer.subscription.created':
                logger.info(f"Processing subscription.created event")
                self._handle_subscription_created(event_data)
            elif event_type == 'customer.subscription.updated':
                logger.info(f"Processing subscription.updated event")
                self._handle_subscription_updated(event_data)
            elif event_type == 'customer.subscription.deleted':
                logger.info(f"Processing subscription.deleted event")
                self._handle_subscription_deleted(event_data)
            elif event_type == 'invoice.payment_succeeded':
                logger.info(f"Processing invoice.payment_succeeded event")
                self._handle_invoice_payment_succeeded(event_data)
            elif event_type == 'invoice.payment_failed':
                logger.info(f"Processing invoice.payment_failed event")
                self._handle_invoice_payment_failed(event_data)
            elif event_type == 'invoice_payment.paid':
                # invoice_payment.paidはinvoice.payment_succeededと同じ処理
                logger.info(f"Processing invoice_payment.paid event (mapped to invoice.payment_succeeded)")
                self._handle_invoice_payment_succeeded(event_data)
            else:
                logger.info(f"Unhandled event type: {event_type}")
        except Exception as e:
            logger.error(f"Error processing webhook event {event_type}: {e}", exc_info=True)
            return HttpResponse(status=500)
        
        logger.info(f"Webhook event processed successfully: {event_type}")
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
        """サブスクリプション更新時の処理（プラン変更含む）"""
        from ..utils.plan_downgrade import handle_plan_downgrade
        
        stripe_subscription_id = subscription_data.get('id')
        logger.info(f"Handling subscription update: {stripe_subscription_id}")
        
        # 既存のサブスクリプションを取得
        subscription = FirmSubscription.objects.filter(
            stripe_subscription_id=stripe_subscription_id
        ).first()
        
        if not subscription:
            logger.warning(f"Subscription not found: {stripe_subscription_id}")
            return
        
        # 古いプランを保存
        old_plan = subscription.plan
        
        # 新しい価格IDを取得
        items = subscription_data.get('items', {}).get('data', [])
        if not items:
            logger.warning("No items in subscription data")
            return
        
        new_price_id = items[0].get('price', {}).get('id')
        if not new_price_id:
            logger.warning("No price ID in subscription data")
            return
        
        logger.info(f"New price ID: {new_price_id}")
        
        # 新しいプランを取得
        new_plan = FirmPlan.objects.filter(
            stripe_price_id_monthly=new_price_id
        ).first()
        
        if not new_plan:
            new_plan = FirmPlan.objects.filter(
                stripe_price_id_yearly=new_price_id
            ).first()
        
        if not new_plan:
            logger.warning(f"Plan not found for price ID: {new_price_id}")
            return
        
        logger.info(f"Plan changed from {old_plan.name} to {new_plan.name}")
        
        # プランを更新
        subscription.plan = new_plan
        subscription.stripe_price_id = new_price_id
        
        # プラン変更履歴を記録
        from ..models import SubscriptionHistory
        SubscriptionHistory.objects.create(
            firm=subscription.firm,
            subscription=subscription,
            old_plan=old_plan,
            new_plan=new_plan,
            reason='Stripe Webhook経由でのプラン変更',
        )
        
        # 通知を作成
        from ..utils.notifications import notify_subscription_updated
        notify_subscription_updated(subscription.firm, new_plan.name)
        
        # ダウングレードの場合は処理を実行
        if old_plan.max_companies > new_plan.max_companies or (
            old_plan.max_companies == 0 and new_plan.max_companies > 0
        ):
            logger.info("Plan downgrade detected, handling grace period...")
            companies_in_grace, grace_days = handle_plan_downgrade(subscription.firm, new_plan)
            logger.info(f"{len(companies_in_grace)} companies entered grace period for {grace_days} days")
            
            # ダウングレード通知を作成
            from ..utils.notifications import notify_plan_downgrade
            notify_plan_downgrade(subscription.firm, old_plan.name, new_plan.name, len(companies_in_grace))
        
        # その他のサブスクリプション情報を更新
        subscription.status = subscription_data.get('status', subscription.status)
        subscription.current_period_start = timezone.datetime.fromtimestamp(
            subscription_data.get('current_period_start', 0),
            tz=timezone.utc
        ) if subscription_data.get('current_period_start') else subscription.current_period_start
        subscription.current_period_end = timezone.datetime.fromtimestamp(
            subscription_data.get('current_period_end', 0),
            tz=timezone.utc
        ) if subscription_data.get('current_period_end') else subscription.current_period_end
        subscription.canceled_at = timezone.datetime.fromtimestamp(
            subscription_data.get('canceled_at', 0),
            tz=timezone.utc
        ) if subscription_data.get('canceled_at') else subscription.canceled_at
        subscription.ends_at = timezone.datetime.fromtimestamp(
            subscription_data.get('cancel_at', 0),
            tz=timezone.utc
        ) if subscription_data.get('cancel_at') else subscription.ends_at
        
        subscription.save()
        logger.info(f"Subscription updated successfully: {subscription.id}")
    
    def _handle_invoice_payment_failed(self, invoice_data):
        """支払い失敗時の処理"""
        from ..utils.notifications import notify_payment_failed
        
        customer_id = invoice_data.get('customer')
        if not customer_id:
            logger.warning("No customer ID in invoice data")
            return
        
        # サブスクリプションを取得
        subscription = FirmSubscription.objects.filter(
            stripe_customer_id=customer_id
        ).first()
        
        if not subscription:
            logger.warning(f"Subscription not found for customer: {customer_id}")
            return
        
        # 通知を作成
        invoice_id = invoice_data.get('id')
        notify_payment_failed(subscription.firm, invoice_id)
        logger.info(f"Payment failed notification created for firm {subscription.firm.id}")
    
    def _handle_subscription_updated_old(self, subscription_data):
        """サブスクリプション更新時の処理"""
        stripe_subscription_id = subscription_data['id']
        logger.info(f"Handling subscription.updated for: {stripe_subscription_id}")
        
        try:
            subscription = FirmSubscription.objects.get(
                stripe_subscription_id=stripe_subscription_id
            )
            logger.info(f"Found subscription: {subscription.id} (Plan: {subscription.plan.name})")
        except FirmSubscription.DoesNotExist:
            logger.warning(f"Subscription not found: {stripe_subscription_id}, attempting to create")
            # サブスクリプションが見つからない場合は、作成処理を試みる
            self._handle_subscription_created(subscription_data)
            return
        
        # プラン変更のチェック（price_idが変更された場合）
        items = subscription_data.get('items', {}).get('data', [])
        logger.info(f"Subscription items: {len(items)} items found")
        
        if items:
            new_price_id = items[0].get('price', {}).get('id', '')
            logger.info(f"New price_id: {new_price_id}, Current price_id: {subscription.stripe_price_id}")
            
            if new_price_id and new_price_id != subscription.stripe_price_id:
                logger.info(f"Price ID changed, looking for new plan...")
                # 新しいプランを特定
                new_plan = FirmPlan.objects.filter(
                    stripe_price_id_monthly=new_price_id
                ).first() or FirmPlan.objects.filter(
                    stripe_price_id_yearly=new_price_id
                ).first()
                
                if new_plan:
                    old_plan = subscription.plan
                    subscription.plan = new_plan
                    subscription.stripe_price_id = new_price_id
                    logger.info(
                        f"Plan changed for subscription {subscription.id}: "
                        f"{old_plan.name} (ID: {old_plan.id}) -> {new_plan.name} (ID: {new_plan.id})"
                    )
                else:
                    logger.warning(
                        f"Plan not found for price_id: {new_price_id} "
                        f"in subscription {subscription.id}. "
                        f"Available plans: {list(FirmPlan.objects.values_list('stripe_price_id_monthly', 'stripe_price_id_yearly', 'name'))}"
                    )
            else:
                logger.info(f"Price ID unchanged or empty. No plan change needed.")
        
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
        logger.info(f"Subscription updated: {subscription.id} (status: {subscription.status}, plan: {subscription.plan.name})")
    
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
            logger.warning(f"Subscription not found: {stripe_subscription_id}, attempting to retrieve from Stripe")
            # Stripeからサブスクリプション情報を取得して作成
            try:
                stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
                logger.info(f"Retrieved subscription from Stripe: {stripe_subscription_id}")
                # サブスクリプション作成処理を呼び出す
                self._handle_subscription_created(stripe_subscription)
                # 再度取得
                subscription = FirmSubscription.objects.get(
                    stripe_subscription_id=stripe_subscription_id
                )
            except Exception as e:
                logger.error(f"Error retrieving subscription from Stripe: {e}")
                return
        
        # Stripeから最新のサブスクリプション情報を取得してプラン変更を確認
        try:
            stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
            logger.info(f"Retrieved latest subscription data from Stripe: {stripe_subscription_id}")
            
            # プラン変更のチェック（price_idが変更された場合）
            items = stripe_subscription.get('items', {}).get('data', [])
            if items:
                new_price_id = items[0].get('price', {}).get('id', '')
                logger.info(f"Current price_id in DB: {subscription.stripe_price_id}, Stripe price_id: {new_price_id}")
                
                if new_price_id and new_price_id != subscription.stripe_price_id:
                    logger.info(f"Price ID changed in invoice payment, updating plan...")
                    # 新しいプランを特定
                    new_plan = FirmPlan.objects.filter(
                        stripe_price_id_monthly=new_price_id
                    ).first() or FirmPlan.objects.filter(
                        stripe_price_id_yearly=new_price_id
                    ).first()
                    
                    if new_plan:
                        old_plan = subscription.plan
                        subscription.plan = new_plan
                        subscription.stripe_price_id = new_price_id
                        logger.info(
                            f"Plan changed for subscription {subscription.id}: "
                            f"{old_plan.name} (ID: {old_plan.id}) -> {new_plan.name} (ID: {new_plan.id})"
                        )
                    else:
                        logger.warning(
                            f"Plan not found for price_id: {new_price_id} "
                            f"in subscription {subscription.id}. "
                            f"Available plans: {list(FirmPlan.objects.values_list('stripe_price_id_monthly', 'stripe_price_id_yearly', 'name'))}"
                        )
        except Exception as e:
            logger.error(f"Error retrieving subscription from Stripe: {e}", exc_info=True)
        
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
        logger.info(f"Invoice payment succeeded for subscription: {subscription.id} (status: {subscription.status}, plan: {subscription.plan.name})")
    
    @transaction.atomic
    def _handle_invoice_payment_failed(self, invoice_data):
        """請求書の支払い失敗時の処理"""
        from ..utils.notifications import notify_payment_failed
        
        stripe_subscription_id = invoice_data.get('subscription')
        customer_id = invoice_data.get('customer')
        
        if not stripe_subscription_id:
            logger.warning("Invoice has no subscription")
            return
        
        # サブスクリプションを取得
        subscription = FirmSubscription.objects.filter(
            stripe_subscription_id=stripe_subscription_id
        ).first()
        
        if not subscription and customer_id:
            # 顧客IDから取得を試みる
            subscription = FirmSubscription.objects.filter(
                stripe_customer_id=customer_id
            ).first()
        
        if not subscription:
            logger.warning(f"Subscription not found for invoice: {invoice_data.get('id')}")
            return
        
        # 通知を作成
        invoice_id = invoice_data.get('id')
        notify_payment_failed(subscription.firm, invoice_id)
        logger.info(f"Payment failed notification created for firm {subscription.firm.id}")
        
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

