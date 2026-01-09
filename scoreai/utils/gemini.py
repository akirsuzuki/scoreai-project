"""
Google Gemini API ユーティリティ関数

google.genaiパッケージを使用（google.generativeaiは非推奨）
"""
import logging
from typing import Optional, Dict, Any

from django.conf import settings

logger = logging.getLogger(__name__)

# 遅延インポート: google.genaiがインストールされていない場合でも
# モジュールのインポートは成功するようにする
genai = None
try:
    import google.genai as genai
except ImportError:
    logger.warning(
        "google.genai is not installed. "
        "Please install google-genai: pip install google-genai. "
        "Gemini API機能は使用できません。"
    )


def _check_genai_installed():
    """google.genaiがインストールされているかチェック"""
    if genai is None:
        raise ImportError(
            "google.genai is not installed. "
            "Please install google-genai: pip install google-genai"
        )


def initialize_gemini() -> None:
    """Gemini APIを初期化（環境変数でAPIキーを設定）"""
    _check_genai_installed()
    if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEYが設定されていません。環境変数を確認してください。")
    # google.genaiパッケージは環境変数GOOGLE_API_KEYまたはClientのapi_key引数で初期化
    # 環境変数が設定されていない場合は、後でClient作成時にapi_keyを指定
    import os
    if 'GOOGLE_API_KEY' not in os.environ:
        os.environ['GOOGLE_API_KEY'] = settings.GEMINI_API_KEY


def get_available_models() -> list:
    """
    利用可能なGeminiモデルのリストを取得
    
    Returns:
        利用可能なモデル名のリスト
    """
    _check_genai_installed()
    try:
        initialize_gemini()
        # Clientを作成してモデルリストを取得
        import os
        api_key = os.environ.get('GOOGLE_API_KEY') or settings.GEMINI_API_KEY
        client = genai.Client(api_key=api_key)
        
        # 利用可能なモデルを取得
        try:
            models = client.models.list()
            available = []
            for m in models:
                # モデル名を取得
                model_name = m.name if hasattr(m, 'name') else str(m)
                # モデル名から 'models/' プレフィックスを削除
                if model_name.startswith('models/'):
                    model_name = model_name.replace('models/', '')
                available.append(model_name)
            logger.info(f"Available models: {available}")
            return available if available else ["gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
        except Exception as e:
            logger.warning(f"Failed to list models using client: {e}")
            # フォールバック: デフォルトのモデルリストを返す
            return ["gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
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
    _check_genai_installed()
    try:
        # APIキーの設定
        if api_key:
            import os
            os.environ['GOOGLE_API_KEY'] = api_key
        else:
            initialize_gemini()
        
        # Clientを作成
        client = genai.Client(api_key=api_key or settings.GEMINI_API_KEY)
        
        # モデルの設定
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,  # 回答文字数を増加（2048 → 8192）
        }
        
        # プロンプトを準備
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
        
        response = None
        last_error = None
        
        for model_name in available_models:
            try:
                logger.info(f"Trying model: {model_name}")
                # google.genaiパッケージのClientを使用してコンテンツを生成
                response = client.models.generate_content(
                    model=model_name,
                    contents=full_prompt,
                    config=generation_config
                )
                
                # モデルの初期化が成功したら、そのモデルを使用
                logger.info(f"Successfully initialized model: {model_name}")
                break
            except Exception as e:
                logger.warning(f"Failed to initialize model {model_name}: {e}")
                last_error = e
                continue
        
        if response is None:
            raise ValueError(f"利用可能なGeminiモデルが見つかりませんでした。最後のエラー: {last_error}")
        
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

