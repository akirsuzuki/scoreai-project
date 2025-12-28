"""
ブログカテゴリーの初期データを作成する管理コマンド
"""
from django.core.management.base import BaseCommand
from scoreai.models import BlogCategory


class Command(BaseCommand):
    help = 'ブログカテゴリーの初期データを作成します'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("ブログカテゴリーの初期化を開始します..."))
        self.stdout.write("=" * 60)
        
        categories = [
            {
                'name': 'お知らせ',
                'slug': 'announcement',
                'description': 'お知らせ・通知',
                'order': 1,
            },
            {
                'name': 'イベント',
                'slug': 'event',
                'description': 'イベント情報',
                'order': 2,
            },
            {
                'name': '機能追加',
                'slug': 'feature',
                'description': '新機能・機能追加のお知らせ',
                'order': 3,
            },
            {
                'name': 'プレスリリース',
                'slug': 'press-release',
                'description': 'プレスリリース',
                'order': 4,
            },
            {
                'name': 'アップデート',
                'slug': 'update',
                'description': 'システムアップデート情報',
                'order': 5,
            },
        ]
        
        for cat_data in categories:
            category, created = BlogCategory.objects.get_or_create(
                slug=cat_data['slug'],
                defaults=cat_data
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f"✓ カテゴリーを作成しました: {category.name}"))
            else:
                # 既存のカテゴリーを更新
                for key, value in cat_data.items():
                    setattr(category, key, value)
                category.save()
                self.stdout.write(self.style.WARNING(f"→ カテゴリーを更新しました: {category.name}"))
        
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("ブログカテゴリーの初期化が完了しました！"))
        self.stdout.write("=" * 60)

