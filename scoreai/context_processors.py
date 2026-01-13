from .models import UserCompany
from django.conf import settings


# どのページからでもthis_companyを使えるようにするため
def selected_company(request):
    if request.user.is_authenticated:
        selected_company = UserCompany.objects.filter(user=request.user, is_selected=True).first()
        return {'this_company': selected_company.company if selected_company else None}
    return {'this_company': None}


# reCAPTCHA設定をテンプレートで使用できるようにする
def recaptcha_settings(request):
    return {
        'RECAPTCHA_SITE_KEY': getattr(settings, 'RECAPTCHA_SITE_KEY', '')
    }
