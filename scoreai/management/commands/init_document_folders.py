"""
システム規定のフォルダ構造をデータベースに初期化する管理コマンド
"""
from django.core.management.base import BaseCommand
from scoreai.models import DocumentFolder


class Command(BaseCommand):
    help = 'システム規定のフォルダ構造をデータベースに初期化します'

    def handle(self, *args, **options):
        # フォルダ構造の定義
        folders = [
            # 決算書
            {
                'folder_type': 'financial_statement',
                'subfolder_type': '',
                'name': '決算書',
                'order': 1,
            },
            # 試算表
            {
                'folder_type': 'trial_balance',
                'subfolder_type': '',
                'name': '試算表',
                'order': 2,
            },
            {
                'folder_type': 'trial_balance',
                'subfolder_type': 'balance_sheet',
                'name': '貸借対照表',
                'order': 3,
            },
            {
                'folder_type': 'trial_balance',
                'subfolder_type': 'profit_loss',
                'name': '損益計算書',
                'order': 4,
            },
            {
                'folder_type': 'trial_balance',
                'subfolder_type': 'monthly_pl',
                'name': '月次推移損益計算書',
                'order': 5,
            },
            {
                'folder_type': 'trial_balance',
                'subfolder_type': 'department_pl',
                'name': '部門別損益計算書',
                'order': 6,
            },
            # 金銭消費貸借契約書
            {
                'folder_type': 'loan_contract',
                'subfolder_type': '',
                'name': '金銭消費貸借契約書',
                'order': 7,
            },
            # 契約書
            {
                'folder_type': 'contract',
                'subfolder_type': '',
                'name': '契約書',
                'order': 8,
            },
            {
                'folder_type': 'contract',
                'subfolder_type': 'lease',
                'name': 'リース契約書',
                'order': 9,
            },
            {
                'folder_type': 'contract',
                'subfolder_type': 'sales',
                'name': '商品売買契約',
                'order': 10,
            },
            {
                'folder_type': 'contract',
                'subfolder_type': 'rental',
                'name': '賃貸借契約',
                'order': 11,
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for folder_data in folders:
            folder, created = DocumentFolder.objects.update_or_create(
                folder_type=folder_data['folder_type'],
                subfolder_type=folder_data.get('subfolder_type', ''),
                defaults={
                    'name': folder_data['name'],
                    'order': folder_data['order'],
                    'is_active': True,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {folder_data["name"]} を作成しました')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {folder_data["name"]} を更新しました')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n初期化が完了しました。'
                f'（作成: {created_count}, 更新: {updated_count}）'
            )
        )

