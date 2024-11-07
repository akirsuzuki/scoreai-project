from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(str(key))


# custom_filter側でget_itemを定義済みなので、こちらは使わない。使用箇所がわかったらHTMLを修正してこちらを削除。