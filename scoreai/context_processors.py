from .models import UserCompany


# どのページからでもthis_companyを使えるようにするため
def selected_company(request):
    if request.user.is_authenticated:
        selected_company = UserCompany.objects.filter(user=request.user, is_selected=True).first()
        return {'this_company': selected_company.company if selected_company else None}
    return {'this_company': None}
