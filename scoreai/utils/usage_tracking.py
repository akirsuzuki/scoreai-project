"""
利用状況追跡のユーティリティ関数
"""
from django.utils import timezone
from django.db import transaction
from ..models import Firm, FirmSubscription, FirmUsageTracking, Company, CompanyUsageTracking
import logging

logger = logging.getLogger(__name__)


def get_or_create_usage_tracking(firm: Firm, subscription: FirmSubscription = None) -> FirmUsageTracking:
    """
    現在の月の利用状況追跡を取得または作成
    
    Args:
        firm: Firmオブジェクト
        subscription: FirmSubscriptionオブジェクト（指定しない場合は自動取得）
    
    Returns:
        FirmUsageTrackingオブジェクト
    """
    if subscription is None:
        try:
            subscription = firm.subscription
        except FirmSubscription.DoesNotExist:
            logger.warning(f"Subscription not found for firm {firm.id}")
            return None
    
    now = timezone.now()
    year = now.year
    month = now.month
    
    usage_tracking, created = FirmUsageTracking.objects.get_or_create(
        firm=firm,
        subscription=subscription,
        year=year,
        month=month,
        defaults={
            'ai_consultation_count': 0,
            'ocr_count': 0,
            'api_count': 0,
            'is_reset': False,
        }
    )
    
    return usage_tracking


@transaction.atomic
def increment_ai_consultation_count(firm: Firm, user=None) -> bool:
    """
    AI相談回数をインクリメント（Company Userの場合のみ）
    
    Args:
        firm: Firmオブジェクト
        user: Userオブジェクト（Company Userの場合のみカウント）
    
    Returns:
        成功した場合True、失敗した場合False
    """
    # Company Userの場合のみカウント
    if user and not user.is_company_user:
        return True  # カウントしないが、エラーではない
    try:
        subscription = firm.subscription
    except FirmSubscription.DoesNotExist:
        logger.warning(f"Subscription not found for firm {firm.id}")
        return False
    
    # 利用制限をチェック
    if not subscription.is_active_subscription:
        logger.warning(f"Subscription is not active for firm {firm.id}")
        return False
    
    usage_tracking = get_or_create_usage_tracking(firm, subscription)
    if not usage_tracking:
        return False
    
    # 無制限の場合はカウントしない
    if subscription.plan.is_unlimited_ai_consultations:
        return True
    
    # 利用制限をチェック
    remaining = usage_tracking.ai_consultation_remaining
    if remaining is not None and remaining <= 0:
        logger.warning(f"AI consultation limit reached for firm {firm.id}")
        return False
    
    # カウントをインクリメント
    usage_tracking.ai_consultation_count += 1
    usage_tracking.save()
    
    logger.info(f"Incremented AI consultation count for firm {firm.id}: {usage_tracking.ai_consultation_count}")
    return True


@transaction.atomic
def increment_ocr_count(firm: Firm, user=None) -> bool:
    """
    OCR読み込み回数をインクリメント（Company Userの場合のみ）
    
    Args:
        firm: Firmオブジェクト
        user: Userオブジェクト（Company Userの場合のみカウント）
    
    Returns:
        成功した場合True、失敗した場合False
    """
    # Company Userの場合のみカウント
    if user and not user.is_company_user:
        return True  # カウントしないが、エラーではない
    try:
        subscription = firm.subscription
    except FirmSubscription.DoesNotExist:
        logger.warning(f"Subscription not found for firm {firm.id}")
        return False
    
    # 利用制限をチェック
    if not subscription.is_active_subscription:
        logger.warning(f"Subscription is not active for firm {firm.id}")
        return False
    
    usage_tracking = get_or_create_usage_tracking(firm, subscription)
    if not usage_tracking:
        return False
    
    # 無制限の場合はカウントしない
    if subscription.plan.is_unlimited_ocr:
        return True
    
    # 利用制限をチェック
    remaining = usage_tracking.ocr_remaining
    if remaining is not None and remaining <= 0:
        logger.warning(f"OCR limit reached for firm {firm.id}")
        return False
    
    # カウントをインクリメント
    usage_tracking.ocr_count += 1
    usage_tracking.save()
    
    logger.info(f"Incremented OCR count for firm {firm.id}: {usage_tracking.ocr_count}")
    return True


def get_or_create_company_usage_tracking(company: Company, firm: Firm) -> CompanyUsageTracking:
    """
    現在の月のCompany利用状況追跡を取得または作成
    
    Args:
        company: Companyオブジェクト
        firm: Firmオブジェクト
    
    Returns:
        CompanyUsageTrackingオブジェクト
    """
    now = timezone.now()
    year = now.year
    month = now.month
    
    usage_tracking, created = CompanyUsageTracking.objects.get_or_create(
        company=company,
        firm=firm,
        year=year,
        month=month,
        defaults={
            'ai_consultation_count': 0,
            'ocr_count': 0,
            'api_count': 0,
            'is_reset': False,
        }
    )
    
    return usage_tracking


@transaction.atomic
def increment_company_api_count(company: Company, firm: Firm, user=None) -> bool:
    """
    CompanyのAPI利用回数をインクリメント（Company Userの場合のみ）
    
    Args:
        company: Companyオブジェクト
        firm: Firmオブジェクト
        user: Userオブジェクト（Company Userの場合のみカウント）
    
    Returns:
        成功した場合True、失敗した場合False
    """
    # Company Userの場合のみカウント
    if user and not user.is_company_user:
        return True  # カウントしないが、エラーではない
    
    try:
        subscription = firm.subscription
    except FirmSubscription.DoesNotExist:
        logger.warning(f"Subscription not found for firm {firm.id}")
        return False
    
    # 利用制限をチェック
    if not subscription.is_active_subscription:
        logger.warning(f"Subscription is not active for firm {firm.id}")
        return False
    
    usage_tracking = get_or_create_company_usage_tracking(company, firm)
    
    # カウントをインクリメント
    usage_tracking.api_count += 1
    usage_tracking.save()
    
    logger.info(f"Incremented Company API count for company {company.id} in firm {firm.id}: {usage_tracking.api_count}")
    return True

