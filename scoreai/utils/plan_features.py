"""
プラン機能制限に関するユーティリティ関数
"""
from typing import Tuple
from ..models import Firm, FirmSubscription, FirmPlan


def check_plan_feature_access(firm: Firm, required_plan_type: str = 'starter') -> Tuple[bool, str]:
    """
    プランの機能アクセス権限をチェック
    
    Args:
        firm: Firmオブジェクト
        required_plan_type: 必要なプランタイプ（'free', 'starter', 'professional', 'enterprise'）
    
    Returns:
        (is_allowed, message)
        - is_allowed: アクセス可能かどうか
        - message: エラーメッセージ（アクセス不可の場合）
    """
    try:
        subscription = firm.subscription
    except FirmSubscription.DoesNotExist:
        return False, 'サブスクリプションが見つかりません。プランを登録してください。'
    
    if not subscription.plan:
        return False, 'プランが設定されていません。'
    
    # プランタイプの優先順位
    plan_hierarchy = {
        'free': 0,
        'starter': 1,
        'professional': 2,
        'enterprise': 3,
    }
    
    current_plan_level = plan_hierarchy.get(subscription.plan.plan_type, -1)
    required_plan_level = plan_hierarchy.get(required_plan_type, -1)
    
    if current_plan_level < required_plan_level:
        plan_names = {
            'free': 'Freeプラン',
            'starter': 'Starterプラン',
            'professional': 'Professionalプラン',
            'enterprise': 'Enterpriseプラン',
        }
        required_plan_name = plan_names.get(required_plan_type, required_plan_type)
        return False, f'この機能は{required_plan_name}以上で利用できます。現在のプラン: {subscription.plan.name}'
    
    return True, ''

