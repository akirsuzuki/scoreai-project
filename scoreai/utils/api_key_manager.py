"""
APIキー管理と利用制限チェックのユーティリティ関数
"""
from typing import Optional, Tuple, Dict
from django.conf import settings
from django.utils import timezone
from django.db import transaction
import logging

from ..models import Firm, FirmSubscription, FirmUsageTracking, Company, User
from .usage_tracking import increment_company_api_count

logger = logging.getLogger(__name__)


def get_api_key_for_ai_consultation(
    firm: Firm,
    company: Company,
    user: User
) -> Tuple[Optional[str], Optional[str], str]:
    """
    AI相談で使用するAPIキーとプロバイダーを決定
    
    優先順位:
    1. 上限を超えている場合:
       - Company User かつ CompanyにAPIキーがある場合 → CompanyのAPIキー
       - それ以外でFirmにAPIキーがある場合 → FirmのAPIキー
       - それ以外 → SCOREのAPIキー（エラーになる可能性あり）
    2. 上限内の場合:
       - SCOREのAPIキーを使用
    
    Args:
        firm: Firmオブジェクト
        company: Companyオブジェクト
        user: Userオブジェクト
    
    Returns:
        (api_key, api_provider, source)のタプル
        - api_key: 使用するAPIキー（Noneの場合はSCOREのデフォルト）
        - api_provider: APIプロバイダー（'gemini' or 'openai'）
        - source: キーのソース（'score', 'firm', 'company'）
    """
    try:
        subscription = firm.subscription
    except FirmSubscription.DoesNotExist:
        logger.warning(f"Subscription not found for firm {firm.id}")
        # サブスクリプションがない場合はSCOREのAPIキーを使用
        return None, 'gemini', 'score'
    
    # 現在の月の利用状況を取得
    now = timezone.now()
    usage_tracking = FirmUsageTracking.objects.filter(
        firm=firm,
        subscription=subscription,
        year=now.year,
        month=now.month
    ).first()
    
    if not usage_tracking:
        # 利用状況がまだ作成されていない場合は上限内とみなす
        return None, 'gemini', 'score'
    
    # API利用上限をチェック
    api_limit = subscription.api_limit
    if api_limit == 0:
        # 無制限の場合は常にSCOREのAPIキーを使用
        return None, 'gemini', 'score'
    
    # 上限を超えているかチェック
    if usage_tracking.api_count >= api_limit:
        # 上限を超えている場合
        
        # Company User かつ CompanyにAPIキーがある場合
        if user.is_company_user and company.api_key and company.api_provider:
            logger.info(f"Using Company API key for company {company.id} (exceeded limit)")
            return company.api_key, company.api_provider, 'company'
        
        # FirmにAPIキーがある場合
        if firm.api_key and firm.api_provider:
            logger.info(f"Using Firm API key for firm {firm.id} (exceeded limit)")
            return firm.api_key, firm.api_provider, 'firm'
        
        # APIキーがない場合はSCOREのAPIキーを使用（エラーになる可能性あり）
        logger.warning(f"No API key available for exceeded limit. Using SCORE API key.")
        return None, 'gemini', 'score'
    
    # 上限内の場合はSCOREのAPIキーを使用
    return None, 'gemini', 'score'


@transaction.atomic
def increment_api_count(firm: Firm, user: Optional[User] = None, company: Optional['Company'] = None) -> bool:
    """
    API利用回数をインクリメント
    
    Args:
        firm: Firmオブジェクト
        user: Userオブジェクト
        company: Companyオブジェクト（Firmユーザーの場合、選択中のCompany）
    
    Returns:
        成功した場合True、失敗した場合False
    """
    try:
        subscription = firm.subscription
    except FirmSubscription.DoesNotExist:
        logger.warning(f"Subscription not found for firm {firm.id}")
        return False
    
    # 利用制限をチェック
    if not subscription.is_active_subscription:
        logger.warning(f"Subscription is not active for firm {firm.id}")
        return False
    
    # Firmユーザー（is_company_user=False）の場合、Companyの利用枠を使用できるかチェック
    if user and not user.is_company_user and company:
        from ..models import FirmCompany
        from .usage_tracking import get_or_create_company_usage_tracking
        
        # 選択中のCompanyのFirmCompanyを取得
        firm_company = FirmCompany.objects.filter(
            firm=firm,
            company=company,
            active=True
        ).first()
        
        if firm_company and firm_company.allow_firm_api_usage and firm_company.api_limit > 0:
            # Companyの利用枠を使用
            company_usage = get_or_create_company_usage_tracking(company, firm)
            
            # Companyの利用枠をチェック
            if company_usage.api_count >= firm_company.api_limit:
                logger.warning(f"Company API limit reached for company {company.id} in firm {firm.id}")
                return False
            
            # Companyの利用枠にカウント
            company_usage.api_count += 1
            company_usage.save()
            
            logger.info(f"Incremented API count for company {company.id} in firm {firm.id} (firm user): {company_usage.api_count}")
            return True
    
    # Company Userの場合のみFirmレベルでカウント
    if user and not user.is_company_user:
        return True  # FirmユーザーでCompanyの利用枠を使用できない場合はカウントしない
    
    from .usage_tracking import get_or_create_usage_tracking
    usage_tracking = get_or_create_usage_tracking(firm, subscription)
    if not usage_tracking:
        return False
    
    # 無制限の場合はカウントしない
    if subscription.api_limit == 0:
        return True
    
    # カウントをインクリメント
    usage_tracking.api_count += 1
    usage_tracking.save()
    
    logger.info(f"Incremented API count for firm {firm.id}: {usage_tracking.api_count}")
    return True

