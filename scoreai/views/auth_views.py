"""
認証・ユーザー関連のビュー
"""
from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView, LogoutView,
    PasswordChangeView, PasswordChangeDoneView,
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from django.contrib.auth import login
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.views import generic
from django.conf import settings
import logging

from ..mixins import SelectedCompanyMixin
from ..models import UserCompany, CompanyInvitation, FirmInvitation
from ..forms import CustomUserCreationForm, LoginForm, UserProfileUpdateForm
from ..utils.security import (
    get_client_ip,
    check_rate_limit,
    reset_rate_limit,
    verify_recaptcha,
    log_suspicious_activity
)
from django.utils import timezone

logger = logging.getLogger(__name__)


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
    セキュリティ対策として、レート制限とreCAPTCHA検証を実装しています。
    """
    form_class = CustomUserCreationForm
    template_name = 'scoreai/user_create_form.html'
    success_url = reverse_lazy('index')

    def dispatch(self, request, *args, **kwargs):
        """リクエスト処理前のレート制限チェック"""
        # GETリクエストの場合は通常通り処理
        if request.method == 'GET':
            return super().dispatch(request, *args, **kwargs)
        
        # POSTリクエストの場合のみレート制限チェック
        is_allowed, error_message = check_rate_limit(
            request,
            key_prefix='user_registration',
            max_attempts=3,  # 5分間に3回まで
            time_window=300,  # 5分
            block_duration=3600  # 1時間ブロック
        )
        
        if not is_allowed:
            log_suspicious_activity(
                request,
                'user_registration_rate_limit_exceeded',
                {'ip': get_client_ip(request)}
            )
            messages.error(request, error_message)
            # フォームを取得してエラーを表示
            form = self.get_form()
            form.add_error(None, error_message)
            return self.form_invalid(form)
        
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """フォームバリデーション成功時の処理
        
        Args:
            form: バリデーション済みフォーム
            
        Returns:
            レスポンスオブジェクト
        """
        # reCAPTCHA検証（設定されている場合）
        recaptcha_secret = getattr(settings, 'RECAPTCHA_SECRET_KEY', None)
        if recaptcha_secret:
            recaptcha_token = self.request.POST.get('g-recaptcha-response')
            is_valid, error_message = verify_recaptcha(recaptcha_token, recaptcha_secret)
            
            if not is_valid:
                log_suspicious_activity(
                    self.request,
                    'user_registration_recaptcha_failed',
                    {
                        'ip': get_client_ip(self.request),
                        'email': form.cleaned_data.get('email'),
                        'username': form.cleaned_data.get('username')
                    }
                )
                messages.error(self.request, error_message or 'reCAPTCHA検証に失敗しました。')
                return self.form_invalid(form)
        
        response = super().form_valid(form)
        user = form.save()
        
        # セキュリティ強化: 新規ユーザーはメール認証まで無効化
        # 招待メールがある場合は有効化（既存の動作を維持）
        email = form.cleaned_data.get('email')
        has_invitation = False
        
        if email:
            # CompanyInvitationを検索（未承認のもの）
            company_invitations = CompanyInvitation.objects.filter(
                email=email,
                is_accepted=False
            )
            
            if company_invitations.exists():
                has_invitation = True
                for invitation in company_invitations:
                    # is_acceptedをTrueに更新（save()メソッドでUserCompanyが作成される）
                    invitation.is_accepted = True
                    invitation.accepted_at = timezone.now()
                    invitation.save()
            
            # FirmInvitationも同様に処理
            firm_invitations = FirmInvitation.objects.filter(
                email=email,
                is_accepted=False
            )
            
            if firm_invitations.exists():
                has_invitation = True
                for invitation in firm_invitations:
                    # is_acceptedをTrueに更新（save()メソッドでUserFirmが作成される）
                    invitation.is_accepted = True
                    invitation.accepted_at = timezone.now()
                    invitation.save()
        
        # 招待がない場合は、メール認証まで無効化
        if not has_invitation:
            user.is_active = False
            user.save()
            # TODO: メール認証機能を実装する場合はここでメール送信
        
        # レート制限をリセット（成功時）
        reset_rate_limit(self.request, 'user_registration')
        
        # ログイン（is_active=Trueの場合のみ）
        if user.is_active:
            login(self.request, user)
            messages.success(self.request, 'アカウントが正常に作成されました。')
        else:
            messages.success(
                self.request,
                'アカウントが作成されました。メール認証を完了してください。'
            )
        
        # 登録ログを記録
        logger.info(
            f"User registration successful: username={user.username}, "
            f"email={user.email}, ip={get_client_ip(self.request)}, "
            f"has_invitation={has_invitation}, is_active={user.is_active}"
        )
        
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
        from ..models import UserFirm, FirmCompany
        
        context = super().get_context_data(**kwargs)
        user = self.request.user
        username = user.username
        context['title'] = 'プロフィール'
        context['show_title_card'] = False
        
        # ユーザーの基本情報
        context['user'] = user
        
        # 所属しているCompany一覧
        context['user_companies'] = UserCompany.objects.filter(
            user=user
        ).select_related('company').order_by('-is_selected', '-is_owner')
        
        # 所属しているFirm一覧
        context['user_firms'] = UserFirm.objects.filter(
            user=user
        ).select_related('firm').order_by('-is_selected', '-is_owner')
        
        # 選択中のCompany
        selected_user_company = UserCompany.objects.filter(
            user=user, is_selected=True
        ).select_related('company').first()
        context['selected_company'] = selected_user_company.company if selected_user_company else None
        context['selected_user_company'] = selected_user_company
        
        # 選択中のFirm
        selected_user_firm = UserFirm.objects.filter(
            user=user, is_selected=True
        ).select_related('firm').first()
        context['selected_firm'] = selected_user_firm.firm if selected_user_firm else None
        context['selected_user_firm'] = selected_user_firm
        
        # ユーザーの属性を判定
        context['is_company_user'] = user.is_company_user
        context['is_financial_consultant'] = user.is_financial_consultant
        # いずれかの会社でマネージャーかどうかを判定
        is_manager_anywhere = UserCompany.objects.filter(
            user=user,
            is_manager=True,
            active=True
        ).exists()
        context['is_manager'] = is_manager_anywhere
        
        # ユーザーの役割を判定
        user_roles = []
        if user.is_company_user:
            user_roles.append('会社ユーザー')
        if user.is_financial_consultant:
            user_roles.append('財務コンサルタント')
        if is_manager_anywhere:
            user_roles.append('マネージャー')
        
        # Companyオーナーかどうか
        company_owner_count = UserCompany.objects.filter(user=user, is_owner=True).count()
        if company_owner_count > 0:
            user_roles.append(f'Companyオーナー ({company_owner_count}社)')
        
        # Firmオーナーかどうか
        firm_owner_count = UserFirm.objects.filter(user=user, is_owner=True).count()
        if firm_owner_count > 0:
            user_roles.append(f'Firmオーナー ({firm_owner_count}社)')
        
        # コンサルタントとしてのCompany数
        consultant_count = UserCompany.objects.filter(user=user, as_consultant=True).count()
        if consultant_count > 0:
            user_roles.append(f'コンサルタント ({consultant_count}社)')
        
        context['user_roles'] = user_roles if user_roles else ['一般ユーザー']
        
        # 統計情報
        context['total_companies'] = context['user_companies'].count()
        context['total_firms'] = context['user_firms'].count()
        
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
        context['title'] = 'プロフィール'
        context['show_title_card'] = False
        context['user_companies'] = UserCompany.objects.filter(
            user=self.request.user
        ).select_related('company')
        return context


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """カスタムパスワード変更ビュー"""
    template_name = 'scoreai/password_change.html'
    success_url = reverse_lazy('password_change_done')
    
    def get_form_class(self):
        """フォームクラスを取得"""
        from ..forms import CustomPasswordChangeForm
        return CustomPasswordChangeForm
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'パスワード変更'
        context['show_title_card'] = False
        return context


class CustomPasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    """パスワード変更完了ビュー"""
    template_name = 'scoreai/password_change_done.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'パスワード変更完了'
        context['show_title_card'] = False
        return context


class CustomPasswordResetView(PasswordResetView):
    """カスタムパスワードリセットビュー"""
    template_name = 'scoreai/password_reset.html'
    email_template_name = 'scoreai/password_reset_email.html'
    subject_template_name = 'scoreai/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')
    
    def get_form_class(self):
        """フォームクラスを取得"""
        from ..forms import CustomPasswordResetForm
        return CustomPasswordResetForm
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'パスワード再設定'
        context['show_title_card'] = False
        return context
    
    def form_valid(self, form):
        """フォームバリデーション成功時の処理"""
        messages.success(
            self.request,
            'パスワード再設定のメールを送信しました。メールボックスを確認してください。'
        )
        return super().form_valid(form)


class CustomPasswordResetDoneView(PasswordResetDoneView):
    """パスワードリセット送信完了ビュー"""
    template_name = 'scoreai/password_reset_done.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'パスワード再設定メール送信完了'
        context['show_title_card'] = False
        return context


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """パスワードリセット確認ビュー"""
    template_name = 'scoreai/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')
    
    def get_form_class(self):
        """フォームクラスを取得"""
        from ..forms import CustomSetPasswordForm
        return CustomSetPasswordForm
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'パスワード再設定'
        context['show_title_card'] = False
        return context


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    """パスワードリセット完了ビュー"""
    template_name = 'scoreai/password_reset_complete.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'パスワード再設定完了'
        context['show_title_card'] = False
        return context

