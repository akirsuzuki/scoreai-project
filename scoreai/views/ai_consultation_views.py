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
from django_ulid.models import ulid

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
from ..utils.usage_tracking import increment_ai_consultation_count

logger = logging.getLogger(__name__)


def make_json_serializable(obj):
    """
    ULIDやその他のJSONシリアライズできないオブジェクトを文字列に変換
    再帰的に処理して、ネストされたULIDも変換
    """
    # 基本的な型はそのまま返す
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    
    # 辞書の場合は再帰的に処理
    if isinstance(obj, dict):
        return {key: make_json_serializable(value) for key, value in obj.items()}
    
    # リストやタプルの場合も再帰的に処理
    if isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    
    # ULID型のチェック
    # django_ulidのULID型をチェック
    try:
        # 型名でチェック
        type_name = type(obj).__name__
        module_name = type(obj).__module__
        
        # ULID型の可能性がある場合
        if 'ulid' in module_name.lower() or type_name == 'ULID':
            return str(obj)
    except (AttributeError, TypeError):
        pass
    
    # その他のオブジェクトは文字列に変換を試みる
    # これにより、ULIDやその他のシリアライズできないオブジェクトも文字列に変換される
    try:
        return str(obj)
    except (TypeError, ValueError):
        return None


class AIConsultationCenterView(SelectedCompanyMixin, TemplateView):
    """AI相談センターのトップページ"""
    template_name = 'scoreai/ai_consultation_center.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        consultation_types = AIConsultationType.objects.filter(is_active=True).order_by('order', 'name')
        context['consultation_types'] = consultation_types
        context['title'] = 'AI相談センター'
        # 第一レベルなのでタイトルカードを表示
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
        context['show_title_card'] = False  # タイトルカードを非表示（テンプレートで独自に表示）
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
            
            # 利用状況をカウント
            usage_incremented = increment_ai_consultation_count(self.this_firm)
            if not usage_incremented:
                return JsonResponse({
                    'success': False,
                    'error': 'AI相談の利用制限に達しています。プランをアップグレードするか、管理者にお問い合わせください。'
                }, status=403)
            
            # 履歴を保存（ULIDを文字列に変換）
            # json.dumps()とjson.loads()を使って、ULIDを確実に文字列に変換
            # default=strにより、すべてのシリアライズできないオブジェクト（ULID含む）が文字列に変換される
            try:
                # まずmake_json_serializableで再帰的に処理
                serializable_data = make_json_serializable(company_data)
                # その後、json.dumps()とjson.loads()で確実にシリアライズ可能な形式に変換
                serializable_data = json.loads(json.dumps(serializable_data, default=str, ensure_ascii=False))
            except (TypeError, ValueError) as e:
                logger.warning(f"Failed to serialize with make_json_serializable, using json.dumps default=str: {e}")
                # フォールバック: json.dumps()のdefault=strを使用
                try:
                    serializable_data = json.loads(json.dumps(company_data, default=str, ensure_ascii=False))
                except (TypeError, ValueError) as e2:
                    logger.error(f"Failed to serialize company_data even with json.dumps default=str: {e2}")
                    # 最終手段: 空の辞書を保存
                    serializable_data = {}
            
            history = AIConsultationHistory.objects.create(
                user=request.user,
                company=self.this_company,
                consultation_type=consultation_type,
                user_message=user_message,
                ai_response=ai_response,
                script_used=system_script if system_script else None,
                user_script_used=user_script if user_script else None,
                data_snapshot=serializable_data
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
        context['show_title_card'] = False  # タイトルカードを非表示（テンプレートで独自に表示）
        return context

