from django import template
from scoreai.models import UserFirm

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(str(key))


@register.simple_tag
def get_user_firm_owner(user):
    """ユーザーがオーナーであるFirmを取得"""
    if not user or not user.is_authenticated:
        return None
    
    user_firm = UserFirm.objects.filter(
        user=user,
        is_owner=True,
        active=True
    ).select_related('firm').first()
    
    return user_firm


# custom_filter側でget_itemを定義済みなので、こちらは使わない。使用箇所がわかったらHTMLを修正してこちらを削除。