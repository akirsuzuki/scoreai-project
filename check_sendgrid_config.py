#!/usr/bin/env python3
"""
SendGrid設定値の簡単な確認スクリプト
Djangoをインポートせずに、設定ファイルから直接値を読み取ります
"""
import os
import sys
from pathlib import Path

# local_settings.pyを読み込む
BASE_DIR = Path(__file__).resolve().parent
local_settings_path = BASE_DIR / 'score' / 'local_settings.py'

print("=" * 60)
print("SendGrid設定値の確認")
print("=" * 60)
print()

if not local_settings_path.exists():
    print(f"❌ エラー: {local_settings_path} が見つかりません")
    sys.exit(1)

# local_settings.pyを実行して設定値を取得
try:
    # 環境変数から取得を試みる
    sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
    default_from_email = os.environ.get('DEFAULT_FROM_EMAIL')
    
    # local_settings.pyから取得
    if not sendgrid_api_key or not default_from_email:
        # local_settings.pyを読み込む
        import importlib.util
        spec = importlib.util.spec_from_file_location("local_settings", local_settings_path)
        local_settings = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(local_settings)
        
        if not sendgrid_api_key:
            sendgrid_api_key = getattr(local_settings, 'SENDGRID_API_KEY', None)
        if not default_from_email:
            default_from_email = getattr(local_settings, 'DEFAULT_FROM_EMAIL', None)
    
    print("【設定値】")
    print(f"EMAIL_HOST: smtp.sendgrid.net")
    print(f"EMAIL_PORT: 587")
    print(f"EMAIL_USE_TLS: True")
    print(f"EMAIL_HOST_USER: apikey")
    
    if sendgrid_api_key:
        masked_key = sendgrid_api_key[:8] + '...' + sendgrid_api_key[-4:] if len(sendgrid_api_key) > 12 else '***'
        print(f"SENDGRID_API_KEY: {masked_key} (マスク表示)")
        
        # APIキーの形式チェック
        if sendgrid_api_key.startswith('SG.'):
            print(f"  ✓ APIキーの形式は正しいです（'SG.'で始まる）")
        else:
            print(f"  ✗ APIキーの形式が不正です（'SG.'で始まる必要があります）")
        
        if 50 <= len(sendgrid_api_key) <= 100:
            print(f"  ✓ APIキーの長さは適切です（{len(sendgrid_api_key)}文字）")
        else:
            print(f"  ⚠ APIキーの長さが想定外です（{len(sendgrid_api_key)}文字、期待値: 50-100文字）")
    else:
        print("SENDGRID_API_KEY: 未設定")
    
    if default_from_email:
        print(f"DEFAULT_FROM_EMAIL: {default_from_email}")
    else:
        print("DEFAULT_FROM_EMAIL: 未設定")
    
    print()
    print("=" * 60)
    print("【次のステップ】")
    print("=" * 60)
    print()
    print("詳細な検証を行うには、Dockerコンテナ内で以下を実行してください:")
    print()
    print("  docker exec -it django python3 verify_sendgrid.py")
    print()
    print("または、Django管理コマンドを使用:")
    print()
    print("  docker exec -it django python manage.py test_sendgrid --check-only --to dummy@example.com")
    print()
    print("実際にメール送信をテストする場合:")
    print()
    print("  docker exec -it django python manage.py test_sendgrid --to <送信先メールアドレス>")
    print()
    
except Exception as e:
    print(f"❌ エラーが発生しました: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
