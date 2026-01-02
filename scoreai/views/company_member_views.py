"""
Companyメンバー管理機能のビュー
"""
from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, FormView, View
from django.views import View as BaseView
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.template.loader import render_to_string
import logging

from ..models import Company, UserCompany, User, CompanyInvitation
from ..mixins import ErrorHandlingMixin
from ..forms import CompanyMemberInviteForm

logger = logging.getLogger(__name__)


class CompanyMemberListView(LoginRequiredMixin, ErrorHandlingMixin, ListView):
    """Companyメンバー一覧ビュー"""
    model = UserCompany
    template_name = 'scoreai/company_member_list.html'
    context_object_name = 'members'
    
    def dispatch(self, request, *args, **kwargs):
        """Companyのオーナーであることを確認"""
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        company_id = kwargs.get('company_id')
        company = get_object_or_404(Company, id=company_id)
        
        # オーナーであることを確認
        user_company = UserCompany.objects.filter(
            user=request.user,
            company=company,
            is_owner=True,
            active=True
        ).first()
        
        if not user_company:
            messages.error(request, 'このCompanyのオーナー権限がありません。')
            return redirect('index')
        
        self.company = company
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        """Companyに所属するメンバーを取得"""
        return UserCompany.objects.filter(
            company=self.company
        ).select_related('user').order_by('-is_owner', '-is_manager', 'user__username')
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = '会社メンバー管理'
        context['show_title_card'] = False
        context['company'] = self.company
        
        # 統計情報
        context['total_members'] = self.get_queryset().count()
        context['active_members'] = self.get_queryset().filter(active=True).count()
        context['owner_count'] = self.get_queryset().filter(is_owner=True).count()
        context['manager_count'] = self.get_queryset().filter(is_manager=True).count()
        
        # 招待中のメンバーを取得
        context['pending_invitations'] = CompanyInvitation.objects.filter(
            company=self.company,
            is_accepted=False
        ).select_related('invited_by').order_by('-invited_at')
        
        return context


class CompanyMemberInviteView(LoginRequiredMixin, ErrorHandlingMixin, FormView):
    """Companyメンバー招待ビュー"""
    template_name = 'scoreai/company_member_invite.html'
    form_class = CompanyMemberInviteForm
    
    def dispatch(self, request, *args, **kwargs):
        """Companyのオーナーであることを確認"""
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        company_id = kwargs.get('company_id')
        company = get_object_or_404(Company, id=company_id)
        
        # オーナーであることを確認
        user_company = UserCompany.objects.filter(
            user=request.user,
            company=company,
            is_owner=True,
            active=True
        ).first()
        
        if not user_company:
            messages.error(request, 'このCompanyのオーナー権限がありません。')
            return redirect('index')
        
        self.company = company
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = '会社メンバー管理'
        context['show_title_card'] = False
        context['company'] = self.company
        return context
    
    def form_valid(self, form):
        """フォームが有効な場合の処理"""
        email = form.cleaned_data['email']
        is_owner = form.cleaned_data.get('is_owner', False)
        is_manager = form.cleaned_data.get('is_manager', False)
        
        # 既存のユーザーを確認
        try:
            user = User.objects.get(email=email)
            
            # 既にCompanyに所属しているか確認
            existing_member = UserCompany.objects.filter(
                user=user,
                company=self.company
            ).first()
            
            if existing_member:
                if existing_member.active:
                    messages.warning(self.request, f'{email} は既にこのCompanyのメンバーです。')
                else:
                    # 非アクティブなメンバーの場合は再アクティブ化
                    existing_member.active = True
                    existing_member.is_owner = is_owner
                    existing_member.save()
                    
                    # Userモデルのis_managerを更新（UserCompanyにはis_managerフィールドがないため）
                    if is_manager:
                        user.is_manager = True
                        user.save()
                    
                    messages.success(self.request, f'{email} をメンバーとして再追加しました。')
            else:
                # 新規メンバーとして追加
                UserCompany.objects.create(
                    user=user,
                    company=self.company,
                    active=True,
                    is_owner=is_owner,
                    is_selected=False
                )
                
                # Userモデルのis_managerを更新（UserCompanyにはis_managerフィールドがないため）
                if is_manager:
                    user.is_manager = True
                    user.save()
                
                messages.success(self.request, f'{email} をメンバーとして追加しました。')
            
            # メール送信
            self._send_invitation_email(user, is_owner, is_manager)
            
        except User.DoesNotExist:
            # 新規ユーザーの場合は招待レコードを作成
            invitation = CompanyInvitation.objects.create(
                company=self.company,
                email=email,
                invited_by=self.request.user,
                is_owner=is_owner,
                is_manager=is_manager,
                is_accepted=False
            )
            
            # 新規ユーザーへの招待メールを送信
            self._send_invitation_email_to_new_user(email, is_owner, is_manager)
            
            messages.success(self.request, f'{email} への招待を送信しました。')
        
        return redirect('company_member_list', company_id=self.company.id)
    
    def _send_invitation_email(self, user, is_owner, is_manager):
        """既存ユーザーへの招待メールを送信"""
        try:
            role_parts = []
            if is_owner:
                role_parts.append('オーナー')
            if is_manager:
                role_parts.append('マネージャー')
            if not role_parts:
                role_parts.append('メンバー')
            role = '・'.join(role_parts)
            
            subject = f'{self.company.name} への招待'
            
            message = f"""
{user.username} 様

{self.company.name} の{role}として招待されました。

以下のリンクからログインして、Companyに参加してください：
{self.request.build_absolute_uri(reverse('index'))}

よろしくお願いします。
"""
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            logger.info(f"Invitation email sent to {user.email} for company {self.company.id}")
        except Exception as e:
            logger.error(f"Error sending invitation email: {e}", exc_info=True)
            messages.warning(self.request, 'メールの送信に失敗しましたが、メンバーは追加されました。')
    
    def _send_invitation_email_to_new_user(self, email, is_owner, is_manager):
        """新規ユーザーへの招待メールを送信"""
        try:
            role_parts = []
            if is_owner:
                role_parts.append('オーナー')
            if is_manager:
                role_parts.append('マネージャー')
            if not role_parts:
                role_parts.append('メンバー')
            role = '・'.join(role_parts)
            
            subject = f'{self.company.name} への招待'
            
            message = f"""
{email} 様

{self.company.name} の{role}として招待されました。

以下のリンクからアカウントを作成して、Companyに参加してください：
{self.request.build_absolute_uri(reverse('user_create'))}

よろしくお願いします。
"""
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            logger.info(f"Invitation email sent to {email} for company {self.company.id}")
        except Exception as e:
            logger.error(f"Error sending invitation email: {e}", exc_info=True)
            messages.warning(self.request, 'メールの送信に失敗しましたが、招待は記録されました。')


class CompanyMemberDeleteView(LoginRequiredMixin, ErrorHandlingMixin, View):
    """Companyメンバー削除ビュー"""
    
    def post(self, request, company_id, member_id):
        """メンバーを削除（非アクティブ化）"""
        company = get_object_or_404(Company, id=company_id)
        
        # オーナーであることを確認
        user_company = UserCompany.objects.filter(
            user=request.user,
            company=company,
            is_owner=True,
            active=True
        ).first()
        
        if not user_company:
            messages.error(request, 'このCompanyのオーナー権限がありません。')
            return redirect('index')
        
        # 削除対象のメンバーを取得
        member = get_object_or_404(UserCompany, id=member_id, company=company)
        
        # 自分自身は削除できない
        if member.user == request.user:
            messages.error(request, '自分自身を削除することはできません。')
            return redirect('company_member_list', company_id=company.id)
        
        # 非アクティブ化
        member.active = False
        member.is_selected = False
        member.save()
        
        messages.success(request, f'{member.user.username} をメンバーから削除しました。')
        return redirect('company_member_list', company_id=company.id)


class CompanyInvitationCancelView(LoginRequiredMixin, ErrorHandlingMixin, View):
    """Company招待キャンセルビュー"""
    
    def post(self, request, company_id, invitation_id):
        """招待をキャンセル"""
        company = get_object_or_404(Company, id=company_id)
        
        # オーナーであることを確認
        user_company = UserCompany.objects.filter(
            user=request.user,
            company=company,
            is_owner=True,
            active=True
        ).first()
        
        if not user_company:
            messages.error(request, 'このCompanyのオーナー権限がありません。')
            return redirect('index')
        
        # 招待を取得
        invitation = get_object_or_404(CompanyInvitation, id=invitation_id, company=company)
        
        # 承認済みの場合は削除できない
        if invitation.is_accepted:
            messages.error(request, '承認済みの招待は削除できません。')
            return redirect('company_member_list', company_id=company.id)
        
        # 削除
        invitation.delete()
        
        messages.success(request, '招待をキャンセルしました。')
        return redirect('company_member_list', company_id=company.id)

