"""
プランダウングレード時の処理
"""
from typing import List, Tuple
from django.utils import timezone
from datetime import timedelta
from ..models import Firm, FirmPlan, FirmSubscription, FirmCompany
from .plan_limits import get_max_companies_allowed, get_current_company_count, get_exceeding_companies


def handle_plan_downgrade(firm: Firm, new_plan: FirmPlan) -> Tuple[List[FirmCompany], int]:
    """
    プランダウングレード時の処理
    
    Args:
        firm: Firmオブジェクト
        new_plan: 新しいプラン
    
    Returns:
        (グレース期間に入ったCompanyリスト, グレース期間日数)
    """
    new_max = new_plan.max_companies if new_plan.max_companies > 0 else 0
    current_count = get_current_company_count(firm, include_grace_period=False)
    
    # 無制限プランへの変更の場合は何もしない
    if new_max == 0:
        return [], 0
    
    # 制限内の場合は何もしない
    if current_count <= new_max:
        return [], 0
    
    # 超過しているCompanyを取得
    exceeding_companies = get_exceeding_companies(firm)
    
    if not exceeding_companies:
        return [], 0
    
    # グレース期間を設定（30日間）
    grace_period_days = 30
    grace_period_end = timezone.now().date() + timedelta(days=grace_period_days)
    
    # 超過しているCompanyをグレース期間に入れる
    companies_in_grace = []
    for firm_company in exceeding_companies:
        firm_company.active = False
        firm_company.grace_period_end = grace_period_end
        firm_company.save()
        companies_in_grace.append(firm_company)
    
    return companies_in_grace, grace_period_days


def check_downgrade_warning(firm: Firm, new_plan: FirmPlan) -> Tuple[bool, int, List[FirmCompany]]:
    """
    ダウングレード時の警告情報を取得
    
    Args:
        firm: Firmオブジェクト
        new_plan: 新しいプラン
    
    Returns:
        (警告が必要か, 超過数, 超過しているCompanyリスト)
    """
    new_max = new_plan.max_companies if new_plan.max_companies > 0 else 0
    current_count = get_current_company_count(firm, include_grace_period=False)
    
    # 無制限プランへの変更の場合は警告不要
    if new_max == 0:
        return False, 0, []
    
    # 制限内の場合は警告不要
    if current_count <= new_max:
        return False, 0, []
    
    # 超過している
    exceeding_companies = get_exceeding_companies(firm)
    exceed_count = current_count - new_max
    
    return True, exceed_count, exceeding_companies

