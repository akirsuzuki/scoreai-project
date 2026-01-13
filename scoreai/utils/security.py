"""
セキュリティ関連のユーティリティ関数
"""
import logging
from typing import Optional, Tuple
from django.core.cache import cache
from django.http import HttpRequest
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


def get_client_ip(request: HttpRequest) -> str:
    """クライアントのIPアドレスを取得
    
    Args:
        request: HTTPリクエストオブジェクト
        
    Returns:
        クライアントのIPアドレス
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # プロキシ経由の場合、最初のIPアドレスを取得
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    return ip


def check_rate_limit(
    request: HttpRequest,
    key_prefix: str,
    max_attempts: int = 5,
    time_window: int = 300,  # 5分
    block_duration: int = 3600  # 1時間
) -> Tuple[bool, Optional[str]]:
    """レート制限をチェック
    
    Args:
        request: HTTPリクエストオブジェクト
        key_prefix: キャッシュキーのプレフィックス
        max_attempts: 許可される最大試行回数
        time_window: 時間ウィンドウ（秒）
        block_duration: ブロック期間（秒）
        
    Returns:
        (is_allowed, error_message)のタプル
        - is_allowed: リクエストが許可される場合True
        - error_message: ブロックされている場合のエラーメッセージ
    """
    ip_address = get_client_ip(request)
    
    # ブロックチェック
    block_key = f'{key_prefix}_block_{ip_address}'
    if cache.get(block_key):
        logger.warning(f"Rate limit blocked: IP {ip_address} is blocked for {key_prefix}")
        return False, f'短時間に多数のリクエストが検出されました。{block_duration // 60}分後に再度お試しください。'
    
    # 試行回数チェック
    attempt_key = f'{key_prefix}_attempts_{ip_address}'
    attempts = cache.get(attempt_key, 0)
    
    if attempts >= max_attempts:
        # ブロックを設定
        cache.set(block_key, True, block_duration)
        logger.warning(f"Rate limit exceeded: IP {ip_address} exceeded {max_attempts} attempts for {key_prefix}")
        return False, f'短時間に多数のリクエストが検出されました。{block_duration // 60}分後に再度お試しください。'
    
    # 試行回数をインクリメント
    cache.set(attempt_key, attempts + 1, time_window)
    
    return True, None


def reset_rate_limit(request: HttpRequest, key_prefix: str) -> None:
    """レート制限をリセット（成功時に呼び出す）
    
    Args:
        request: HTTPリクエストオブジェクト
        key_prefix: キャッシュキーのプレフィックス
    """
    ip_address = get_client_ip(request)
    attempt_key = f'{key_prefix}_attempts_{ip_address}'
    cache.delete(attempt_key)


def verify_recaptcha(token: str, secret_key: str) -> Tuple[bool, Optional[str]]:
    """reCAPTCHA v3トークンを検証
    
    Args:
        token: reCAPTCHAトークン
        secret_key: reCAPTCHAシークレットキー
        
    Returns:
        (is_valid, error_message)のタプル
        - is_valid: トークンが有効な場合True
        - error_message: エラーメッセージ（無効な場合）
    """
    import requests
    
    if not token:
        return False, 'reCAPTCHAトークンが提供されていません。'
    
    try:
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={
                'secret': secret_key,
                'response': token
            },
            timeout=5
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get('success'):
            score = result.get('score', 0)
            # スコアが0.5以上の場合のみ許可（v3の場合）
            if score >= 0.5:
                return True, None
            else:
                logger.warning(f"reCAPTCHA score too low: {score}")
                return False, 'reCAPTCHA検証に失敗しました。スコアが低すぎます。'
        else:
            error_codes = result.get('error-codes', [])
            logger.warning(f"reCAPTCHA verification failed: {error_codes}")
            return False, f'reCAPTCHA検証に失敗しました: {", ".join(error_codes)}'
            
    except requests.RequestException as e:
        logger.error(f"reCAPTCHA verification error: {e}", exc_info=True)
        return False, 'reCAPTCHA検証中にエラーが発生しました。'


def log_suspicious_activity(
    request: HttpRequest,
    activity_type: str,
    details: Optional[dict] = None
) -> None:
    """不審な活動をログに記録
    
    Args:
        request: HTTPリクエストオブジェクト
        activity_type: 活動タイプ（例: 'user_registration_attempt', 'rate_limit_exceeded'）
        details: 追加の詳細情報
    """
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
    
    log_data = {
        'ip_address': ip_address,
        'user_agent': user_agent,
        'activity_type': activity_type,
        'timestamp': timezone.now().isoformat(),
        'details': details or {}
    }
    
    logger.warning(f"Suspicious activity detected: {log_data}")
