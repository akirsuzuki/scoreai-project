"""
居酒屋出店計画のテスト用コマンド
実際に計画を作成し、計算結果を確認します
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from scoreai.models import Company, IzakayaPlan
from scoreai.services.izakaya_plan_service import IzakayaPlanService
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = '居酒屋出店計画を作成し、計算結果を確認します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=str,
            help='会社ID（指定しない場合は最初の会社を使用）',
        )
        parser.add_argument(
            '--user-email',
            type=str,
            help='ユーザーメールアドレス（指定しない場合は最初のユーザーを使用）',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== 居酒屋出店計画テスト ===\n'))
        
        # 会社とユーザーの取得
        if options['company_id']:
            company = Company.objects.get(id=options['company_id'])
        else:
            company = Company.objects.first()
            if not company:
                self.stdout.write(self.style.ERROR('会社が存在しません。'))
                return
        
        if options['user_email']:
            user = User.objects.get(email=options['user_email'])
        else:
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR('ユーザーが存在しません。'))
                return
        
        self.stdout.write(f'会社: {company.name}')
        self.stdout.write(f'ユーザー: {user.username} ({user.email})\n')
        
        # テストデータの作成
        self.stdout.write(self.style.SUCCESS('--- テストデータの作成 ---'))
        
        plan = IzakayaPlan.objects.create(
            company=company,
            user=user,
            store_concept='地域密着型の居酒屋、カジュアルな雰囲気で家族連れも歓迎',
            number_of_seats=30,
            opening_hours_start='17:00:00',
            opening_hours_end='23:00:00',
            target_customer='20代〜40代の会社員、家族連れ',
            average_price_per_customer=Decimal('3500'),
            initial_investment=Decimal('15000000'),  # 1500万円
            monthly_rent=Decimal('300000'),  # 30万円
            number_of_staff=2,
            staff_monthly_salary=Decimal('250000'),  # 25万円
            part_time_hours_per_month=200,
            part_time_hourly_wage=Decimal('1200'),  # 1200円
            sales_coefficients=IzakayaPlanService.get_default_sales_coefficients(),
            is_draft=False,
        )
        
        self.stdout.write(f'✓ 計画を作成しました (ID: {plan.id})')
        self.stdout.write(f'  店のコンセプト: {plan.store_concept}')
        self.stdout.write(f'  席数: {plan.number_of_seats}席')
        self.stdout.write(f'  営業時間: {plan.opening_hours_start} ～ {plan.opening_hours_end}')
        self.stdout.write(f'  客単価: {plan.average_price_per_customer:,.0f}円')
        self.stdout.write(f'  初期投資: {plan.initial_investment:,.0f}円')
        self.stdout.write(f'  月額家賃: {plan.monthly_rent:,.0f}円\n')
        
        # 計算の実行
        self.stdout.write(self.style.SUCCESS('--- 計算の実行 ---'))
        try:
            IzakayaPlanService.calculate_all(plan)
            plan.refresh_from_db()
            self.stdout.write(self.style.SUCCESS('✓ 計算が完了しました\n'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 計算中にエラーが発生しました: {e}'))
            return
        
        # 計算結果の表示
        self.stdout.write(self.style.SUCCESS('--- 計算結果 ---'))
        self.stdout.write(f'月間売上: {plan.monthly_revenue:,.0f}円')
        self.stdout.write(f'月間経費: {plan.monthly_cost:,.0f}円')
        self.stdout.write(f'月間利益: {plan.monthly_profit:,.0f}円')
        
        if plan.payback_period_years == 999:
            self.stdout.write(self.style.ERROR('回収期間: 回収不可能（月間利益が0以下）'))
        else:
            self.stdout.write(f'回収期間: {plan.payback_period_years}年{plan.payback_period_months}ヶ月')
        
        # 詳細な計算内容の表示
        self.stdout.write(self.style.SUCCESS('\n--- 計算の詳細 ---'))
        
        # 営業時間の計算
        from datetime import datetime, date, time
        start_time = datetime.combine(date.today(), plan.opening_hours_start)
        end_time = datetime.combine(date.today(), plan.opening_hours_end)
        if end_time <= start_time:
            end_time = datetime.combine(date.today().replace(day=date.today().day + 1), plan.opening_hours_end)
        opening_duration = (end_time - start_time).total_seconds() / 3600
        self.stdout.write(f'営業時間: {opening_duration:.1f}時間')
        
        # 回転率の計算
        average_stay_hours = Decimal('2.5')
        turnover_rate = Decimal(str(opening_duration)) / average_stay_hours
        self.stdout.write(f'平均滞在時間: {average_stay_hours}時間')
        self.stdout.write(f'回転率: {turnover_rate:.2f}回/日')
        
        # 人件費の計算
        staff_cost = plan.number_of_staff * plan.staff_monthly_salary
        part_time_cost = plan.part_time_hours_per_month * plan.part_time_hourly_wage
        total_labor_cost = staff_cost + part_time_cost
        self.stdout.write(f'社員人件費: {staff_cost:,.0f}円')
        self.stdout.write(f'アルバイト人件費: {part_time_cost:,.0f}円')
        self.stdout.write(f'合計人件費: {total_labor_cost:,.0f}円')
        
        # その他経費（売上の30%）
        other_costs = plan.monthly_revenue * Decimal('0.3')
        self.stdout.write(f'その他経費（売上の30%）: {other_costs:,.0f}円')
        
        # 売上係数の平均
        coefficients = plan.sales_coefficients
        if coefficients:
            avg_coefficient = sum(coefficients.values()) / len(coefficients)
            self.stdout.write(f'平均売上係数: {avg_coefficient:.2f}')
        
        self.stdout.write(self.style.SUCCESS('\n=== テスト完了 ==='))
        self.stdout.write(f'計画のプレビューURL: /ai-consultation/industry/food-service/izakaya-plan/{plan.id}/preview/')

