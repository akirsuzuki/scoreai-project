#!/usr/bin/env python3
"""
SendGrid設定の検証スクリプト
設定値の確認とAPIキーの形式チェックを行います
"""
import os
import sys
import re
from pathlib import Path

# requestsモジュールのインポート（オプション）
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("警告: requestsモジュールが見つかりません。API検証はスキップされます。")
    print("      Dockerコンテナ内で実行するか、pip install requests を実行してください。\n")

# プロジェクトルートをパスに追加
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Django設定を読み込む前に環境変数を設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'score.settings')

# Django設定をインポート
import django
django.setup()

from django.conf import settings

def check_api_key_format(api_key):
    """APIキーの形式をチェック"""
    if not api_key:
        return False, "APIキーが設定されていません"
    
    # SendGrid APIキーは通常 "SG." で始まり、約70文字
    if not api_key.startswith('SG.'):
        return False, "APIキーは 'SG.' で始まる必要があります"
    
    if len(api_key) < 50 or len(api_key) > 100:
        return False, f"APIキーの長さが不正です（現在: {len(api_key)}文字、期待値: 50-100文字）"
    
    return True, "APIキーの形式は正しいです"

def verify_sendgrid_api(api_key):
    """SendGrid APIを直接呼び出して検証"""
    if not HAS_REQUESTS:
        return None, "requestsモジュールがインストールされていません（スキップ）"
    
    if not api_key:
        return False, "APIキーが設定されていません"
    
    # SendGrid API v3でユーザー情報を取得して検証
    url = "https://api.sendgrid.com/v3/user/profile"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return True, f"APIキーは有効です（ユーザー: {data.get('username', 'N/A')}）"
        elif response.status_code == 401:
            return False, "APIキーが無効です（認証に失敗しました）"
        else:
            return False, f"APIキーの検証に失敗しました（ステータスコード: {response.status_code}）"
    except requests.exceptions.RequestException as e:
        return False, f"APIキーの検証中にエラーが発生しました: {str(e)}"

def check_sender_verification(api_key, from_email):
    """送信元メールアドレスの認証状態を確認"""
    if not HAS_REQUESTS:
        return None, "requestsモジュールがインストールされていません（スキップ）"
    
    if not api_key or not from_email:
        return False, "APIキーまたは送信元メールアドレスが設定されていません"
    
    url = "https://api.sendgrid.com/v3/verified_senders"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            verified_senders = response.json().get('results', [])
            for sender in verified_senders:
                if sender.get('from', {}).get('email') == from_email:
                    verified = sender.get('verified', False)
                    if verified:
                        return True, f"送信元メールアドレス '{from_email}' は認証済みです"
                    else:
                        return False, f"送信元メールアドレス '{from_email}' は未認証です"
            return False, f"送信元メールアドレス '{from_email}' が見つかりません（SendGridで認証が必要です）"
        else:
            return False, f"送信元メールアドレスの確認に失敗しました（ステータスコード: {response.status_code}）"
    except requests.exceptions.RequestException as e:
        return False, f"送信元メールアドレスの確認中にエラーが発生しました: {str(e)}"

def main():
    print("=" * 60)
    print("SendGrid設定検証")
    print("=" * 60)
    print()
    
    # 設定値の確認
    print("【設定値の確認】")
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print()
    
    # APIキーの取得
    api_key = settings.EMAIL_HOST_PASSWORD
    if api_key:
        masked_key = api_key[:8] + '...' + api_key[-4:] if len(api_key) > 12 else '***'
        print(f"SENDGRID_API_KEY: {masked_key} (マスク表示)")
    else:
        print("SENDGRID_API_KEY: 未設定")
        print()
        print("❌ エラー: APIキーが設定されていません")
        print("   local_settings.py または環境変数 SENDGRID_API_KEY を設定してください")
        return 1
    print()
    
    # APIキーの形式チェック
    print("【APIキーの形式チェック】")
    is_valid_format, format_msg = check_api_key_format(api_key)
    if is_valid_format:
        print(f"✓ {format_msg}")
    else:
        print(f"✗ {format_msg}")
        return 1
    print()
    
    # SendGrid APIでの検証
    print("【SendGrid APIでの検証】")
    if HAS_REQUESTS:
        print("APIキーをSendGrid APIで検証しています...")
        is_valid_api, api_msg = verify_sendgrid_api(api_key)
        if is_valid_api is None:
            print(f"⚠ {api_msg}")
        elif is_valid_api:
            print(f"✓ {api_msg}")
        else:
            print(f"✗ {api_msg}")
            print()
            print("【トラブルシューティング】")
            print("1. SendGridダッシュボードでAPIキーが有効か確認してください")
            print("   https://app.sendgrid.com/settings/api_keys")
            print("2. APIキーが削除されていないか確認してください")
            print("3. APIキーに 'Mail Send' 権限があるか確認してください")
            return 1
    else:
        print("⚠ requestsモジュールがないため、API検証をスキップします")
        print("   Dockerコンテナ内で実行するか、pip install requests を実行してください")
    print()
    
    # 送信元メールアドレスの認証確認
    from_email = settings.DEFAULT_FROM_EMAIL
    if from_email:
        print("【送信元メールアドレスの認証確認】")
        print(f"送信元メールアドレス: {from_email}")
        if HAS_REQUESTS:
            print("認証状態を確認しています...")
            is_verified, verify_msg = check_sender_verification(api_key, from_email)
            if is_verified is None:
                print(f"⚠ {verify_msg}")
            elif is_verified:
                print(f"✓ {verify_msg}")
            else:
                print(f"✗ {verify_msg}")
                print()
                print("【認証手順】")
                print("1. SendGridダッシュボードにログイン")
                print("   https://app.sendgrid.com/")
                print("2. 「Settings」→「Sender Authentication」→「Single Sender Verification」を選択")
                print("3. 「Create New Sender」をクリック")
                print(f"4. From Email Address に「{from_email}」を入力")
                print("5. その他の必須項目を入力して「Create」をクリック")
                print("6. 送信された認証メールのリンクをクリックして認証を完了")
                print()
                print("詳細: https://sendgrid.com/docs/for-developers/sending-email/sender-identity/")
                return 1
        else:
            print("⚠ requestsモジュールがないため、認証確認をスキップします")
            print("   送信元メールアドレスの認証が必要です（上記の認証手順を参照）")
    print()
    
    print("=" * 60)
    print("✓ すべての検証が完了しました")
    print("=" * 60)
    print()
    print("【次のステップ】")
    print("実際にメール送信をテストするには、以下のコマンドを実行してください:")
    print(f"  python manage.py test_sendgrid --to <送信先メールアドレス>")
    print()
    
    return 0

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n検証を中断しました")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
