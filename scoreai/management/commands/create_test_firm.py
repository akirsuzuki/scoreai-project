"""
テスト用FirmとUserFirmを作成するコマンド

使用方法:
    docker compose exec django python manage.py create_test_firm
    docker compose exec django python manage.py create_test_firm --email your-email@example.com
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from scoreai.models import Firm, UserFirm

User = get_user_model()


class Command(BaseCommand):
    help = 'テスト用のFirmとUserFirmを作成します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Firmオーナーにするユーザーのメールアドレス（指定しない場合は最初のユーザーを使用）',
        )

    def handle(self, *args, **options):
        email = options.get('email')
        
        if email:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'ユーザーが見つかりません: {email}'))
                return
        else:
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR('ユーザーが存在しません。先にユーザーを作成してください。'))
                return
        
        self.stdout.write(f'ユーザー: {user.username} ({user.email}) を使用します')
        
        # 既存のFirmを確認
        existing_user_firm = UserFirm.objects.filter(
            user=user,
            is_owner=True,
            active=True
        ).first()
        
        if existing_user_firm:
            self.stdout.write(self.style.WARNING(f'既にFirmが存在します: {existing_user_firm.firm.name} (ID: {existing_user_firm.firm.id})'))
            self.stdout.write(self.style.SUCCESS(f'Firm ID: {existing_user_firm.firm.id}'))
            return
        
        # Firmを作成
        firm = Firm.objects.create(
            name=f'{user.username}事務所',
            owner=user
        )
        
        # UserFirmを作成（オーナー権限）
        user_firm = UserFirm.objects.create(
            user=user,
            firm=firm,
            is_owner=True,
            active=True,
            is_selected=True
        )
        
        self.stdout.write(self.style.SUCCESS(f'✓ Firmを作成しました: {firm.name}'))
        self.stdout.write(self.style.SUCCESS(f'✓ UserFirmを作成しました（オーナー権限）'))
        self.stdout.write(self.style.SUCCESS(f'\nFirm ID: {firm.id}'))
        self.stdout.write(self.style.SUCCESS(f'Firm名: {firm.name}'))
        self.stdout.write(self.style.SUCCESS(f'\nプラン一覧URL: http://localhost:8000/plans/{firm.id}/'))

