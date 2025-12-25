"""
認証・ユーザー関連のビュー
"""
from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import login
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.views import generic

from ..mixins import SelectedCompanyMixin
from ..models import UserCompany
from ..forms import CustomUserCreationForm, LoginForm, UserProfileUpdateForm


class LoginView(LoginView):  # LoginViewは認証不要なのでSelectedCompanyMixinは不要
    """ログインビュー"""
    form_class = LoginForm
    template_name = 'scoreai/login.html'


class ScoreLogoutView(LogoutView):  # LogoutViewは認証済みユーザーのみなのでLoginRequiredMixinは不要
    """ログアウトビュー"""
    template_name = 'scoreai/logout.html'


class UserCreateView(CreateView):
    """ユーザー作成ビュー
    
    新規ユーザーアカウントを作成します。
    """
    form_class = CustomUserCreationForm
    template_name = 'scoreai/user_create_form.html'
    success_url = reverse_lazy('index')

    def form_valid(self, form):
        """フォームバリデーション成功時の処理
        
        Args:
            form: バリデーション済みフォーム
            
        Returns:
            レスポンスオブジェクト
        """
        response = super().form_valid(form)
        user = form.save()
        login(self.request, user)
        messages.success(self.request, 'アカウントが正常に作成されました。')
        return response

    def form_invalid(self, form):
        """フォームバリデーション失敗時の処理
        
        Args:
            form: バリデーション失敗したフォーム
            
        Returns:
            レスポンスオブジェクト
        """
        messages.error(self.request, 'アカウントの作成に失敗しました。入力内容を確認してください。')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得
        
        Args:
            **kwargs: 追加のキーワード引数
            
        Returns:
            コンテキストデータの辞書
        """
        context = super().get_context_data(**kwargs)
        context['title'] = 'ユーザー登録'
        return context


class UserProfileView(SelectedCompanyMixin, generic.TemplateView):
    """ユーザープロフィール表示ビュー"""
    template_name = 'scoreai/user_profile.html'

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得
        
        Args:
            **kwargs: 追加のキーワード引数
            
        Returns:
            コンテキストデータの辞書
        """
        context = super().get_context_data(**kwargs)
        username = self.request.user.username
        context['title'] = f'{username}のユーザー情報'
        context['user_companies'] = UserCompany.objects.filter(
            user=self.request.user
        ).select_related('company')
        return context


class UserProfileUpdateView(SelectedCompanyMixin, UpdateView):
    """ユーザープロフィール更新ビュー"""
    form_class = UserProfileUpdateForm
    template_name = 'scoreai/user_profile_update.html'
    success_url = reverse_lazy('user_profile')

    def get_object(self, queryset=None):
        """更新対象のオブジェクトを取得
        
        Args:
            queryset: クエリセット（未使用）
            
        Returns:
            現在ログインしているユーザーオブジェクト
        """
        return self.request.user

    def form_valid(self, form):
        """フォームバリデーション成功時の処理
        
        Args:
            form: バリデーション済みフォーム
            
        Returns:
            レスポンスオブジェクト
        """
        response = super().form_valid(form)
        messages.success(self.request, 'プロフィールが正常に更新されました。')
        return response

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得
        
        Args:
            **kwargs: 追加のキーワード引数
            
        Returns:
            コンテキストデータの辞書
        """
        context = super().get_context_data(**kwargs)
        context['title'] = 'プロフィール更新'
        context['user_companies'] = UserCompany.objects.filter(
            user=self.request.user
        ).select_related('company')
        return context

