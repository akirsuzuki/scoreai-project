"""
月次利用状況リセットコマンド

毎月1日に実行して、前月の利用状況をリセットし、当月の利用状況レコードを作成します。
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from scoreai.models import Firm, FirmSubscription, FirmUsageTracking
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '月次利用状況をリセットします（毎月1日に実行）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際にはリセットせず、実行内容を表示するだけ',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='既にリセット済みでも強制的にリセットする',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        now = timezone.now()
        current_year = now.year
        current_month = now.month
        
        # 前月を計算
        if current_month == 1:
            previous_year = current_year - 1
            previous_month = 12
        else:
            previous_year = current_year
            previous_month = current_month - 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'月次リセット処理を開始します...\n'
                f'現在: {current_year}年{current_month}月\n'
                f'前月: {previous_year}年{previous_month}月'
            )
        )
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUNモード: 実際にはリセットしません'))
        
        # すべてのFirmを取得
        firms = Firm.objects.filter(
            subscription__isnull=False
        ).select_related('subscription')
        
        total_firms = firms.count()
        reset_count = 0
        created_count = 0
        error_count = 0
        
        for firm in firms:
            try:
                subscription = firm.subscription
                
                # 前月の利用状況を取得
                previous_usage = FirmUsageTracking.objects.filter(
                    firm=firm,
                    subscription=subscription,
                    year=previous_year,
                    month=previous_month,
                ).first()
                
                # 当月の利用状況を取得または作成
                current_usage, created = FirmUsageTracking.objects.get_or_create(
                    firm=firm,
                    subscription=subscription,
                    year=current_year,
                    month=current_month,
                    defaults={
                        'ai_consultation_count': 0,
                        'ocr_count': 0,
                        'is_reset': True,
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        f'  {firm.name}: 当月の利用状況レコードを作成しました'
                    )
                elif not current_usage.is_reset or force:
                    # リセット済みでない場合、または強制リセットの場合
                    if not dry_run:
                        with transaction.atomic():
                            current_usage.ai_consultation_count = 0
                            current_usage.ocr_count = 0
                            current_usage.is_reset = True
                            current_usage.save()
                        reset_count += 1
                        self.stdout.write(
                            f'  {firm.name}: 利用状況をリセットしました'
                        )
                    else:
                        self.stdout.write(
                            f'  {firm.name}: 利用状況をリセットします（DRY RUN）'
                        )
                else:
                    self.stdout.write(
                        f'  {firm.name}: 既にリセット済みです'
                    )
                
                # 前月の利用状況をログに記録
                if previous_usage:
                    self.stdout.write(
                        f'    前月の利用状況: '
                        f'AI相談 {previous_usage.ai_consultation_count}回, '
                        f'OCR {previous_usage.ocr_count}回'
                    )
                
            except Exception as e:
                error_count += 1
                logger.error(
                    f"Error resetting usage for firm {firm.id}: {e}",
                    exc_info=True
                )
                self.stdout.write(
                    self.style.ERROR(f'  {firm.name}: エラーが発生しました - {str(e)}')
                )
        
        # 結果を表示
        self.stdout.write(
            self.style.SUCCESS(
                f'\n処理完了:\n'
                f'  対象Firm数: {total_firms}\n'
                f'  新規作成: {created_count}\n'
                f'  リセット: {reset_count}\n'
                f'  エラー: {error_count}'
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\nDRY RUNモードでした。実際にリセットするには --dry-run を外してください。')
            )

