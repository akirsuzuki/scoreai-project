"""
プラン制限に関するユーティリティ関数
"""
from typing import Tuple, List
from django.utils import timezone
from django.db.models import Q
from ..models import Firm, FirmSubscription, FirmCompany


def get_current_company_count(firm: Firm, include_grace_period: bool = True) -> int:
    """
    Firmの現在のCompany数を取得
    
    Args:
        firm: Firmオブジェクト
        include_grace_period: グレース期間中のCompanyも含めるか
    
    Returns:
        現在のアクティブなCompany数（グレース期間中のものも含む）
    """
    queryset = FirmCompany.objects.filter(firm=firm)
    
    if include_grace_period:
        today = timezone.now().date()
        # アクティブなもの + グレース期間中のもの
        queryset = queryset.filter(
            Q(active=True) | 
            Q(active=False, grace_period_end__gte=today, grace_period_end__isnull=False)
        )
    else:
        queryset = queryset.filter(active=True)
    
    return queryset.count()


def get_companies_in_grace_period(firm: Firm) -> List[FirmCompany]:
    """
    グレース期間中のCompanyを取得
    
    Args:
        firm: Firmオブジェクト
    
    Returns:
        グレース期間中のFirmCompanyリスト
    """
    today = timezone.now().date()
    return list(FirmCompany.objects.filter(
        firm=firm,
        active=False,
        grace_period_end__gte=today,
        grace_period_end__isnull=False
    ).select_related('company'))


def get_exceeding_companies(firm: Firm) -> List[FirmCompany]:
    """
    プラン制限を超過しているCompanyを取得
    
    Args:
        firm: Firmオブジェクト
    
    Returns:
        超過しているFirmCompanyリスト（グレース期間中のものを除く）
    """
    max_allowed = get_max_companies_allowed(firm)
    if max_allowed == 0:
        return []
    
    # アクティブなCompanyを取得（グレース期間中のものを除く）
    active_companies = FirmCompany.objects.filter(
        firm=firm,
        active=True
    ).select_related('company').order_by('start_date')
    
    # 制限を超過している分を返す
    current_count = active_companies.count()
    if current_count > max_allowed:
        # 古いものから超過分を返す
        return list(active_companies[max_allowed:])
    
    return []


def get_max_companies_allowed(firm: Firm) -> int:
    """
    Firmが許可される最大Company数を取得
    
    Args:
        firm: Firmオブジェクト
    
    Returns:
        最大許可数（0の場合は無制限）
    """
    subscription = FirmSubscription.objects.filter(
        firm=firm,
        status__in=['trial', 'active']
    ).first()
    
    if not subscription:
        # サブスクリプションがない場合は制限なし（後方互換性）
        return 0
    
    return subscription.total_companies_allowed


def check_company_limit(firm: Firm) -> Tuple[bool, int, int]:
    """
    FirmのCompany数制限をチェック
    
    Args:
        firm: Firmオブジェクト
    
    Returns:
        (is_allowed, current_count, max_allowed)
        - is_allowed: 追加可能かどうか
        - current_count: 現在のCompany数
        - max_allowed: 最大許可数（0の場合は無制限）
    """
    current_count = get_current_company_count(firm)
    max_allowed = get_max_companies_allowed(firm)
    
    # 無制限の場合は常に許可
    if max_allowed == 0:
        return True, current_count, 0
    
    # 制限チェック
    is_allowed = current_count < max_allowed
    
    return is_allowed, current_count, max_allowed


def can_add_company(firm: Firm) -> bool:
    """
    Companyを追加できるかどうかを簡易チェック
    
    Args:
        firm: Firmオブジェクト
    
    Returns:
        追加可能な場合はTrue
    """
    is_allowed, _, _ = check_company_limit(firm)
    return is_allowed


