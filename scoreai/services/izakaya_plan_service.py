"""
居酒屋出店計画の計算ロジックを提供するサービス
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, time
from typing import Tuple, Dict
from ..models import IzakayaPlan


class IzakayaPlanService:
    """居酒屋出店計画の計算ロジックを提供するサービスクラス"""
    
    # 曜日名のマッピング
    WEEKDAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    WEEKDAY_NAMES = {
        'monday': '月曜日',
        'tuesday': '火曜日',
        'wednesday': '水曜日',
        'thursday': '木曜日',
        'friday': '金曜日',
        'saturday': '土曜日',
        'sunday': '日曜日',
    }
    
    @staticmethod
    def calculate_time_slot_revenue(
        plan: IzakayaPlan,
        start_time: time,
        end_time: time,
        operating_days: list,
        price_per_customer: Decimal,
        monthly_coefficients: Dict[str, float],
        average_stay_hours: Decimal = Decimal('2.5')
    ) -> Decimal:
        """
        特定の時間帯の月間売上を計算
        
        Args:
            plan: IzakayaPlanインスタンス
            start_time: 営業開始時間
            end_time: 営業終了時間
            operating_days: 営業曜日のリスト（['monday', 'tuesday', ...]）
            price_per_customer: 客単価
            monthly_coefficients: 月毎指数の辞書（{'1': 1.0, '2': 1.1, ...}）
            average_stay_hours: 平均滞在時間（デフォルト2.5時間）
        
        Returns:
            月間売上（円）
        """
        if not start_time or not end_time or not operating_days:
            return Decimal('0')
        
        # 営業時間の計算（時間）
        start_datetime = datetime.combine(date.today(), start_time)
        end_datetime = datetime.combine(date.today(), end_time)
        
        # 終了時間が開始時間より前の場合は翌日とみなす
        if end_datetime <= start_datetime:
            end_datetime = datetime.combine(
                date.today().replace(day=date.today().day + 1) if date.today().day < 28 else date.today().replace(month=date.today().month + 1, day=1),
                end_time
            )
        
        opening_duration = Decimal(str((end_datetime - start_datetime).total_seconds() / 3600))
        
        # 回転率 = 営業時間 / 平均滞在時間
        if average_stay_hours > 0:
            turnover_rate = opening_duration / average_stay_hours
        else:
            turnover_rate = Decimal('0')
        
        # 営業日数の計算（月間）
        # 1ヶ月あたりの各曜日の出現回数を計算（平均4.33回）
        days_per_weekday = Decimal('4.33')
        monthly_operating_days = Decimal(str(len(operating_days))) * days_per_weekday
        
        # 月毎指数の平均を計算（デフォルトは1.0）
        if monthly_coefficients:
            avg_monthly_coefficient = Decimal(str(sum(monthly_coefficients.values()) / len(monthly_coefficients)))
        else:
            avg_monthly_coefficient = Decimal('1.0')
        
        # 月間売上計算
        monthly_revenue = (
            price_per_customer *
            Decimal(str(plan.number_of_seats)) *
            turnover_rate *
            monthly_operating_days *
            avg_monthly_coefficient
        )
        
        return monthly_revenue.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_monthly_revenue(plan: IzakayaPlan) -> Decimal:
        """
        月間売上を計算（昼と夜の合計）
        
        Args:
            plan: IzakayaPlanインスタンス
        
        Returns:
            月間売上（円）
        """
        total_revenue = Decimal('0')
        
        # 昼の営業時間帯の売上
        if plan.lunch_start_time and plan.lunch_end_time and plan.lunch_operating_days:
            lunch_revenue = IzakayaPlanService.calculate_time_slot_revenue(
                plan=plan,
                start_time=plan.lunch_start_time,
                end_time=plan.lunch_end_time,
                operating_days=plan.lunch_operating_days or [],
                price_per_customer=Decimal(str(plan.lunch_price_per_customer)),
                monthly_coefficients=plan.lunch_monthly_coefficients or {}
            )
            total_revenue += lunch_revenue
        
        # 夜の営業時間帯の売上
        if plan.dinner_start_time and plan.dinner_end_time and plan.dinner_operating_days:
            dinner_revenue = IzakayaPlanService.calculate_time_slot_revenue(
                plan=plan,
                start_time=plan.dinner_start_time,
                end_time=plan.dinner_end_time,
                operating_days=plan.dinner_operating_days or [],
                price_per_customer=Decimal(str(plan.dinner_price_per_customer)),
                monthly_coefficients=plan.dinner_monthly_coefficients or {}
            )
            total_revenue += dinner_revenue
        
        # 後方互換性: 旧フィールドが設定されている場合
        if not total_revenue and plan.opening_hours_start and plan.opening_hours_end:
            # 旧ロジックを使用
            from datetime import datetime as dt
            start_time_obj = plan.opening_hours_start
            end_time_obj = plan.opening_hours_end
            
            if isinstance(start_time_obj, str):
                start_time_obj = dt.strptime(start_time_obj, '%H:%M:%S').time()
            if isinstance(end_time_obj, str):
                end_time_obj = dt.strptime(end_time_obj, '%H:%M:%S').time()
            
            start_datetime = datetime.combine(date.today(), start_time_obj)
            end_datetime = datetime.combine(date.today(), end_time_obj)
            
            if end_datetime <= start_datetime:
                end_datetime = datetime.combine(
                    date.today().replace(day=date.today().day + 1) if date.today().day < 28 else date.today().replace(month=date.today().month + 1, day=1),
                    end_time_obj
                )
            
            opening_duration = Decimal(str((end_datetime - start_datetime).total_seconds() / 3600))
            average_stay_hours = Decimal('2.5')
            turnover_rate = opening_duration / average_stay_hours if average_stay_hours > 0 else Decimal('0')
            
            coefficients = plan.sales_coefficients or {}
            if coefficients:
                avg_coefficient = Decimal(str(sum(coefficients.values()) / len(coefficients)))
            else:
                avg_coefficient = Decimal('1.0')
            
            monthly_operating_days = Decimal('30')
            total_revenue = (
                Decimal(str(plan.average_price_per_customer)) *
                Decimal(str(plan.number_of_seats)) *
                turnover_rate *
                monthly_operating_days *
                avg_coefficient
            )
        
        return total_revenue.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_monthly_cost_of_goods_sold(plan: IzakayaPlan) -> Decimal:
        """
        月間売上原価を計算
        
        Args:
            plan: IzakayaPlanインスタンス
        
        Returns:
            月間売上原価（円）
        """
        total_cost = Decimal('0')
        monthly_revenue = IzakayaPlanService.calculate_monthly_revenue(plan)
        
        # 昼の営業時間帯の原価
        if plan.lunch_start_time and plan.lunch_end_time and plan.lunch_operating_days:
            lunch_revenue = IzakayaPlanService.calculate_time_slot_revenue(
                plan=plan,
                start_time=plan.lunch_start_time,
                end_time=plan.lunch_end_time,
                operating_days=plan.lunch_operating_days or [],
                price_per_customer=Decimal(str(plan.lunch_price_per_customer)),
                monthly_coefficients=plan.lunch_monthly_coefficients or {}
            )
            lunch_cost_rate = Decimal(str(plan.lunch_cost_rate)) / Decimal('100')
            total_cost += lunch_revenue * lunch_cost_rate
        
        # 夜の営業時間帯の原価
        if plan.dinner_start_time and plan.dinner_end_time and plan.dinner_operating_days:
            dinner_revenue = IzakayaPlanService.calculate_time_slot_revenue(
                plan=plan,
                start_time=plan.dinner_start_time,
                end_time=plan.dinner_end_time,
                operating_days=plan.dinner_operating_days or [],
                price_per_customer=Decimal(str(plan.dinner_price_per_customer)),
                monthly_coefficients=plan.dinner_monthly_coefficients or {}
            )
            dinner_cost_rate = Decimal(str(plan.dinner_cost_rate)) / Decimal('100')
            total_cost += dinner_revenue * dinner_cost_rate
        
        # 後方互換性: 旧フィールドが設定されている場合
        if not total_cost and plan.opening_hours_start and plan.opening_hours_end:
            # デフォルト原価率30%を使用
            default_cost_rate = Decimal('0.3')
            total_cost = monthly_revenue * default_cost_rate
        
        return total_cost.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_monthly_cost(plan: IzakayaPlan) -> Decimal:
        """
        月間経費を計算
        
        経費 = 家賃 + 人件費 + 光熱費 + 消耗品費 + 広告宣伝費 + 手数料 + その他販管費
        
        Args:
            plan: IzakayaPlanインスタンス
        
        Returns:
            月間経費（円）
        """
        # 人件費
        staff_cost = Decimal(str(plan.number_of_staff)) * Decimal(str(plan.staff_monthly_salary))
        part_time_cost = Decimal(str(plan.part_time_hours_per_month)) * Decimal(str(plan.part_time_hourly_wage))
        total_labor_cost = staff_cost + part_time_cost
        
        # 月間経費
        monthly_cost = (
            Decimal(str(plan.monthly_rent)) +
            total_labor_cost +
            Decimal(str(plan.monthly_utilities)) +
            Decimal(str(plan.monthly_supplies)) +
            Decimal(str(plan.monthly_advertising)) +
            Decimal(str(plan.monthly_fees)) +
            Decimal(str(plan.monthly_other_expenses))
        )
        
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
        monthly_profit = plan.monthly_profit or Decimal('0')
        
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
        
        # 月間売上
        plan.monthly_revenue = IzakayaPlanService.calculate_monthly_revenue(plan)
        
        # 月間売上原価
        plan.monthly_cost_of_goods_sold = IzakayaPlanService.calculate_monthly_cost_of_goods_sold(plan)
        
        # 月間粗利益
        plan.monthly_gross_profit = plan.monthly_revenue - plan.monthly_cost_of_goods_sold
        
        # 月間経費
        plan.monthly_cost = IzakayaPlanService.calculate_monthly_cost(plan)
        
        # 月間利益
        plan.monthly_profit = plan.monthly_gross_profit - plan.monthly_cost
        
        # 回収期間
        years, months = IzakayaPlanService.calculate_payback_period(plan)
        plan.payback_period_years = years
        plan.payback_period_months = months
        
        plan.save()
        return plan
    
    @staticmethod
    def get_default_sales_coefficients() -> dict:
        """
        デフォルトの売上係数を返す（後方互換性のため）
        
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
    
    @staticmethod
    def get_default_monthly_coefficients() -> dict:
        """
        デフォルトの月毎指数を返す
        
        Returns:
            月毎指数の辞書（1-12月、すべて1.0）
        """
        return {str(i): 1.0 for i in range(1, 13)}
