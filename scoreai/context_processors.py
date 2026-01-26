from .models import UserCompany
from django.conf import settings


# どのページからでもthis_companyを使えるようにするため
def selected_company(request):
    if request.user.is_authenticated:
        # 選択中の会社
        selected_uc = UserCompany.objects.filter(user=request.user, is_selected=True).select_related('company').first()
        # ユーザーが所属する全会社（会社切り替え用）
        user_companies = UserCompany.objects.filter(
            user=request.user, 
            active=True
        ).select_related('company').order_by('company__name')
        return {
            'this_company': selected_uc.company if selected_uc else None,
            'header_user_companies': user_companies
        }
    return {'this_company': None, 'header_user_companies': []}


# reCAPTCHA設定をテンプレートで使用できるようにする
def recaptcha_settings(request):
    return {
        'RECAPTCHA_SITE_KEY': getattr(settings, 'RECAPTCHA_SITE_KEY', '')
    }
