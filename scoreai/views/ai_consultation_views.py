"""
AI相談機能のビュー
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction
import json
import logging

from ..models import (
    AIConsultationType,
    AIConsultationScript,
    UserAIConsultationScript,
    AIConsultationHistory,
    Company,
    FiscalSummary_Year,
    FiscalSummary_Month,
    Debt,
)
from ..mixins import SelectedCompanyMixin
from ..utils.gemini import get_gemini_response
from ..utils.ai_consultation_data import get_consultation_data, build_consultation_prompt

logger = logging.getLogger(__name__)


class AIConsultationCenterView(SelectedCompanyMixin, TemplateView):
    """AI相談センターのトップページ"""
    template_name = 'scoreai/ai_consultation_center.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        consultation_types = AIConsultationType.objects.filter(is_active=True).order_by('order', 'name')
        context['consultation_types'] = consultation_types
        context['title'] = 'AI相談センター'
        return context


class AIConsultationView(SelectedCompanyMixin, TemplateView):
    """AI相談画面（チャット形式）"""
    template_name = 'scoreai/ai_consultation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        consultation_type_id = kwargs.get('consultation_type_id')
        consultation_type = get_object_or_404(
            AIConsultationType,
            id=consultation_type_id,
            is_active=True
        )
        
        # 相談履歴を取得（最新10件）
        histories = AIConsultationHistory.objects.filter(
            user=self.request.user,
            company=self.this_company,
            consultation_type=consultation_type
        ).order_by('-created_at')[:10]
        
        # 利用可能なデータを確認
        available_data = get_consultation_data(consultation_type, self.this_company)
        
        context['consultation_type'] = consultation_type
        context['histories'] = histories
        context['available_data'] = available_data
        context['title'] = f'{consultation_type.name}'
        return context


@method_decorator(csrf_exempt, name='dispatch')
class AIConsultationAPIView(SelectedCompanyMixin, View):
    """AI相談のAPI（AJAX用）"""
    
    def post(self, request, consultation_type_id):
        consultation_type = get_object_or_404(
            AIConsultationType,
            id=consultation_type_id,
            is_active=True
        )
        user_message = request.POST.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({
                'success': False,
                'error': 'メッセージを入力してください。'
            }, status=400)
        
        try:
            # データを収集
            company_data = get_consultation_data(consultation_type, self.this_company)
            
            # スクリプトを取得（ユーザー用 → システム用の順）
            user_script = UserAIConsultationScript.objects.filter(
                user=request.user,
                consultation_type=consultation_type,
                is_active=True,
                is_default=True
            ).first()
            
            system_script = None
            if not user_script:
                system_script = AIConsultationScript.objects.filter(
                    consultation_type=consultation_type,
                    is_active=True,
                    is_default=True
                ).first()
            
            # プロンプトを構築
            prompt, system_instruction = build_consultation_prompt(
                consultation_type,
                user_message,
                company_data,
                user_script if user_script else None
            )
            
            # AI応答を生成
            ai_response = get_gemini_response(
                prompt,
                system_instruction=system_instruction
            )
            
            if not ai_response:
                return JsonResponse({
                    'success': False,
                    'error': 'AI応答の生成に失敗しました。'
                }, status=500)
            
            # 履歴を保存
            history = AIConsultationHistory.objects.create(
                user=request.user,
                company=self.this_company,
                consultation_type=consultation_type,
                user_message=user_message,
                ai_response=ai_response,
                script_used=system_script if system_script else None,
                user_script_used=user_script if user_script else None,
                data_snapshot=company_data
            )
            
            return JsonResponse({
                'success': True,
                'response': ai_response,
                'history_id': history.id
            })
            
        except Exception as e:
            logger.error(f"AI consultation error: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'エラーが発生しました: {str(e)}'
            }, status=500)


class AIConsultationHistoryView(SelectedCompanyMixin, ListView):
    """AI相談履歴一覧"""
    model = AIConsultationHistory
    template_name = 'scoreai/ai_consultation_history.html'
    context_object_name = 'histories'
    paginate_by = 20
    
    def get_queryset(self):
        return AIConsultationHistory.objects.filter(
            user=self.request.user,
            company=self.this_company
        ).select_related('consultation_type').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'AI相談履歴'
        return context

