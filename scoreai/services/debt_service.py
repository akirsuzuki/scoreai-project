"""
借入管理に関するビジネスロジックを提供するサービス層
"""
from typing import Dict, List, Tuple, Any
from django.db.models import QuerySet
from ..models import Debt, Company


class DebtService:
    """借入管理に関するビジネスロジックを提供するサービスクラス"""
    
    @staticmethod
    def get_debt_queryset(company: Company) -> QuerySet:
        """
        会社の借入データを取得するクエリセットを返す
        
        N+1問題を回避するため、関連オブジェクトを事前取得
        
        Args:
            company: 対象となる会社オブジェクト
            
        Returns:
            最適化されたDebtクエリセット
        """
        return Debt.objects.filter(
            company=company
        ).select_related(
            'financial_institution',
            'secured_type',
            'company'
        )
    
    @staticmethod
    def get_debt_list_with_totals(company: Company) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[Debt], List[Debt], List[Debt]]:
        """
        選択済みの会社の借入データを取得し、集計情報を返します。
        
        借入データを取得し、アクティブな借入、非表示の借入、リスケ済みの借入、
        完済済みの借入に分類します。また、月次残高や決算期残高の集計も行います。
        
        Args:
            company: 対象となる会社オブジェクト
            
        Returns:
            Tuple containing:
            - debt_list: アクティブな借入のリスト（辞書形式）
            - debt_list_totals: 集計情報の辞書
            - debt_list_nodisplay: 非表示の借入リスト
            - debt_list_rescheduled: リスケ済みの借入リスト
            - debt_list_finished: 完済済みの借入リスト
        """
        debts = DebtService.get_debt_queryset(company)
        
        debt_list = []
        debt_list_rescheduled = []
        debt_list_nodisplay = []
        debt_list_finished = []
        total_monthly_repayment = 0
        total_balances_monthly = [0] * 12
        total_interest_amount_monthly = [0] * 12
        total_balance_fy1 = 0
        total_balance_fy2 = 0
        total_balance_fy3 = 0
        total_balance_fy4 = 0
        total_balance_fy5 = 0
        
        # 返済開始している or していないで処理を分ける
        for debt in debts:
            # 関連オブジェクトの属性を事前に取得（N+1クエリ回避）
            company_name = debt.company.name
            financial_institution = debt.financial_institution
            financial_institution_short_name = debt.financial_institution.short_name
            
            if debt.is_nodisplay:
                debt_list_nodisplay.append(debt)
            elif debt.is_rescheduled:
                debt_list_rescheduled.append(debt)
            elif debt.remaining_months < 1:
                debt_list_finished.append(debt)
            else:
                total_monthly_repayment += debt.monthly_repayment
                total_balance_fy1 += debt.balance_fy1
                total_balance_fy2 += debt.balance_fy2
                total_balance_fy3 += debt.balance_fy3
                total_balance_fy4 += debt.balance_fy4
                total_balance_fy5 += debt.balance_fy5
                
                for i in range(12):
                    total_balances_monthly[i] += debt.balances_monthly[i]
                    total_interest_amount_monthly[i] += debt.interest_amount_monthly[i]
                
                debt_data = {
                    'id': debt.id,
                    'company': company_name,
                    'financial_institution': financial_institution,
                    'financial_institution_short_name': financial_institution_short_name,
                    'debt_type': debt.debt_type,
                    'repayment_months': debt.repayment_months,
                    'principal': debt.principal,
                    'issue_date': debt.issue_date,
                    'start_date': debt.start_date,
                    'interest_rate': debt.interest_rate,
                    'monthly_repayment': debt.monthly_repayment,
                    'payment_terms': debt.payment_terms,
                    'secured_type': debt.secured_type,
                    'remaining_months': debt.remaining_months,
                    'adjusted_amount_first': debt.adjusted_amount_first,
                    'adjusted_amount_last': debt.adjusted_amount_last,
                    'balances_monthly': debt.balances_monthly,
                    'interest_amount_monthly': debt.interest_amount_monthly,
                    'is_securedby_management': debt.is_securedby_management,
                    'is_collateraled': debt.is_collateraled,
                    'is_rescheduled': debt.is_rescheduled,
                    'reschedule_date': debt.reschedule_date,
                    'reschedule_balance': debt.reschedule_balance,
                    'is_nodisplay': debt.is_nodisplay,
                    'balance_fy1': debt.balance_fy1,
                    'balance_fy2': debt.balance_fy2,
                    'balance_fy3': debt.balance_fy3,
                    'balance_fy4': debt.balance_fy4,
                    'balance_fy5': debt.balance_fy5
                }
                debt_list.append(debt_data)
        
        # Sort debt_list by financial_institution and secured_type
        debt_list.sort(key=lambda x: (x['financial_institution'].name, x['secured_type'].name))
        
        # Add totals to the result
        debt_list_totals = {
            'total_monthly_repayment': total_monthly_repayment,
            'total_balances_monthly': total_balances_monthly,
            'total_interest_amount_monthly': total_interest_amount_monthly,
            'total_balance_fy1': total_balance_fy1,
            'total_balance_fy2': total_balance_fy2,
            'total_balance_fy3': total_balance_fy3,
            'total_balance_fy4': total_balance_fy4,
            'total_balance_fy5': total_balance_fy5,
        }
        
        return debt_list, debt_list_totals, debt_list_nodisplay, debt_list_rescheduled, debt_list_finished
    
    @staticmethod
    def calculate_weighted_average_interest(
        total_interest_amount_monthly: List[float],
        total_balances_monthly: List[float]
    ) -> List[float]:
        """
        加重平均金利を計算します。
        
        計算式: 当月利息合計 / 当月残高 * 12 * 100 = 加重平均金利（年利）
        
        Args:
            total_interest_amount_monthly: 月次利息合計のリスト（12ヶ月分）
            total_balances_monthly: 月次残高合計のリスト（12ヶ月分）
            
        Returns:
            加重平均金利のリスト（12ヶ月分、当月のみ計算、他は0）
        """
        if total_balances_monthly[0] != 0:
            weighted_average_interest = [
                (12 * total_interest_amount_monthly[0]) / total_balances_monthly[0] * 100
            ] + [0] * 11  # Keep list format for template compatibility
        else:
            weighted_average_interest = [0] * 12
        
        return weighted_average_interest

