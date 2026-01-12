from django import template
from scoreai.models import UserFirm, UserCompany

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


@register.simple_tag
def get_user_selected_company(user):
    """ユーザーが選択中のCompanyを取得"""
    if not user or not user.is_authenticated:
        return None
    
    user_company = UserCompany.objects.filter(
        user=user,
        is_selected=True,
        active=True
    ).select_related('company').first()
    
    return user_company.company if user_company else None


@register.simple_tag
def get_user_company(user, company):
    """ユーザーとCompanyからUserCompanyを取得"""
    if not user or not user.is_authenticated or not company:
        return None
    
    user_company = UserCompany.objects.filter(
        user=user,
        company=company,
        active=True
    ).select_related('company', 'user').first()
    
    return user_company


@register.simple_tag
def get_user_selected_firm(user):
    """ユーザーが選択中のFirmを取得"""
    if not user or not user.is_authenticated:
        return None
    
    user_firm = UserFirm.objects.filter(
        user=user,
        is_selected=True,
        active=True
    ).select_related('firm').first()
    
    return user_firm.firm if user_firm else None


@register.simple_tag
def get_company_firm_for_plan_check(company):
    """Companyが属するFirmを取得（プランチェック用）"""
    if not company:
        return None
    
    from scoreai.models import FirmCompany
    firm_company = FirmCompany.objects.filter(
        company=company,
        active=True
    ).select_related('firm', 'firm__subscription', 'firm__subscription__plan').first()
    
    return firm_company.firm if firm_company else None


# custom_filter側でget_itemを定義済みなので、こちらは使わない。使用箇所がわかったらHTMLを修正してこちらを削除。