from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from .models import UserCompany, Company

class SelectedCompanyMixin:
    # ログイン中であれば常にthis_companyを取得可能。classでself.this_companyとすればよい。
    def dispatch(self, request, *args, **kwargs):
        self.this_company = self.get_selected_company()
        return super().dispatch(request, *args, **kwargs)

    def get_selected_company(self):
        user = self.request.user
        user_company = UserCompany.objects.filter(user=user, is_selected=True).first()
        return user_company.company if user_company else None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['this_company'] = self.this_company
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        return self.filter_by_selected_company(queryset)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not self.is_object_in_selected_company(obj):
            raise PermissionDenied("このデータにアクセスする権限がありません。(mixins.py)")
        return obj

    def is_object_in_selected_company(self, obj):
        if self.this_company and hasattr(obj, 'company'):
            return obj.company == self.this_company
        return False

    def filter_by_selected_company(self, queryset):
        if self.this_company:
            return queryset.filter(company=self.this_company)
        return queryset.none()