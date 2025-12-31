"""
通知機能のユーティリティ関数
"""
from django.utils import timezone
from ..models import Firm, FirmNotification, FirmSubscription, FirmUsageTracking
from .plan_limits import get_current_company_count, get_max_companies_allowed
import logging

logger = logging.getLogger(__name__)


def create_notification(firm: Firm, notification_type: str, title: str, message: str) -> FirmNotification:
    """
    通知を作成
    
    Args:
        firm: Firmオブジェクト
        notification_type: 通知タイプ
        title: タイトル
        message: メッセージ
    
    Returns:
        FirmNotificationオブジェクト
    """
    return FirmNotification.objects.create(
        firm=firm,
        notification_type=notification_type,
        title=title,
        message=message,
    )


def check_and_notify_plan_limits(firm: Firm):
    """
    プラン制限に近づいている場合の通知をチェック
    
    Args:
        firm: Firmオブジェクト
    """
    try:
        subscription = firm.subscription
    except FirmSubscription.DoesNotExist:
        return
    
    # Company数制限のチェック
    current_count = get_current_company_count(firm)
    max_allowed = get_max_companies_allowed(firm)
    
    if max_allowed > 0:
        usage_percentage = (current_count / max_allowed) * 100
        
        # 80%以上の場合に警告
        if usage_percentage >= 80:
            create_notification(
                firm=firm,
                notification_type='plan_limit_warning',
                title='Company数制限に近づいています',
                message=f'現在のCompany数: {current_count}社 / 上限: {max_allowed}社 ({usage_percentage:.1f}%)'
            )
    
    # 利用状況のチェック
    now = timezone.now()
    usage = FirmUsageTracking.objects.filter(
        firm=firm,
        year=now.year,
        month=now.month
    ).first()
    
    if usage:
        # AI相談回数のチェック
        if not subscription.plan.is_unlimited_ai_consultations:
            total = subscription.total_ai_consultations_allowed
            if total > 0:
                usage_percentage = (usage.ai_consultation_count / total) * 100
                if usage_percentage >= 80:
                    create_notification(
                        firm=firm,
                        notification_type='plan_limit_warning',
                        title='AI相談回数制限に近づいています',
                        message=f'現在の利用回数: {usage.ai_consultation_count}回 / 上限: {total}回 ({usage_percentage:.1f}%)'
                    )
        
        # OCR回数のチェック
        if not subscription.plan.is_unlimited_ocr:
            total = subscription.total_ocr_allowed
            if total > 0:
                usage_percentage = (usage.ocr_count / total) * 100
                if usage_percentage >= 80:
                    create_notification(
                        firm=firm,
                        notification_type='plan_limit_warning',
                        title='OCR読み込み回数制限に近づいています',
                        message=f'現在の利用回数: {usage.ocr_count}回 / 上限: {total}回 ({usage_percentage:.1f}%)'
                    )


def notify_payment_failed(firm: Firm, invoice_id: str = None):
    """
    支払い失敗の通知を作成
    
    Args:
        firm: Firmオブジェクト
        invoice_id: Stripe請求書ID（オプション）
    """
    create_notification(
        firm=firm,
        notification_type='payment_failed',
        title='支払いに失敗しました',
        message=f'サブスクリプションの支払い処理に失敗しました。支払い方法を確認してください。' + (f'請求書ID: {invoice_id}' if invoice_id else '')
    )


def notify_subscription_updated(firm: Firm, plan_name: str):
    """
    サブスクリプション更新の通知を作成
    
    Args:
        firm: Firmオブジェクト
        plan_name: 新しいプラン名
    """
    create_notification(
        firm=firm,
        notification_type='subscription_updated',
        title='サブスクリプションが更新されました',
        message=f'プランが「{plan_name}」に変更されました。'
    )


def notify_member_invited(firm: Firm, email: str, invited_by: str):
    """
    メンバー招待の通知を作成
    
    Args:
        firm: Firmオブジェクト
        email: 招待されたメールアドレス
        invited_by: 招待者のユーザー名
    """
    create_notification(
        firm=firm,
        notification_type='member_invited',
        title='新しいメンバーが招待されました',
        message=f'{invited_by}さんが{email}をメンバーとして招待しました。'
    )


def notify_plan_downgrade(firm: Firm, old_plan_name: str, new_plan_name: str, companies_in_grace: int):
    """
    プランダウングレードの通知を作成
    
    Args:
        firm: Firmオブジェクト
        old_plan_name: 旧プラン名
        new_plan_name: 新プラン名
        companies_in_grace: グレース期間に入ったCompany数
    """
    create_notification(
        firm=firm,
        notification_type='plan_downgrade',
        title='プランがダウングレードされました',
        message=f'プランが「{old_plan_name}」から「{new_plan_name}」に変更されました。{companies_in_grace}社がグレース期間（30日間）に入りました。'
    )


def notify_grace_period_ending(firm: Firm, company_name: str, days_remaining: int):
    """
    グレース期間終了間近の通知を作成
    
    Args:
        firm: Firmオブジェクト
        company_name: Company名
        days_remaining: 残り日数
    """
    create_notification(
        firm=firm,
        notification_type='grace_period_ending',
        title='グレース期間が終了間近です',
        message=f'{company_name}のグレース期間が残り{days_remaining}日で終了します。プランをアップグレードするか、Companyを削除してください。'
    )

