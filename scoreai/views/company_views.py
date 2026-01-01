"""
会社関連のビュー
"""
from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import DetailView, UpdateView

from django.contrib.auth.mixins import LoginRequiredMixin
from ..mixins import SelectedCompanyMixin
from ..models import Company, UserCompany, IndustrySubClassification
from ..forms import CompanyForm


class CompanyDetailView(LoginRequiredMixin, DetailView):  # SelectedCompanyMixinは不要（会社選択は不要）
    """会社詳細ビュー"""
    model = Company
    template_name = 'scoreai/company_detail.html'
    context_object_name = 'company'
    slug_field = 'id'
    slug_url_kwarg = 'id'

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得
        
        Args:
            **kwargs: 追加のキーワード引数
            
        Returns:
            コンテキストデータの辞書
        """
        context = super().get_context_data(**kwargs)
        context['title'] = f'{self.object.name} の詳細'
        context['user_count'] = self.object.user_count
        context['users'] = UserCompany.objects.filter(
            company=self.object,
            active=True
        ).select_related('user', 'company')
        
        # 現在のユーザーがこのCompanyのOwnerかどうかを判定
        if self.request.user.is_authenticated:
            context['is_company_owner'] = UserCompany.objects.filter(
                user=self.request.user,
                company=self.object,
                is_owner=True,
                active=True
            ).exists()
        else:
            context['is_company_owner'] = False
        
        return context


class CompanyUpdateView(SelectedCompanyMixin, UpdateView):
    """会社情報更新ビュー"""
    model = Company
    form_class = CompanyForm
    template_name = 'scoreai/company_form.html'
    success_url = reverse_lazy('company_detail')

    def get_object(self, queryset=None):
        """更新対象のオブジェクトを取得
        
        Args:
            queryset: クエリセット（未使用）
            
        Returns:
            選択された会社オブジェクト
        """
        # SelectedCompanyMixin から選択された会社を取得
        return self.this_company

    def form_valid(self, form):
        """フォームバリデーション成功時の処理
        
        Args:
            form: バリデーション済みフォーム
            
        Returns:
            レスポンスオブジェクト
        """
        messages.success(self.request, '会社情報が正常に更新されました。')
        return super().form_valid(form)

    def get_success_url(self):
        """成功時のリダイレクト先URLを取得
        
        Returns:
            リダイレクト先のURL
        """
        return reverse_lazy('company_detail', kwargs={'id': self.object.id})

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得
        
        Args:
            **kwargs: 追加のキーワード引数
            
        Returns:
            コンテキストデータの辞書
        """
        context = super().get_context_data(**kwargs)
        context['title'] = '会社情報編集'
        return context


def load_industry_subclassifications(request):
    """業種小分類をAJAXで取得
    
    会社情報編集時に業種分類の親子関係の入力制御を画面上で行うための処理。
    
    Args:
        request: HTTPリクエストオブジェクト
        
    Returns:
        JSONレスポンス（業種小分類のリスト）
    """
    industry_classification_id = request.GET.get('industry_classification')
    subclassifications = IndustrySubClassification.objects.filter(
        industry_classification_id=industry_classification_id
    ).select_related('industry_classification').order_by('name')
    return JsonResponse(list(subclassifications.values('id', 'name')), safe=False)

