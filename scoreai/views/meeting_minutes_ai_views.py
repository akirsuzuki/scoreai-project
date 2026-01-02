"""
AI議事録生成機能のビュー
"""
from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView, TemplateView
from django.contrib import messages
from django.shortcuts import redirect
from django.db import transaction
import logging

from ..models import Firm, MeetingMinutes
from ..mixins import SelectedCompanyMixin, ErrorHandlingMixin
from ..forms import MeetingMinutesAIGenerateForm
from ..utils.plan_features import check_plan_feature_access
from ..utils.gemini import get_gemini_response
from ..utils.meeting_minutes_templates import (
    get_meeting_title,
    build_meeting_minutes_prompt,
    get_meeting_minutes_script
)

logger = logging.getLogger(__name__)


class MeetingMinutesAIGenerateView(SelectedCompanyMixin, LoginRequiredMixin, ErrorHandlingMixin, FormView):
    """AI議事録生成ビュー"""
    form_class = MeetingMinutesAIGenerateForm
    template_name = 'scoreai/meeting_minutes_ai_generate.html'
    
    def dispatch(self, request, *args, **kwargs):
        """プラン制限チェック"""
        # Firmを取得（SelectedCompanyMixinから）
        try:
            from ..models import UserFirm
            user_firm = UserFirm.objects.filter(
                user=request.user,
                is_selected=True,
                active=True
            ).select_related('firm', 'firm__subscription', 'firm__subscription__plan').first()
            
            if not user_firm:
                messages.error(request, 'Firmが選択されていません。')
                return redirect('index')
            
            firm = user_firm.firm
            
            # プラン制限チェック（starter以上）
            is_allowed, error_message = check_plan_feature_access(firm, required_plan_type='starter')
            if not is_allowed:
                messages.error(request, error_message)
                return redirect('index')
            
            self.firm = firm
        except Exception as e:
            logger.error(f"Error in dispatch: {e}", exc_info=True)
            messages.error(request, 'エラーが発生しました。')
            return redirect('index')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'AI議事録生成'
        context['show_title_card'] = False
        context['company'] = self.this_company
        return context
    
    def form_valid(self, form):
        """フォームが有効な場合の処理"""
        meeting_type = form.cleaned_data['meeting_type']
        meeting_category = form.cleaned_data['meeting_category']
        agenda = form.cleaned_data['agenda']
        additional_info = form.cleaned_data.get('additional_info', '')
        
        # スクリプトを取得（管理画面で設定されたものがあれば使用）
        script = get_meeting_minutes_script(meeting_type, meeting_category, agenda)
        
        # プロンプトを構築
        prompt, system_instruction = build_meeting_minutes_prompt(
            meeting_type=meeting_type,
            meeting_category=meeting_category,
            agenda=agenda,
            additional_info=additional_info,
            company_name=self.this_company.name,
            script=script
        )
        
        # AIで議事録を生成
        try:
            generated_text = get_gemini_response(prompt, system_instruction=system_instruction)
            
            if not generated_text:
                messages.error(self.request, '議事録の生成に失敗しました。もう一度お試しください。')
                return self.form_invalid(form)
            
            # セッションに生成結果を保存
            self.request.session['generated_minutes'] = generated_text
            self.request.session['meeting_type'] = meeting_type
            self.request.session['meeting_category'] = meeting_category
            self.request.session['agenda'] = agenda
            self.request.session['meeting_title'] = get_meeting_title(meeting_type, meeting_category, agenda)
            
            return redirect('meeting_minutes_ai_result')
            
        except Exception as e:
            logger.error(f"Error generating meeting minutes: {e}", exc_info=True)
            messages.error(self.request, f'議事録の生成中にエラーが発生しました: {str(e)}')
            return self.form_invalid(form)


class MeetingMinutesAIResultView(SelectedCompanyMixin, LoginRequiredMixin, ErrorHandlingMixin, TemplateView):
    """AI議事録生成結果表示ビュー"""
    template_name = 'scoreai/meeting_minutes_ai_result.html'
    
    def dispatch(self, request, *args, **kwargs):
        """プラン制限チェック"""
        try:
            from ..models import UserFirm
            user_firm = UserFirm.objects.filter(
                user=request.user,
                is_selected=True,
                active=True
            ).select_related('firm', 'firm__subscription', 'firm__subscription__plan').first()
            
            if not user_firm:
                messages.error(request, 'Firmが選択されていません。')
                return redirect('index')
            
            firm = user_firm.firm
            
            # プラン制限チェック（starter以上）
            is_allowed, error_message = check_plan_feature_access(firm, required_plan_type='starter')
            if not is_allowed:
                messages.error(request, error_message)
                return redirect('index')
            
            self.firm = firm
        except Exception as e:
            logger.error(f"Error in dispatch: {e}", exc_info=True)
            messages.error(request, 'エラーが発生しました。')
            return redirect('index')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        
        # セッションから生成結果を取得
        generated_minutes = self.request.session.get('generated_minutes')
        meeting_title = self.request.session.get('meeting_title', '議事録')
        
        if not generated_minutes:
            messages.error(self.request, '生成された議事録が見つかりません。最初からやり直してください。')
            return redirect('meeting_minutes_ai_generate')
        
        context['title'] = 'AI議事録生成'
        context['show_title_card'] = False
        context['company'] = self.this_company
        context['generated_minutes'] = generated_minutes
        context['meeting_title'] = meeting_title
        
        return context


class MeetingMinutesAISaveView(SelectedCompanyMixin, LoginRequiredMixin, ErrorHandlingMixin, TemplateView):
    """AI生成議事録の保存ビュー"""
    template_name = 'scoreai/meeting_minutes_ai_save.html'
    
    def dispatch(self, request, *args, **kwargs):
        """プラン制限チェック"""
        try:
            from ..models import UserFirm
            user_firm = UserFirm.objects.filter(
                user=request.user,
                is_selected=True,
                active=True
            ).select_related('firm', 'firm__subscription', 'firm__subscription__plan').first()
            
            if not user_firm:
                messages.error(request, 'Firmが選択されていません。')
                return redirect('index')
            
            firm = user_firm.firm
            
            # プラン制限チェック（starter以上）
            is_allowed, error_message = check_plan_feature_access(firm, required_plan_type='starter')
            if not is_allowed:
                messages.error(request, error_message)
                return redirect('index')
            
            self.firm = firm
        except Exception as e:
            logger.error(f"Error in dispatch: {e}", exc_info=True)
            messages.error(request, 'エラーが発生しました。')
            return redirect('index')
        
        return super().dispatch(request, *args, **kwargs)
    
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """議事録を保存"""
        # セッションから生成結果を取得
        generated_minutes = request.session.get('generated_minutes')
        meeting_title = request.session.get('meeting_title', '議事録')
        
        if not generated_minutes:
            messages.error(request, '生成された議事録が見つかりません。最初からやり直してください。')
            return redirect('meeting_minutes_ai_generate')
        
        # 会議日を取得（フォームから）
        meeting_date = request.POST.get('meeting_date')
        if not meeting_date:
            messages.error(request, '会議日を入力してください。')
            return redirect('meeting_minutes_ai_result')
        
        try:
            from datetime import datetime
            meeting_date_obj = datetime.strptime(meeting_date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, '会議日の形式が正しくありません。')
            return redirect('meeting_minutes_ai_result')
        
        # 議事録を保存
        meeting_minutes = MeetingMinutes.objects.create(
            company=self.this_company,
            created_by=request.user,
            meeting_date=meeting_date_obj,
            notes=generated_minutes
        )
        
        # セッションをクリア
        request.session.pop('generated_minutes', None)
        request.session.pop('meeting_type', None)
        request.session.pop('meeting_category', None)
        request.session.pop('agenda', None)
        request.session.pop('meeting_title', None)
        
        messages.success(request, '議事録を保存しました。')
        return redirect('meeting_minutes_detail', company_id=self.this_company.id, pk=meeting_minutes.pk)

