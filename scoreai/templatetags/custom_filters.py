from django import template
from django.forms.widgets import Select

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
        result = (float(value) / float(arg)) * 100
        return f"{result:.2f}%"
    except (ValueError, ZeroDivisionError):
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
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return None

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except ValueError:
        return None

@register.filter(name='get_by_name')
def get_by_name(queryset, name):
    return queryset.filter(name=name).first()