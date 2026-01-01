from django import template
from django.forms.widgets import Select
from django.utils.safestring import mark_safe
from urllib.parse import urlencode
import markdown

register = template.Library()

@register.filter
def to_thousands(value):
    try:
        value = int(value)
        return value // 1000
    except (ValueError, TypeError):
        return value

@register.filter
def percentage(value, arg):
    try:
        if value is None or arg is None:
            return None
        result = (float(value) / float(arg)) * 100
        return f"{result:.2f}%"
    except (ValueError, TypeError, ZeroDivisionError):
        return None

@register.filter
def get_last_item(queryset, index):
    try:
        return queryset[index]
    except IndexError:
        return None


@register.filter
def get_debt(debt_list, args):
    bank, secured_type = args.split(',')
    for debt in debt_list:
        if debt.financial_institution == bank and debt.secured_type == secured_type:
            return debt
    return None


@register.filter(name='add_class')
def add_class(field, css_class):
    if isinstance(field.field.widget, Select):
        return field.as_widget(attrs={'class': f'{field.field.widget.attrs.get("class", "")} {css_class}'.strip()})
    return field.as_widget(attrs={'class': f'{field.field.widget.attrs.get("class", "")} {css_class}'.strip()})


@register.filter
def get_item(dictionary, key):
    return dictionary.get(str(key))

@register.filter
def sum(values):
    return sum(values)

@register.filter
def average(values):
    if not values:
        return 0
    return sum(values) / len(values)


@register.filter
def divide(value, arg):
    try:
        if value is None or arg is None:
            return None
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return None

@register.filter
def multiply(value, arg):
    try:
        if value is None or arg is None:
            return None
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return None

@register.filter
def subtract(value, arg):
    try:
        if value is None or arg is None:
            return None
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return None

@register.filter(name='get_by_name')
def get_by_name(queryset, name):
    return queryset.filter(name=name).first()

@register.filter
def to(value, arg):
    return range(value, arg + 1)


@register.simple_tag
def update_query_params(request, **kwargs):
    """
    Update the query parameters of the current URL.
    Usage: {% update_query_params request page_param=2 %}
    """
    query_params = request.GET.copy()
    for key, value in kwargs.items():
        query_params[key] = value
    return '?' + urlencode(query_params)


@register.filter(name='markdown')
def markdown_filter(value):
    """
    MarkdownテキストをHTMLに変換
    Usage: {{ content|markdown }}
    """
    if not value:
        return ''
    md = markdown.Markdown(extensions=['extra', 'codehilite', 'tables', 'nl2br'])
    return mark_safe(md.convert(str(value)))