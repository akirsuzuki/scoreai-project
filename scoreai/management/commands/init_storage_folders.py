"""
システム規定のフォルダ構造を初期化する管理コマンド
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from scoreai.models import CloudStorageSetting, DocumentFolder
from scoreai.utils.storage.google_drive import GoogleDriveAdapter
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'システム規定のフォルダ構造をクラウドストレージに作成します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='特定のユーザーIDのみ初期化する（指定しない場合は全ユーザー）',
        )
        parser.add_argument(
            '--storage-type',
            type=str,
            default='google_drive',
            help='ストレージタイプ（デフォルト: google_drive）',
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        storage_type = options.get('storage_type', 'google_drive')
        
        # 対象ユーザーを取得
        if user_id:
            users = User.objects.filter(id=user_id)
        else:
            users = User.objects.all()
        
        # ストレージ設定を取得
        storage_settings = CloudStorageSetting.objects.filter(
            user__in=users,
            storage_type=storage_type,
            is_active=True
        )
        
        if not storage_settings.exists():
            self.stdout.write(
                self.style.WARNING(
                    f'アクティブな{storage_type}設定が見つかりませんでした。'
                )
            )
            return
        
        # システム規定のフォルダ構造を取得
        folders = DocumentFolder.objects.filter(is_active=True).order_by('folder_type', 'order', 'subfolder_type')
        
        if not folders.exists():
            self.stdout.write(
                self.style.WARNING(
                    'システム規定のフォルダ構造が定義されていません。'
                )
            )
            return
        
        # 各ユーザーのストレージにフォルダを作成
        for storage_setting in storage_settings:
            self.stdout.write(
                f'ユーザー {storage_setting.user.username} の{storage_setting.get_storage_type_display()}を初期化中...'
            )
            
            try:
                # ストレージアダプターを初期化
                if storage_setting.storage_type == 'google_drive':
                    adapter = GoogleDriveAdapter(
                        user=storage_setting.user,
                        access_token=storage_setting.access_token,
                        refresh_token=storage_setting.refresh_token
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'ストレージタイプ {storage_setting.storage_type} はまだサポートされていません。'
                        )
                    )
                    continue
                
                # 「S-CoreAI」ルートフォルダを作成または取得
                if not storage_setting.root_folder_id:
                    try:
                        root_folder_info = adapter.get_or_create_folder('S-CoreAI', None)
                        storage_setting.root_folder_id = root_folder_info['id']
                        storage_setting.save()
                        self.stdout.write(
                            f'  ✓ ルートフォルダ「S-CoreAI」を作成しました (ID: {root_folder_info["id"]})'
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ✗ ルートフォルダ「S-CoreAI」の作成に失敗しました: {str(e)}'
                            )
                        )
                        logger.error(
                            f"Failed to create root folder 'S-CoreAI' for user {storage_setting.user.id}: {e}",
                            exc_info=True
                        )
                        continue
                
                # ルートフォルダIDを取得
                root_folder_id = storage_setting.root_folder_id
                
                # フォルダを作成
                created_count = 0
                for folder in folders:
                    try:
                        # フォルダパスを構築
                        folder_path = self._get_folder_path(folder)
                        
                        # フォルダを取得または作成
                        folder_info = adapter.get_or_create_folder(folder_path, root_folder_id)
                        
                        self.stdout.write(
                            f'  ✓ {folder_path} を作成しました (ID: {folder_info["id"]})'
                        )
                        created_count += 1
                        
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ✗ {folder_path} の作成に失敗しました: {str(e)}'
                            )
                        )
                        logger.error(
                            f"Failed to create folder {folder_path} for user {storage_setting.user.id}: {e}",
                            exc_info=True
                        )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'ユーザー {storage_setting.user.username} の初期化が完了しました。'
                        f'（{created_count}/{folders.count()} フォルダを作成）'
                    )
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'ユーザー {storage_setting.user.username} の初期化に失敗しました: {str(e)}'
                    )
                )
                logger.error(
                    f"Failed to initialize storage for user {storage_setting.user.id}: {e}",
                    exc_info=True
                )
    
    def _get_folder_path(self, folder):
        """フォルダパスを取得"""
        from scoreai.utils.document_naming import get_folder_path
        
        return get_folder_path(folder.folder_type, folder.subfolder_type)

