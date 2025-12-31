"""
Google Gemini API ユーティリティ関数
"""
import google.generativeai as genai
from django.conf import settings
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def initialize_gemini() -> None:
    """Gemini APIを初期化"""
    if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEYが設定されていません。環境変数を確認してください。")
    genai.configure(api_key=settings.GEMINI_API_KEY)


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
    Gemini APIを使用してテキスト生成
    
    Args:
        prompt: ユーザーのプロンプト
        system_instruction: システム指示（オプション）
        model: 使用するGeminiモデル（Noneの場合は利用可能なモデルから自動選択）
        api_key: 使用するAPIキー（Noneの場合はSCOREのデフォルト）
        
    Returns:
        生成されたテキスト、エラー時はNone
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
                model_instance = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config=generation_config
                )
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
        
        # レスポンステキストの取得
        if hasattr(response, 'text') and response.text:
            return response.text
        elif hasattr(response, 'candidates') and response.candidates:
            # candidatesからテキストを取得
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                text_parts = [part.text for part in candidate.content.parts if hasattr(part, 'text')]
                if text_parts:
                    return ''.join(text_parts)
        
        # レスポンスが空の場合
        logger.warning("Gemini APIからのレスポンスが空です")
        logger.warning(f"Response object type: {type(response)}")
        logger.warning(f"Response attributes: {dir(response)}")
        if hasattr(response, 'prompt_feedback'):
            logger.warning(f"Prompt feedback: {response.prompt_feedback}")
        return None
            
    except ValueError as e:
        # APIキー関連のエラー
        logger.error(f"Gemini API configuration error: {e}", exc_info=True)
        raise ValueError(f"Gemini APIの設定エラー: {str(e)}")
    except Exception as e:
        logger.error(f"Gemini API error: {e}", exc_info=True)
        logger.error(f"Error type: {type(e).__name__}")
        raise


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

