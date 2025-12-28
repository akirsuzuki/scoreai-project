"""
Firm向けプランの初期データ投入コマンド

使用方法:
    docker compose exec django python manage.py init_firm_plans
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from scoreai.models import FirmPlan


class Command(BaseCommand):
    help = 'Firm向けプランの初期データを投入します'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Firm向けプランの初期データ投入を開始します..."))

        plans_data = [
            {
                'plan_type': 'free',
                'name': 'Freeプラン（無料・試用）',
                'description': '3ヶ月間の無料試用プラン。製品を体験してから有料プランへの移行を検討できます。',
                'monthly_price': 0,
                'yearly_price': 0,
                'yearly_discount_months': 0,
                'max_companies': 1,
                'max_ai_consultations_per_month': 10,
                'max_ocr_per_month': 5,
                'cloud_storage_google_drive': False,
                'cloud_storage_box': False,
                'cloud_storage_dropbox': False,
                'cloud_storage_onedrive': False,
                'report_basic': True,
                'report_advanced': False,
                'report_custom': False,
                'marketing_support': False,
                'marketing_support_seminar': 0,
                'marketing_support_offline': 0,
                'marketing_support_newsletter': False,
                'api_integration': False,
                'priority_support': False,
                'profile_page_enhanced': False,
                'stripe_price_id_monthly': '',
                'stripe_price_id_yearly': '',
                'is_active': True,
                'order': 1,
            },
            {
                'plan_type': 'starter',
                'name': 'Starterプラン',
                'description': '小規模事務所向けの基本プラン。基本的な財務管理ツールが必要な事務所に最適です。',
                'monthly_price': 9800,
                'yearly_price': 98000,
                'yearly_discount_months': 2,
                'max_companies': 5,
                'max_ai_consultations_per_month': 50,
                'max_ocr_per_month': 20,
                'cloud_storage_google_drive': True,
                'cloud_storage_box': False,
                'cloud_storage_dropbox': False,
                'cloud_storage_onedrive': False,
                'report_basic': True,
                'report_advanced': False,
                'report_custom': False,
                'marketing_support': False,
                'marketing_support_seminar': 0,
                'marketing_support_offline': 0,
                'marketing_support_newsletter': False,
                'api_integration': False,
                'priority_support': False,
                'profile_page_enhanced': False,
                'stripe_price_id_monthly': '',  # Stripe Dashboardで作成後に設定
                'stripe_price_id_yearly': '',  # Stripe Dashboardで作成後に設定
                'is_active': True,
                'order': 2,
            },
            {
                'plan_type': 'professional',
                'name': 'Professionalプラン',
                'description': '中規模事務所向けの本格プラン。複数のクライアントを管理し、本格的な財務分析が必要な事務所に最適です。',
                'monthly_price': 29800,
                'yearly_price': 298000,
                'yearly_discount_months': 2,
                'max_companies': 20,
                'max_ai_consultations_per_month': 200,
                'max_ocr_per_month': 100,
                'cloud_storage_google_drive': True,
                'cloud_storage_box': True,
                'cloud_storage_dropbox': True,
                'cloud_storage_onedrive': True,
                'report_basic': True,
                'report_advanced': True,
                'report_custom': False,
                'marketing_support': True,
                'marketing_support_seminar': 0,  # 案内配信のみ
                'marketing_support_offline': 0,
                'marketing_support_newsletter': False,
                'api_integration': True,
                'priority_support': True,
                'profile_page_enhanced': True,
                'stripe_price_id_monthly': '',  # Stripe Dashboardで作成後に設定
                'stripe_price_id_yearly': '',  # Stripe Dashboardで作成後に設定
                'is_active': True,
                'order': 3,
            },
            {
                'plan_type': 'enterprise',
                'name': 'Enterpriseプラン',
                'description': '大規模事務所向けの最上位プラン。積極的なクライアント獲得を目指す事務所に最適です。マーケティング支援も充実しています。',
                'monthly_price': 79800,
                'yearly_price': 798000,
                'yearly_discount_months': 2,
                'max_companies': 10,  # 基本10社、追加可能
                'max_ai_consultations_per_month': 500,  # 基本500回、追加可能
                'max_ocr_per_month': 250,  # 基本250回、追加可能
                'cloud_storage_google_drive': True,
                'cloud_storage_box': True,
                'cloud_storage_dropbox': True,
                'cloud_storage_onedrive': True,
                'report_basic': True,
                'report_advanced': True,
                'report_custom': True,
                'marketing_support': True,
                'marketing_support_seminar': 1,  # 年1回まで
                'marketing_support_offline': 1,  # 年1回まで
                'marketing_support_newsletter': True,
                'api_integration': True,
                'priority_support': True,
                'profile_page_enhanced': True,
                'stripe_price_id_monthly': '',  # Stripe Dashboardで作成後に設定
                'stripe_price_id_yearly': '',  # Stripe Dashboardで作成後に設定
                'is_active': True,
                'order': 4,
            },
        ]

        created_count = 0
        updated_count = 0

        for plan_data in plans_data:
            plan_type = plan_data.pop('plan_type')
            plan, created = FirmPlan.objects.update_or_create(
                plan_type=plan_type,
                defaults=plan_data
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"  ✓ {plan.name} を作成しました"))
                created_count += 1
            else:
                self.stdout.write(self.style.WARNING(f"  → {plan.name} を更新しました"))
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"\n初期データ投入が完了しました。"))
        self.stdout.write(self.style.SUCCESS(f"  作成: {created_count}件"))
        self.stdout.write(self.style.SUCCESS(f"  更新: {updated_count}件"))
        self.stdout.write(self.style.WARNING("\n注意: Stripe価格IDはStripe Dashboardで作成後、管理画面から設定してください。"))

