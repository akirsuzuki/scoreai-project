"""
Google Gemini API ユーティリティ関数
"""
import warnings

# FutureWarningを抑制（google-genaiへの移行が完了するまで）
warnings.filterwarnings('ignore', category=FutureWarning, module='google.generativeai')

try:
    import google.genai as genai
    GENAI_PACKAGE = 'google.genai'
except ImportError:
    # 後方互換性のため、古いパッケージも試す
    try:
        import google.generativeai as genai
        GENAI_PACKAGE = 'google.generativeai'
    except ImportError:
        raise ImportError(
            "Neither google.genai nor google.generativeai is installed. "
            "Please install google-genai: pip install google-genai"
        )

from django.conf import settings
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# 古いパッケージを使用している場合に警告を表示
if GENAI_PACKAGE == 'google.generativeai':
    logger.warning(
        "google.generativeai is deprecated. Please install google-genai package: pip install google-genai"
    )

# パッケージタイプを確認（グローバル変数が定義されていない場合のフォールバック）
if 'GENAI_PACKAGE' not in globals():
    try:
        import google.genai
        GENAI_PACKAGE = 'google.genai'
    except ImportError:
        GENAI_PACKAGE = 'google.generativeai'  # フォールバック


def initialize_gemini() -> None:
    """Gemini APIを初期化"""
    if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEYが設定されていません。環境変数を確認してください。")
    # google.genaiの場合は異なる初期化方法を使用する可能性がある
    if hasattr(genai, 'configure'):
        genai.configure(api_key=settings.GEMINI_API_KEY)
    elif hasattr(genai, 'Client'):
        # google.genaiの新しいAPI
        genai.Client(api_key=settings.GEMINI_API_KEY)


def get_available_models() -> list:
    """
    利用可能なGeminiモデルのリストを取得
    
    Returns:
        利用可能なモデル名のリスト
    """
    try:
        initialize_gemini()
        # 利用可能なモデルを取得
        models = genai.list_models()
        available = []
        for m in models:
            # generateContentをサポートしているモデルのみを取得
            if 'generateContent' in m.supported_generation_methods:
                available.append(m.name.replace('models/', ''))
        logger.info(f"Available models: {available}")
        return available
    except Exception as e:
        logger.warning(f"Failed to list models: {e}")
        # フォールバック: 一般的なモデル名のリスト
        return ["gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]


def get_gemini_response(
    prompt: str,
    system_instruction: Optional[str] = None,
    model: str = None,
    api_key: Optional[str] = None
) -> Optional[str]:
    """
    Gemini APIを使用してテキスト生成（後方互換性のため、テキストのみを返す）
    
    Args:
        prompt: ユーザーのプロンプト
        system_instruction: システム指示（オプション）
        model: 使用するGeminiモデル（Noneの場合は利用可能なモデルから自動選択）
        api_key: 使用するAPIキー（Noneの場合はSCOREのデフォルト）
        
    Returns:
        生成されたテキスト、エラー時はNone
    """
    result = get_gemini_response_with_tokens(prompt, system_instruction, model, api_key)
    if result:
        return result['text']
    return None


def get_gemini_response_with_tokens(
    prompt: str,
    system_instruction: Optional[str] = None,
    model: str = None,
    api_key: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Gemini APIを使用してテキスト生成（トークン数も返す）
    
    Args:
        prompt: ユーザーのプロンプト
        system_instruction: システム指示（オプション）
        model: 使用するGeminiモデル（Noneの場合は利用可能なモデルから自動選択）
        api_key: 使用するAPIキー（Noneの場合はSCOREのデフォルト）
        
    Returns:
        {'text': str, 'input_tokens': int, 'output_tokens': int, 'total_tokens': int} の辞書
        エラー時はNone
    """
    try:
        # APIキーが指定されている場合はそれを使用、そうでない場合はデフォルト
        if api_key:
            genai.configure(api_key=api_key)
        else:
            initialize_gemini()
        
        # モデルの設定
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,  # 回答文字数を増加（2048 → 8192）
        }
        
        # モデルを初期化（複数のモデル名を試す）
        # system_instructionはモデルによってサポートされていない場合があるため、プロンプトに含める
        if system_instruction:
            full_prompt = f"{system_instruction}\n\n{prompt}"
        else:
            full_prompt = prompt
        
        # 利用可能なモデルを取得
        if model:
            available_models = [model]
        else:
            available_models = get_available_models()
        
        # フォールバック用のモデルリストを追加
        fallback_models = ["gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
        for fallback in fallback_models:
            if fallback not in available_models:
                available_models.append(fallback)
        
        model_instance = None
        last_error = None
        
        for model_name in available_models:
            try:
                logger.info(f"Trying model: {model_name}")
                # google.genaiとgoogle.generativeaiで異なる可能性がある
                if hasattr(genai, 'GenerativeModel'):
                    model_instance = genai.GenerativeModel(
                        model_name=model_name,
                        generation_config=generation_config
                    )
                elif hasattr(genai, 'Client'):
                    # google.genaiの新しいAPI（将来の移行用）
                    client = genai.Client(api_key=api_key or settings.GEMINI_API_KEY)
                    model_instance = client.models.generate_content
                    # 注意: この部分は実際のgoogle.genai APIに合わせて調整が必要
                else:
                    raise ValueError("サポートされていないgenai APIです")
                # モデルの初期化が成功したら、そのモデルを使用
                logger.info(f"Successfully initialized model: {model_name}")
                break
            except Exception as e:
                logger.warning(f"Failed to initialize model {model_name}: {e}")
                last_error = e
                continue
        
        if model_instance is None:
            raise ValueError(f"利用可能なGeminiモデルが見つかりませんでした。最後のエラー: {last_error}")
        
        # レスポンスを生成
        response = model_instance.generate_content(full_prompt)
        
        # レスポンスの確認
        if not response:
            logger.warning("Gemini APIからのレスポンスがNoneです")
            return None
        
        # トークン数の取得
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0
        
        # usage_metadataからトークン数を取得
        if hasattr(response, 'usage_metadata'):
            usage = response.usage_metadata
            if hasattr(usage, 'prompt_token_count'):
                input_tokens = usage.prompt_token_count
            if hasattr(usage, 'candidates_token_count'):
                output_tokens = usage.candidates_token_count
            if hasattr(usage, 'total_token_count'):
                total_tokens = usage.total_token_count
            elif input_tokens > 0 or output_tokens > 0:
                total_tokens = input_tokens + output_tokens
        
        # レスポンステキストの取得
        text = None
        if hasattr(response, 'text') and response.text:
            text = response.text
        elif hasattr(response, 'candidates') and response.candidates:
            # candidatesからテキストを取得
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                text_parts = [part.text for part in candidate.content.parts if hasattr(part, 'text')]
                if text_parts:
                    text = ''.join(text_parts)
        
        if not text:
            # レスポンスが空の場合
            logger.warning("Gemini APIからのレスポンスが空です")
            logger.warning(f"Response object type: {type(response)}")
            logger.warning(f"Response attributes: {dir(response)}")
            if hasattr(response, 'prompt_feedback'):
                logger.warning(f"Prompt feedback: {response.prompt_feedback}")
            return None
        
        return {
            'text': text,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens,
        }
            
    except ValueError as e:
        # APIキー関連のエラー
        logger.error(f"Gemini API configuration error: {e}", exc_info=True)
        raise ValueError(f"Gemini APIの設定エラー: {str(e)}")
    except Exception as e:
        error_str = str(e)
        error_type = type(e).__name__
        
        # 429エラー（クォータ制限）の処理
        if '429' in error_str or 'quota' in error_str.lower() or 'Quota exceeded' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
            logger.error(f"Gemini API quota/rate limit exceeded: {error_type} - {e}")
            
            # エラーメッセージから詳細を抽出
            error_message = "Gemini APIの利用制限に達しました。\n\n"
            
            # プラン情報を確認（エラーメッセージから）
            if 'free_tier' in error_str.lower():
                error_message += "【無料プランの制限】\n"
                error_message += "無料プランの1日のリクエスト数やトークン数の制限に達している可能性があります。\n"
            else:
                error_message += "【Proプランでも制限に達している可能性があります】\n"
                error_message += "以下の可能性があります：\n"
                error_message += "1. 1分あたりのリクエスト数制限（RPM: Requests Per Minute）\n"
                error_message += "2. 1分あたりのトークン数制限（TPM: Tokens Per Minute）\n"
                error_message += "3. 1日あたりのリクエスト数制限\n"
                error_message += "4. APIキーが正しいプランに紐づいていない\n\n"
            
            error_message += "【対処方法】\n"
            error_message += "- しばらく時間をおいてから再度お試しください（通常1分程度）\n"
            error_message += "- APIキーの設定を確認してください\n"
            error_message += "- Google AI Studioで使用状況を確認してください: https://ai.dev/usage\n"
            error_message += "- 詳細: https://ai.google.dev/gemini-api/docs/rate-limits\n\n"
            error_message += f"【エラー詳細】\n{error_str[:500]}"  # 最初の500文字を表示
            
            raise ValueError(error_message)
        
        # その他のエラー
        logger.error(f"Gemini API error: {error_type} - {e}", exc_info=True)
        logger.error(f"Full error: {error_str}")
        raise ValueError(f"Gemini APIエラー ({error_type}): {str(e)[:500]}")


def get_financial_advice(
    user_message: str,
    debt_info: Optional[str] = None,
    financial_summary: Optional[str] = None
) -> Optional[str]:
    """
    財務アドバイスを取得
    
    Args:
        user_message: ユーザーの質問
        debt_info: 債務情報（オプション）
        financial_summary: 財務サマリー（オプション）
        
    Returns:
        財務アドバイス、エラー時はNone
        
    Raises:
        ValueError: APIキーが設定されていない場合
        Exception: その他のAPIエラー
    """
    system_instruction = """与えられた財務情報に基づいて、実践的で具体的なアドバイスを提供してください。
返答は日本語で、分かりやすく、専門的すぎない言葉で説明してください。"""
    
    # プロンプトを構築
    prompt_parts = []
    
    if debt_info:
        prompt_parts.append(f"【債務情報】\n{debt_info}\n")
    
    if financial_summary:
        prompt_parts.append(f"【財務サマリー】\n{financial_summary}\n")
    
    prompt_parts.append(f"【ユーザーの質問】\n{user_message}")
    
    prompt = "\n".join(prompt_parts)
    
    try:
        return get_gemini_response(prompt, system_instruction=system_instruction)
    except ValueError as e:
        # APIキー関連のエラーは再発生させる
        raise
    except Exception as e:
        logger.error(f"Financial advice generation error: {e}", exc_info=True)
        raise

