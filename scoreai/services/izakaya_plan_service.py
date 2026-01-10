"""
居酒屋出店計画の計算ロジックを提供するサービス
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, time
from typing import Tuple
from ..models import IzakayaPlan


class IzakayaPlanService:
    """居酒屋出店計画の計算ロジックを提供するサービスクラス"""
    
    @staticmethod
    def calculate_monthly_revenue(plan: IzakayaPlan) -> Decimal:
        """
        月間売上を計算
        
        計算式:
        月間売上 = 客単価 × 席数 × 回転率 × 営業日数 × 平均係数
        
        回転率 = 営業時間 / 平均滞在時間
        
        Args:
            plan: IzakayaPlanインスタンス
        
        Returns:
            月間売上（円）
        """
        if not plan.opening_hours_start or not plan.opening_hours_end:
            return Decimal('0')
        
        # 営業時間の計算（時間）
        # TimeFieldからtimeオブジェクトを取得
        if isinstance(plan.opening_hours_start, str):
            from datetime import datetime as dt
            start_time_obj = dt.strptime(plan.opening_hours_start, '%H:%M:%S').time()
        else:
            start_time_obj = plan.opening_hours_start
        
        if isinstance(plan.opening_hours_end, str):
            from datetime import datetime as dt
            end_time_obj = dt.strptime(plan.opening_hours_end, '%H:%M:%S').time()
        else:
            end_time_obj = plan.opening_hours_end
        
        start_time = datetime.combine(date.today(), start_time_obj)
        end_time = datetime.combine(date.today(), end_time_obj)
        
        # 終了時間が開始時間より前の場合は翌日とみなす
        if end_time <= start_time:
            end_time = datetime.combine(date.today().replace(day=date.today().day + 1), end_time_obj)
        
        opening_duration = (end_time - start_time).total_seconds() / 3600
        
        # 平均滞在時間（仮に2.5時間とする、将来的には設定可能にする）
        average_stay_hours = Decimal('2.5')
        
        # 回転率 = 営業時間 / 平均滞在時間
        if average_stay_hours > 0:
            turnover_rate = Decimal(str(opening_duration)) / average_stay_hours
        else:
            turnover_rate = Decimal('0')
        
        # 営業日数の計算（月間）
        # 曜日別係数の平均を計算
        coefficients = plan.sales_coefficients or {}
        if coefficients:
            avg_coefficient = Decimal(str(sum(coefficients.values()) / len(coefficients)))
        else:
            # デフォルト係数（全曜日1.0）
            avg_coefficient = Decimal('1.0')
        
        # 月間営業日数（仮に30日とする）
        monthly_operating_days = Decimal('30')
        
        # 月間売上計算
        monthly_revenue = (
            Decimal(str(plan.average_price_per_customer)) *
            Decimal(str(plan.number_of_seats)) *
            turnover_rate *
            monthly_operating_days *
            avg_coefficient
        )
        
        return monthly_revenue.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_monthly_cost(plan: IzakayaPlan) -> Decimal:
        """
        月間経費を計算
        
        経費 = 家賃 + 人件費 + その他経費（売上の30%を仮定）
        
        Args:
            plan: IzakayaPlanインスタンス
        
        Returns:
            月間経費（円）
        """
        # 人件費
        staff_cost = Decimal(str(plan.number_of_staff)) * Decimal(str(plan.staff_monthly_salary))
        part_time_cost = Decimal(str(plan.part_time_hours_per_month)) * Decimal(str(plan.part_time_hourly_wage))
        total_labor_cost = staff_cost + part_time_cost
        
        # その他経費（売上の30%を仮定：食材費、光熱費、その他）
        monthly_revenue = IzakayaPlanService.calculate_monthly_revenue(plan)
        other_costs = monthly_revenue * Decimal('0.3')
        
        # 月間経費
        monthly_cost = Decimal(str(plan.monthly_rent)) + total_labor_cost + other_costs
        
        return monthly_cost.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_payback_period(plan: IzakayaPlan) -> Tuple[int, int]:
        """
        初期投資回収期間を計算
        
        Args:
            plan: IzakayaPlanインスタンス
        
        Returns:
            (年, 月) のタプル
        """
        monthly_revenue = IzakayaPlanService.calculate_monthly_revenue(plan)
        monthly_cost = IzakayaPlanService.calculate_monthly_cost(plan)
        monthly_profit = monthly_revenue - monthly_cost
        
        if monthly_profit <= 0:
            return (999, 999)  # 回収不可能
        
        initial_investment = Decimal(str(plan.initial_investment))
        if initial_investment <= 0:
            return (0, 0)
        
        payback_months = initial_investment / monthly_profit
        payback_years = int(payback_months // 12)
        payback_months_remainder = int((payback_months % 12).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        
        return (payback_years, payback_months_remainder)
    
    @staticmethod
    def calculate_all(plan: IzakayaPlan) -> IzakayaPlan:
        """
        すべての計算を実行してplanを更新
        
        Args:
            plan: IzakayaPlanインスタンス（companyが設定されている必要がある）
        
        Returns:
            更新されたIzakayaPlanインスタンス
        
        Raises:
            ValueError: Companyが設定されていない場合
        """
        # Companyが設定されていることを確認
        if not plan.company:
            raise ValueError("Company must be set for IzakayaPlan")
        
        plan.monthly_revenue = IzakayaPlanService.calculate_monthly_revenue(plan)
        plan.monthly_cost = IzakayaPlanService.calculate_monthly_cost(plan)
        plan.monthly_profit = plan.monthly_revenue - plan.monthly_cost
        
        years, months = IzakayaPlanService.calculate_payback_period(plan)
        plan.payback_period_years = years
        plan.payback_period_months = months
        
        plan.save()
        return plan
    
    @staticmethod
    def get_default_sales_coefficients() -> dict:
        """
        デフォルトの売上係数を返す
        
        Returns:
            曜日別・祝前日別の売上係数の辞書
        """
        return {
            'monday': 0.8,
            'tuesday': 0.9,
            'wednesday': 0.9,
            'thursday': 1.0,
            'friday': 1.2,
            'saturday': 1.3,
            'sunday': 1.1,
            'holiday_eve': 1.5,
        }

