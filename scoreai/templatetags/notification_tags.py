"""
通知機能用のテンプレートタグ
"""
from django import template
from ..models import FirmNotification

register = template.Library()


@register.simple_tag
def get_unread_notification_count(firm):
    """未読通知数を取得"""
    if not firm:
        return 0
    return FirmNotification.objects.filter(firm=firm, is_read=False).count()

