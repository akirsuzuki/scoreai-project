"""
Firmメンバー管理機能のビュー
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

from ..models import Firm, UserFirm, User, FirmInvitation
from ..mixins import ErrorHandlingMixin
from ..forms import FirmMemberInviteForm

logger = logging.getLogger(__name__)


class FirmMemberListView(LoginRequiredMixin, ErrorHandlingMixin, ListView):
    """Firmメンバー一覧ビュー"""
    model = UserFirm
    template_name = 'scoreai/firm_member_list.html'
    context_object_name = 'members'
    
    def dispatch(self, request, *args, **kwargs):
        """Firmのオーナーであることを確認"""
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        firm_id = kwargs.get('firm_id')
        firm = get_object_or_404(Firm, id=firm_id)
        
        # オーナーであることを確認
        user_firm = UserFirm.objects.filter(
            user=request.user,
            firm=firm,
            is_owner=True,
            active=True
        ).first()
        
        if not user_firm:
            messages.error(request, 'このFirmのオーナー権限がありません。')
            return redirect('index')
        
        self.firm = firm
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        """Firmに所属するメンバーを取得"""
        return UserFirm.objects.filter(
            firm=self.firm
        ).select_related('user').order_by('-is_owner', 'user__username')
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'スタッフ管理'
        context['show_title_card'] = False
        context['firm'] = self.firm
        
        # 統計情報
        context['total_members'] = self.get_queryset().count()
        context['active_members'] = self.get_queryset().filter(active=True).count()
        context['owner_count'] = self.get_queryset().filter(is_owner=True).count()
        
        # 招待中のメンバーを取得
        context['pending_invitations'] = FirmInvitation.objects.filter(
            firm=self.firm,
            is_accepted=False
        ).select_related('invited_by').order_by('-invited_at')
        
        return context


class FirmMemberInviteView(LoginRequiredMixin, ErrorHandlingMixin, FormView):
    """Firmメンバー招待ビュー"""
    template_name = 'scoreai/firm_member_invite.html'
    form_class = FirmMemberInviteForm
    
    def dispatch(self, request, *args, **kwargs):
        """Firmのオーナーであることを確認"""
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        firm_id = kwargs.get('firm_id')
        firm = get_object_or_404(Firm, id=firm_id)
        
        # オーナーであることを確認
        user_firm = UserFirm.objects.filter(
            user=request.user,
            firm=firm,
            is_owner=True,
            active=True
        ).first()
        
        if not user_firm:
            messages.error(request, 'このFirmのオーナー権限がありません。')
            return redirect('index')
        
        self.firm = firm
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'スタッフ管理'
        context['show_title_card'] = False
        context['firm'] = self.firm
        return context
    
    def form_valid(self, form):
        """フォームが有効な場合の処理"""
        email = form.cleaned_data['email']
        is_owner = form.cleaned_data.get('is_owner', False)
        
        # 既存のユーザーを確認
        try:
            user = User.objects.get(email=email)
            
            # 既にFirmに所属しているか確認
            existing_member = UserFirm.objects.filter(
                user=user,
                firm=self.firm
            ).first()
            
            if existing_member:
                if existing_member.active:
                    messages.warning(self.request, f'{email} は既にこのFirmのメンバーです。')
                else:
                    # 非アクティブなメンバーの場合は再アクティブ化
                    existing_member.active = True
                    existing_member.is_owner = is_owner
                    existing_member.save()
                    messages.success(self.request, f'{email} をメンバーとして再追加しました。')
            else:
                # 新規メンバーとして追加
                UserFirm.objects.create(
                    user=user,
                    firm=self.firm,
                    active=True,
                    is_owner=is_owner,
                    is_selected=False
                )
                messages.success(self.request, f'{email} をメンバーとして追加しました。')
            
            # メール送信
            self._send_invitation_email(user, is_owner)
            
        except User.DoesNotExist:
            # ユーザーが存在しない場合は招待レコードを作成
            # 既存の招待を確認
            existing_invitation = FirmInvitation.objects.filter(
                firm=self.firm,
                email=email,
                is_accepted=False
            ).first()
            
            if existing_invitation:
                messages.warning(self.request, f'{email} には既に招待が送信されています。')
            else:
                # 新規招待レコードを作成
                invitation = FirmInvitation.objects.create(
                    firm=self.firm,
                    email=email,
                    invited_by=self.request.user,
                    is_owner=is_owner
                )
                
                # 招待メールを送信
                self._send_invitation_email_to_new_user(email, is_owner)
                
                # 通知を作成
                from ..utils.notifications import notify_member_invited
                notify_member_invited(self.firm, email, self.request.user.username)
                
                messages.success(self.request, f'{email} に招待メールを送信しました。')
        
        return redirect('firm_member_list', firm_id=self.firm.id)
    
    def _send_invitation_email(self, user, is_owner):
        """既存ユーザーへの招待メールを送信"""
        try:
            role = 'オーナー' if is_owner else 'メンバー'
            subject = f'{self.firm.name} への招待'
            
            message = f"""
{user.username} さん

{self.firm.name} の{role}として招待されました。

以下のリンクからログインして、Firmに参加してください：
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
            logger.info(f"Invitation email sent to {user.email} for firm {self.firm.id}")
        except Exception as e:
            logger.error(f"Error sending invitation email: {e}", exc_info=True)
            messages.warning(self.request, 'メールの送信に失敗しましたが、メンバーは追加されました。')
    
    def _send_invitation_email_to_new_user(self, email, is_owner):
        """新規ユーザーへの招待メールを送信"""
        try:
            role = 'オーナー' if is_owner else 'メンバー'
            subject = f'{self.firm.name} への招待'
            
            message = f"""
{email} 様

{self.firm.name} の{role}として招待されました。

以下のリンクからアカウントを作成して、Firmに参加してください：
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
            logger.info(f"Invitation email sent to {email} for firm {self.firm.id}")
        except Exception as e:
            logger.error(f"Error sending invitation email: {e}", exc_info=True)
            messages.warning(self.request, 'メールの送信に失敗しましたが、招待は記録されました。')


class FirmMemberUpdateView(LoginRequiredMixin, ErrorHandlingMixin, BaseView):
    """Firmメンバー更新ビュー（権限変更、アクティブ/非アクティブ）"""
    
    @transaction.atomic
    def post(self, request, firm_id, member_id):
        """メンバー情報を更新"""
        firm = get_object_or_404(Firm, id=firm_id)
        
        # オーナーであることを確認
        user_firm = UserFirm.objects.filter(
            user=request.user,
            firm=firm,
            is_owner=True,
            active=True
        ).first()
        
        if not user_firm:
            messages.error(request, 'このFirmのオーナー権限がありません。')
            return redirect('index')
        
        action = request.POST.get('action')
        
        # 招待キャンセルの場合はFirmInvitationを取得
        if action == 'cancel_invitation':
            invitation = get_object_or_404(FirmInvitation, id=member_id, firm=firm, is_accepted=False)
            email = invitation.email
            invitation.delete()
            messages.success(request, f'{email} への招待をキャンセルしました。')
            return redirect('firm_member_list', firm_id=firm_id)
        
        # その他のアクションはUserFirmを取得
        member = get_object_or_404(UserFirm, id=member_id, firm=firm)
        
        if action == 'toggle_owner':
            # オーナー権限の切り替え
            # 最後のオーナーは削除できない
            owner_count = UserFirm.objects.filter(
                firm=firm,
                is_owner=True,
                active=True
            ).count()
            
            if member.is_owner and owner_count <= 1:
                messages.error(request, '最後のオーナーは削除できません。')
            else:
                member.is_owner = not member.is_owner
                member.save()
                role = 'オーナー' if member.is_owner else 'メンバー'
                messages.success(request, f'{member.user.username} を{role}に変更しました。')
        
        elif action == 'toggle_active':
            # アクティブ/非アクティブの切り替え
            # 最後のアクティブなオーナーは非アクティブにできない
            if member.is_owner and member.active:
                active_owner_count = UserFirm.objects.filter(
                    firm=firm,
                    is_owner=True,
                    active=True
                ).count()
                
                if active_owner_count <= 1:
                    messages.error(request, '最後のアクティブなオーナーは非アクティブにできません。')
                    return redirect('firm_member_list', firm_id=firm_id)
            
            member.active = not member.active
            member.save()
            status = 'アクティブ' if member.active else '非アクティブ'
            messages.success(request, f'{member.user.username} を{status}に変更しました。')
        
        elif action == 'remove':
            # メンバーの削除
            # 最後のオーナーは削除できない
            if member.is_owner:
                owner_count = UserFirm.objects.filter(
                    firm=firm,
                    is_owner=True,
                    active=True
                ).count()
                
                if owner_count <= 1:
                    messages.error(request, '最後のオーナーは削除できません。')
                    return redirect('firm_member_list', firm_id=firm_id)
            
            username = member.user.username
            member.delete()
            messages.success(request, f'{username} をメンバーから削除しました。')
        
        return redirect('firm_member_list', firm_id=firm_id)


class FirmInvitationCancelView(LoginRequiredMixin, ErrorHandlingMixin, BaseView):
    """Firm招待キャンセルビュー"""
    
    @transaction.atomic
    def post(self, request, firm_id, invitation_id):
        """招待をキャンセル"""
        firm = get_object_or_404(Firm, id=firm_id)
        
        # オーナーであることを確認
        user_firm = UserFirm.objects.filter(
            user=request.user,
            firm=firm,
            is_owner=True,
            active=True
        ).first()
        
        if not user_firm:
            messages.error(request, 'このFirmのオーナー権限がありません。')
            return redirect('index')
        
        # 招待を取得
        invitation = get_object_or_404(FirmInvitation, id=invitation_id, firm=firm, is_accepted=False)
        email = invitation.email
        invitation.delete()
        
        messages.success(request, f'{email} への招待をキャンセルしました。')
        return redirect('firm_member_list', firm_id=firm_id)

