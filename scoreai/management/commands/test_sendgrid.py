"""
SendGrid設定の確認とテスト用の管理コマンド
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'SendGrid設定を確認し、テストメールを送信します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            help='テストメールの送信先メールアドレス',
            required=True
        )
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='設定のみを確認し、メールは送信しない',
        )

    def handle(self, *args, **options):
        to_email = options['to']
        check_only = options['check_only']

        self.stdout.write(self.style.SUCCESS('=== SendGrid設定確認 ===\n'))

        # 設定の確認
        self.stdout.write(f'EMAIL_BACKEND: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'EMAIL_HOST: {settings.EMAIL_HOST}')
        self.stdout.write(f'EMAIL_PORT: {settings.EMAIL_PORT}')
        self.stdout.write(f'EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}')
        self.stdout.write(f'EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}')
        
        # APIキーの確認（マスク表示）
        # settings.EMAIL_HOST_PASSWORDから取得（local_settings.pyまたは環境変数から）
        api_key = settings.EMAIL_HOST_PASSWORD
        if api_key:
            masked_key = api_key[:8] + '...' + api_key[-4:] if len(api_key) > 12 else '***'
            self.stdout.write(self.style.SUCCESS(f'SENDGRID_API_KEY: {masked_key} (設定済み)'))
        else:
            self.stdout.write(self.style.ERROR('SENDGRID_API_KEY: 未設定'))
        
        # 送信元メールアドレスの確認
        from_email = settings.DEFAULT_FROM_EMAIL
        self.stdout.write(f'DEFAULT_FROM_EMAIL: {from_email}')
        
        if check_only:
            self.stdout.write(self.style.SUCCESS('\n設定確認完了'))
            return

        # テストメールの送信
        self.stdout.write(self.style.SUCCESS('\n=== テストメール送信 ==='))
        self.stdout.write(f'送信先: {to_email}')
        self.stdout.write(f'送信元: {from_email}')

        try:
            subject = '[SCore AI] SendGrid設定テスト'
            message = f"""
これはSendGrid設定のテストメールです。

設定情報:
- EMAIL_HOST: {settings.EMAIL_HOST}
- EMAIL_PORT: {settings.EMAIL_PORT}
- EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}
- DEFAULT_FROM_EMAIL: {from_email}

このメールが届いていれば、SendGrid設定は正常に動作しています。
"""
            send_mail(
                subject,
                message,
                from_email,
                [to_email],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS('\n✓ テストメールを送信しました'))
            self.stdout.write(f'  {to_email} にメールが届くか確認してください')
        except Exception as e:
            error_msg = str(e)
            self.stdout.write(self.style.ERROR(f'\n✗ メール送信に失敗しました: {error_msg}'))
            
            # 送信元メールアドレス認証エラーの場合、詳細な案内を表示
            if 'verified Sender Identity' in error_msg or '550' in error_msg:
                self.stdout.write(self.style.WARNING('\n【重要】送信元メールアドレスの認証が必要です'))
                self.stdout.write(f'\n現在の送信元メールアドレス: {from_email}')
                self.stdout.write('\n認証手順:')
                self.stdout.write('1. SendGridダッシュボードにログイン')
                self.stdout.write('   https://app.sendgrid.com/')
                self.stdout.write('2. 「Settings」→「Sender Authentication」→「Single Sender Verification」を選択')
                self.stdout.write('3. 「Create New Sender」をクリック')
                self.stdout.write(f'4. From Email Address に「{from_email}」を入力')
                self.stdout.write('5. その他の必須項目を入力して「Create」をクリック')
                self.stdout.write('6. 送信された認証メールのリンクをクリックして認証を完了')
                self.stdout.write('\n詳細: https://sendgrid.com/docs/for-developers/sending-email/sender-identity/')
            
            self.stdout.write('\nトラブルシューティング:')
            self.stdout.write('1. SENDGRID_API_KEYが正しく設定されているか確認')
            self.stdout.write('2. 送信元メールアドレスがSendGridで認証されているか確認')
            self.stdout.write('3. SendGridダッシュボードの「Activity」で送信状況を確認')
            raise

