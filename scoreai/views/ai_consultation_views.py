"""
AI相談機能のビュー
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.http import JsonResponse
import json
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
        # 汎用相談タイプを取得
        consultation_types = AIConsultationType.objects.filter(is_active=True).order_by('order', 'name')
        context['consultation_types'] = consultation_types
        
        # 業界別相談室のカテゴリーを取得
        from ..models import IndustryCategory
        industry_categories = IndustryCategory.objects.filter(is_active=True).order_by('order', 'name')
        context['industry_categories'] = industry_categories
        
        context['title'] = 'AI相談センター'
        context['show_title_card'] = False  # タイトルカードを非表示（他のページと統一）
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
        
        # 利用可能なデータを確認（全てのデータタイプを個別に取得）
        from ..utils.ai_consultation_data import (
            get_fiscal_summary_data,
            get_debt_data,
            get_monthly_data,
            get_meeting_minutes_data,
            get_stakeholder_data,
            get_available_fiscal_summaries,
            get_available_monthly_summaries,
        )
        
        # 利用可能な決算書データと月次データの一覧を取得
        available_fiscal_summaries = get_available_fiscal_summaries(self.this_company)
        available_monthly_summaries = get_available_monthly_summaries(self.this_company)
        
        # 各データタイプの存在を確認
        has_fiscal_summary = bool(available_fiscal_summaries['actual'] or available_fiscal_summaries['budget'])
        has_debt_info = bool(get_debt_data(self.this_company))
        has_monthly_data = bool(available_monthly_summaries['actual'] or available_monthly_summaries['budget'])
        has_meeting_minutes = bool(get_meeting_minutes_data(self.this_company))
        has_stakeholder_name = bool(get_stakeholder_data(self.this_company))
        
        # データの詳細情報を取得（表示用）
        available_data = {
            'debt_info': get_debt_data(self.this_company) if has_debt_info else None,
            'meeting_minutes': get_meeting_minutes_data(self.this_company) if has_meeting_minutes else None,
            'stakeholder_name': get_stakeholder_data(self.this_company) if has_stakeholder_name else None,
        }
        
        # よくある質問を取得
        from ..models import AIConsultationFAQ
        faqs = AIConsultationFAQ.objects.filter(
            consultation_type=consultation_type,
            is_active=True
        ).order_by('order', 'question')
        
        # マイスクリプトを取得（選択中のCompanyに紐づくもののみ、かつ相談タイプが一致するもの）
        # 現在選択中のCompanyのもののみを表示
        user_scripts = UserAIConsultationScript.objects.filter(
            consultation_type=consultation_type,
            company=self.this_company,
            is_active=True
        ).select_related('user', 'company').order_by('-is_default', '-created_at')
        
        context['consultation_type'] = consultation_type
        context['histories'] = histories
        context['available_data'] = available_data
        context['available_fiscal_summaries'] = available_fiscal_summaries
        context['available_monthly_summaries'] = available_monthly_summaries
        context['has_fiscal_summary'] = has_fiscal_summary
        context['has_debt_info'] = has_debt_info
        context['has_monthly_data'] = has_monthly_data
        context['has_meeting_minutes'] = has_meeting_minutes
        context['has_stakeholder_name'] = has_stakeholder_name
        context['faqs'] = faqs
        context['user_scripts'] = user_scripts
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
        faq_id = request.POST.get('faq_id', '').strip()
        
        if not user_message:
            return JsonResponse({
                'success': False,
                'error': 'メッセージを入力してください。'
            }, status=400)
        
        try:
            # 選択されたデータタイプを取得
            selected_data_types = request.POST.getlist('selected_data_types')
            
            # 選択された決算書データを取得
            selected_fiscal_years = []
            for key in request.POST.keys():
                if key.startswith('fiscal_year_'):
                    # フォーマット: fiscal_year_2025_budget または fiscal_year_2025_actual
                    parts = key.replace('fiscal_year_', '').split('_')
                    if len(parts) == 2:
                        year = int(parts[0])
                        is_budget = parts[1] == 'budget'
                        selected_fiscal_years.append({'year': year, 'is_budget': is_budget})
            
            # 選択された月次データを取得
            selected_monthly_years = []
            for key in request.POST.keys():
                if key.startswith('monthly_year_'):
                    # フォーマット: monthly_year_2025_budget または monthly_year_2025_actual
                    parts = key.replace('monthly_year_', '').split('_')
                    if len(parts) == 2:
                        year = int(parts[0])
                        is_budget = parts[1] == 'budget'
                        selected_monthly_years.append({'year': year, 'is_budget': is_budget})
            
            # データを収集（選択されたデータタイプのみ）
            company_data = get_consultation_data(
                consultation_type, 
                self.this_company,
                selected_data_types=selected_data_types if selected_data_types else None,
                selected_fiscal_years=selected_fiscal_years if selected_fiscal_years else None,
                selected_monthly_years=selected_monthly_years if selected_monthly_years else None
            )
            
            # FAQのスクリプトを取得（指定されている場合）
            faq_script = None
            if faq_id:
                from ..models import AIConsultationFAQ
                faq = AIConsultationFAQ.objects.filter(
                    id=faq_id,
                    consultation_type=consultation_type,
                    is_active=True
                ).first()
                if faq and faq.script:
                    faq_script = faq.script
            
            # スクリプトを取得（FAQ用 → 選択されたスクリプト → ユーザー用 → システム用の順）
            user_script = None
            system_script = None
            
            # 選択されたスクリプトIDを取得
            selected_script_id = request.POST.get('script_id', '').strip()
            
            if not faq_script:
                # 選択されたスクリプトがある場合はそれを使用
                # 現在選択中のCompanyのもののみを対象
                if selected_script_id:
                    try:
                        user_script = UserAIConsultationScript.objects.filter(
                            id=selected_script_id,
                            consultation_type=consultation_type,
                            company=self.this_company,
                            is_active=True
                        ).first()
                    except (ValueError, UserAIConsultationScript.DoesNotExist):
                        pass
                
                # 選択されたスクリプトがない場合、デフォルトスクリプトを取得
                # 現在選択中のCompanyのもののみを対象
                if not user_script:
                    user_script = UserAIConsultationScript.objects.filter(
                        consultation_type=consultation_type,
                        company=self.this_company,
                        is_active=True
                    ).order_by('-is_default', '-created_at').first()
                
                # デフォルトスクリプトも見つからない場合はシステムスクリプトを使用
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
                user_script=user_script,
                faq_script=faq_script
            )
            
            # 使用するAPIキーを決定
            from ..utils.api_key_manager import get_api_key_for_ai_consultation, increment_api_count
            api_key, api_provider, source = get_api_key_for_ai_consultation(
                self.this_firm,
                self.this_company,
                request.user
            )
            
            # API利用回数をカウント
            from ..utils.usage_tracking import increment_company_api_count
            if source == 'score':
                increment_api_count(self.this_firm, user=request.user, company=self.this_company)
                # Company Userの場合、CompanyごとのAPI利用回数もカウント
                if request.user.is_company_user:
                    increment_company_api_count(self.this_company, self.this_firm, user=request.user)
            elif source == 'company':
                # CompanyのAPIキーを使用した場合もCompanyレベルでカウント
                if request.user.is_company_user:
                    increment_company_api_count(self.this_company, self.this_firm, user=request.user)
            # FirmのAPIキーを使用した場合はFirmレベルでカウントしない（既に上限を超えているため）
            
            # AI応答を生成（トークン数も取得）
            # 現在はGeminiのみ対応（OpenAI対応は後で追加可能）
            ai_response_text = None
            input_tokens = 0
            output_tokens = 0
            total_tokens = 0
            
            if api_provider == 'gemini':
                from ..utils.gemini import get_gemini_response_with_tokens
                try:
                    response_data = get_gemini_response_with_tokens(
                        prompt,
                        system_instruction=system_instruction,
                        api_key=api_key
                    )
                    if response_data:
                        ai_response_text = response_data['text']
                        input_tokens = response_data.get('input_tokens', 0)
                        output_tokens = response_data.get('output_tokens', 0)
                        total_tokens = response_data.get('total_tokens', 0) or (input_tokens + output_tokens)
                except ImportError as e:
                    logger.error(f"AI consultation error: {e}", exc_info=True)
                    return JsonResponse({
                        'success': False,
                        'error': 'google.genaiパッケージがインストールされていません。管理者にお問い合わせください。'
                    }, status=500)
            else:
                # OpenAI対応は後で実装
                logger.error(f"Unsupported API provider: {api_provider}")
                return JsonResponse({
                    'success': False,
                    'error': '現在サポートされていないAPIプロバイダーです。'
                }, status=500)
            
            if not ai_response_text:
                return JsonResponse({
                    'success': False,
                    'error': 'AI応答の生成に失敗しました。'
                }, status=500)
            
            # 利用状況をカウント（Company Userの場合のみ）
            # 現状は相談回数ベースで制限（トークン数は記録のみ）
            usage_incremented = increment_ai_consultation_count(self.this_firm, user=request.user)
            if not usage_incremented:
                return JsonResponse({
                    'success': False,
                    'error': 'AI相談の利用制限に達しています。プランをアップグレードするか、管理者にお問い合わせください。'
                }, status=403)
            
            # トークン数を累積（将来の制限用）
            if total_tokens > 0:
                from ..utils.usage_tracking import increment_ai_consultation_tokens
                increment_ai_consultation_tokens(self.this_firm, total_tokens, user=request.user)
            
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
                ai_response=ai_response_text,
                script_used=system_script if system_script else None,
                user_script_used=user_script if user_script else None,
                data_snapshot=serializable_data,
                input_tokens=input_tokens if input_tokens > 0 else None,
                output_tokens=output_tokens if output_tokens > 0 else None,
                total_tokens=total_tokens if total_tokens > 0 else None,
            )
            
            # JsonResponseに渡す前に、すべてのULIDを文字列に変換
            response_data = {
                'success': True,
                'response': ai_response_text,
                'history_id': str(history.id),  # ULIDを文字列に変換
                'tokens': {
                    'input': input_tokens,
                    'output': output_tokens,
                    'total': total_tokens,
                } if total_tokens > 0 else None
            }
            # 念のため、json.dumpsでシリアライズ可能か確認
            try:
                json.dumps(response_data, default=str, ensure_ascii=False)
            except (TypeError, ValueError) as e:
                logger.error(f"Failed to serialize response_data: {e}")
                # エラーが発生した場合は、make_json_serializableで処理
                response_data = make_json_serializable(response_data)
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"AI consultation error: {e}", exc_info=True)
            # エラーメッセージもULIDが含まれている可能性があるため、文字列に変換
            error_message = str(e)
            # ULIDオブジェクトが含まれている場合は、さらに処理
            try:
                json.dumps({'success': False, 'error': error_message}, default=str)
            except (TypeError, ValueError):
                error_message = f'エラーが発生しました: {type(e).__name__}'
            
            return JsonResponse({
                'success': False,
                'error': error_message
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

