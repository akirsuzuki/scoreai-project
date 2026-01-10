"""
業界別相談室の初期データ投入コマンド
"""
from django.core.management.base import BaseCommand
from scoreai.models import IndustryCategory, IndustryConsultationType


class Command(BaseCommand):
    help = '業界別相談室の初期データを投入します'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('業界別相談室の初期データ投入を開始します...'))
        
        # 外食業界カテゴリーの作成
        food_service_category, created = IndustryCategory.objects.update_or_create(
            name='外食業界',
            defaults={
                'description': 'レストラン、居酒屋、カフェなど外食業界向けの専門相談室',
                'icon': 'ti ti-utensils',
                'order': 1,
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ 外食業界カテゴリーを作成しました'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ 外食業界カテゴリーを更新しました'))
        
        # 居酒屋出店計画作成の作成
        izakaya_plan_type, created = IndustryConsultationType.objects.update_or_create(
            industry_category=food_service_category,
            template_type='izakaya_plan',
            defaults={
                'name': '居酒屋出店計画作成',
                'description': '初期投資回収期間を計算し、銀行提出用の事業計画書を作成します。店のコンセプト、席数、営業時間、投資額などを入力することで、詳細な収支計画と回収期間を自動計算します。',
                'order': 1,
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ 居酒屋出店計画作成タイプを作成しました'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ 居酒屋出店計画作成タイプを更新しました'))
        
        self.stdout.write(self.style.SUCCESS('\n初期データ投入が完了しました。'))

