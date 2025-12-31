"""
プラン機能制限用のテンプレートタグ
"""
from django import template
from ..utils.plan_features import check_plan_feature_access

register = template.Library()


@register.simple_tag
def check_plan_feature_access_tag(firm, required_plan_type='starter'):
    """プランの機能アクセス権限をチェック（テンプレート用）"""
    if not firm:
        return (False, 'Firmが見つかりません。')
    return check_plan_feature_access(firm, required_plan_type)

