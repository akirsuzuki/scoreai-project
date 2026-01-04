"""
ユーティリティ関数モジュール

財務データの計算や集計を行う関数を提供します。
"""
from typing import List, Dict, Tuple, Optional, Any
from decimal import Decimal
from datetime import datetime
import calendar
import random
import logging

from django.db.models import QuerySet, Max

logger = logging.getLogger(__name__)
from ..models import (
    Company,
    Debt,
    FiscalSummary_Year,
    FiscalSummary_Month,
    IndustryBenchmark,
    IndustryIndicator,
    IndustryClassification,
    IndustrySubClassification,
)


def get_finance_score(
    year: int,
    industry_classification: IndustryClassification,
    industry_subclassification: IndustrySubClassification,
    company_size: str,
    indicator_name: str,
    value: Decimal
) -> Optional[int]:
    """
    財務指標のスコア（1-5）を計算します。
    
    業界ベンチマークと比較して、指標値を1-5のスコアに変換します。
    Group A指標（高ければ高いほど良い）とGroup B指標（低ければ低いほど良い）で
    評価方法が異なります。
    
    Args:
        year: 対象の年度
        industry_classification: 業界大分類
        industry_subclassification: 業界小分類
        company_size: 企業規模 ('s', 'm', 'l')
        indicator_name: 指標名（例: 'sales_growth_rate', 'operating_profit_margin'）
        value: 評価対象の指標値
        
    Returns:
        スコア（1-5）。ベンチマークデータが見つからない場合はNone。
        
    Example:
        >>> score = get_finance_score(2023, classification, subclassification, 'm', 'sales_growth_rate', Decimal('10.5'))
        >>> print(score)
        4
    """
    # Group A indicators (高ければ高いほど良い指標)
    group_a_indicators = ["sales_growth_rate", "operating_profit_margin", "labor_productivity", "equity_ratio"]
    # Group B indicators (低ければ低いほど良い指標)
    group_b_indicators = ["operating_working_capital_turnover_period", "EBITDA_interest_bearing_debt_ratio"]

    try:
        indicator_instance = IndustryIndicator.objects.get(name=indicator_name)

        # Check for negative EBITDA
        if indicator_name == 'EBITDA_interest_bearing_debt_ratio' and (value is not None or value < 0):
            return 1
        
        # 最初の検索（N+1問題を回避するため、関連オブジェクトを事前取得）
        benchmark = IndustryBenchmark.objects.filter(
            year=year,
            industry_classification=industry_classification,
            industry_subclassification=industry_subclassification,
            company_size=company_size,
            indicator=indicator_instance
        ).select_related(
            'industry_classification',
            'industry_subclassification',
            'indicator'
        ).first()
        # 見つからない場合は year-1 で再検索
        if not benchmark:
            benchmark = IndustryBenchmark.objects.filter(
                year=year-1,
                industry_classification=industry_classification,
                industry_subclassification=industry_subclassification,
                company_size=company_size,
                indicator=indicator_instance
            ).select_related(
                'industry_classification',
                'industry_subclassification',
                'indicator'
            ).first()

        # それでも見つからない場合は year=2022 で再検索
        if not benchmark:
            benchmark = IndustryBenchmark.objects.filter(
                year=2022,
                industry_classification=industry_classification,
                industry_subclassification=industry_subclassification,
                company_size=company_size,
                indicator=indicator_instance
            ).select_related(
                'industry_classification',
                'industry_subclassification',
                'indicator'
            ).first()

        # それでも見つからなければ None を返す
        if not benchmark:
            return None

    except (IndustryBenchmark.DoesNotExist, IndustryIndicator.DoesNotExist):
        return None

    # Retrieve benchmark ranges
    iv = Decimal(benchmark.range_iv)
    iii = Decimal(benchmark.range_iii)
    ii = Decimal(benchmark.range_ii)
    i = Decimal(benchmark.range_i)

    # Ensure value is a Decimal for accurate comparison
    value = Decimal(value)

    if indicator_instance.name in group_a_indicators:
        # Higher is better
        if value <= iv:
            return 1
        elif iv < value <= iii:
            return 2
        elif iii < value <= ii:
            return 3
        elif ii < value <= i:
            return 4
        elif value > i:
            return 5
    elif indicator_instance.name in group_b_indicators:
        # Lower is better
        if value >= iv:
            return 1
        elif iii <= value < iv:
            return 2
        elif ii <= value < iii:
            return 3
        elif i <= value < ii:
            return 4
        elif value < i:
            return 5
    else:
        return None


def calculate_total_monthly_summaries(
    monthly_summaries: List[Dict[str, Any]],
    year_index: int = 0,
    period_count: int = 13
) -> Dict[str, Any]:
    """
    月次サマリーの合計値を計算します。
    
    指定された年度の月次データから、売上高、粗利益、営業利益、経常利益の
    合計値と平均利益率を計算します。
    
    Args:
        monthly_summaries: 月次サマリーのリスト
        year_index: 対象年度のインデックス（デフォルト: 0）
        period_count: 集計する期間数（デフォルト: 13）
        
    Returns:
        集計結果の辞書。以下のキーを含む:
        - year: 年度
        - sum_sales: 売上高合計
        - sum_gross_profit: 粗利益合計
        - sum_operating_profit: 営業利益合計
        - sum_ordinary_profit: 経常利益合計
        - average_gross_profit_rate: 平均粗利益率
        - average_operating_profit_rate: 平均営業利益率
        - average_ordinary_profit_rate: 平均経常利益率
        
    Example:
        >>> summaries = [{'year': 2023, 'data': [...]}]
        >>> totals = calculate_total_monthly_summaries(summaries, year_index=0)
        >>> print(totals['sum_sales'])
        1000000.0
    """
    # 引数が空でないか確認
    if not monthly_summaries:
        return {
            'year': None,
            'sum_sales': 0,
            'sum_gross_profit': 0,
            'sum_operating_profit': 0,
            'average_ordinary_profit': 0,
            'average_gross_profit_rate': 0,
        }
    # 引数から年を取得
    try:
        year = monthly_summaries[year_index]['year']
    except (IndexError, KeyError):
        # yearが取得できない場合はNoneを返して終了
        return {
            'year': None,
            'sum_sales': 0,
            'sum_gross_profit': 0,
            'sum_operating_profit': 0,
            'average_ordinary_profit': 0,
            'average_gross_profit_rate': 0,
        }
            
    # 各合計値を初期化
    sum_sales = 0.0
    sum_gross_profit = 0.0
    sum_operating_profit = 0.0
    sum_ordinary_profit = 0.0

    # 各データをループして合計を計算
    for month in monthly_summaries[year_index]['data'][:period_count]:
        sum_sales += month['sales']
        sum_gross_profit += month['gross_profit']
        sum_operating_profit += month['operating_profit']
        sum_ordinary_profit += month['ordinary_profit']

    # 各利益率を計算
    average_gross_profit_rate = (sum_gross_profit / sum_sales * 100) if sum_sales > 0 else 0
    average_operating_profit_rate = (sum_operating_profit / sum_sales * 100) if sum_sales > 0 else 0
    average_ordinary_profit_rate = (sum_ordinary_profit / sum_sales * 100) if sum_sales > 0 else 0

    # 結果を辞書形式で返す
    return {
        'year': year,
        'sum_sales': sum_sales,
        'sum_gross_profit': sum_gross_profit,
        'sum_operating_profit': sum_operating_profit,
        'sum_ordinary_profit': sum_ordinary_profit,
        'average_gross_profit_rate': average_gross_profit_rate,
        'average_operating_profit_rate': average_operating_profit_rate,
        'average_ordinary_profit_rate': average_ordinary_profit_rate,
    }


def get_benchmark_index(
    classification: IndustryClassification,
    subclassification: IndustrySubClassification,
    company_size: str,
    year: int
) -> QuerySet[IndustryBenchmark]:
    """
    指定した年度以下のベンチマーク指標を取得します。
    
    指定年度から遡ってベンチマークデータを検索します。
    見つからない場合は2022年のデータを返します。
    
    Args:
        classification: 業界大分類
        subclassification: 業界小分類
        company_size: 企業規模 ('s', 'm', 'l')
        year: 開始年度
        
    Returns:
        ベンチマーク指標のQuerySet
    """
    while year >= 2000:
        benchmark_index = IndustryBenchmark.objects.filter(
            industry_classification=classification,
            industry_subclassification=subclassification,
            company_size=company_size,
            year=year
        )
        if benchmark_index:
            return benchmark_index
        year -= 1
    else:
        # If no data is found, attempt to get data for year=2022
        benchmark_index = IndustryBenchmark.objects.filter(
            industry_classification=classification,
            industry_subclassification=subclassification,
            company_size=company_size,
            year=2022
        )
        return benchmark_index
    
    if not benchmark_index:
        return IndustryBenchmark.objects.none()


def get_last_day_of_next_month(months: int) -> datetime:
    """
    指定した月数後の月末日を返します。
    
    Args:
        months: 現在から何ヶ月後か（例: 1 = 来月、-1 = 先月）
        
    Returns:
        指定月の月末日のdatetimeオブジェクト
        
    Example:
        >>> last_day = get_last_day_of_next_month(1)
        >>> print(last_day)
        2024-02-29 00:00:00
    """
    today = datetime.today()
    # Calculate the target month and year
    target_month = today.month + months
    target_year = today.year + (target_month - 1) // 12
    target_month = (target_month - 1) % 12 + 1

    # Get the last day of the target month
    last_day = calendar.monthrange(target_year, target_month)[1]
    return datetime(target_year, target_month, last_day)


def get_monthly_summaries(
    this_company: Company,
    num_years: int = 5
) -> List[Dict[str, Any]]:
    """
    指定された会社の月次決算サマリーを取得します。
    
    最新の指定年数分の年度データを取得し、各年度の12ヶ月分のデータを
    辞書形式で返します。データがない月は0で埋めます。
    
    Args:
        this_company: 対象となる会社オブジェクト
        num_years: 取得する年数（デフォルト: 5）
        
    Returns:
        月次サマリーのリスト。各要素は以下のキーを含む:
        - year: 年度
        - data: 12ヶ月分のデータ（辞書のリスト）
        - actual_months_count: 実際のデータがある月数
        
    Example:
        >>> company = Company.objects.get(id='...')
        >>> summaries = get_monthly_summaries(company, num_years=3)
        >>> print(summaries[0]['year'])
        2023
    """
    # Ensure num_years is at least 1
    num_years = max(1, int(num_years))

    # 年度取得（実績データのみ：is_budget=False、下書きも含む）
    latest_years = FiscalSummary_Year.objects.filter(
        company=this_company,
        is_budget=False
    ).values_list('year', flat=True).distinct().order_by('-year')[:num_years]

    # 取得した年度をリストに変換し、新しい順に並べる
    latest_years = sorted(latest_years, reverse=True)

    monthly_summaries = []
    for year in latest_years:
        # 実績データのみを取得（is_budget=False、下書きも含む）
        # 同じ期間に複数のレコードがある場合、非下書きを優先し、実績データのみを取得
        # 予算データを確実に除外するため、明示的にis_budget=Falseをチェック
        monthly_data = FiscalSummary_Month.objects.filter(
            fiscal_summary_year__company=this_company,
            fiscal_summary_year__year=year,
            fiscal_summary_year__is_budget=False,  # 年度が実績であること
            is_budget=False  # 月次データが実績であること
        ).exclude(
            is_budget=True  # 念のため、予算データを明示的に除外
        ).exclude(
            fiscal_summary_year__is_budget=True  # 念のため、予算年度を明示的に除外
        ).select_related('fiscal_summary_year', 'fiscal_summary_year__company').order_by('-fiscal_summary_year__is_draft', 'period')

        # 月データを辞書に変換（同じ期間に複数のレコードがある場合、最初の1つ（非下書き優先）のみを使用）
        # 予算データ（is_budget=True）は確実に除外（念のため二重チェック）
        monthly_data_dict = {}
        for month in monthly_data:
            # 予算データを確実に除外（二重チェック）
            # select_relatedで取得しているので、fiscal_summary_yearは既にロードされている
            if month.is_budget is True:
                logger.warning(f"予算データがフィルタを通過しました: month.id={month.id}, month.is_budget={month.is_budget}, fiscal_summary_year.is_budget={month.fiscal_summary_year.is_budget if hasattr(month, 'fiscal_summary_year') else 'N/A'}")
                continue
            if hasattr(month, 'fiscal_summary_year') and month.fiscal_summary_year.is_budget is True:
                logger.warning(f"予算年度のデータがフィルタを通過しました: month.id={month.id}, fiscal_summary_year.is_budget={month.fiscal_summary_year.is_budget}")
                continue
            # 既に同じ期間のデータが存在する場合はスキップ（非下書きが優先される）
            if month.period and month.period not in monthly_data_dict:
                monthly_data_dict[month.period] = {
                    'id': month.id,
                    'sales': float(month.sales) if month.sales is not None else 0.0,
                    'gross_profit': float(month.gross_profit) if month.gross_profit is not None else 0.0,
                    'operating_profit': float(month.operating_profit) if month.operating_profit is not None else 0.0,
                    'ordinary_profit': float(month.ordinary_profit) if month.ordinary_profit is not None else 0.0,
                    'gross_profit_rate': float(month.gross_profit_rate) if month.gross_profit_rate is not None else 0.0,
                    'operating_profit_rate': float(month.operating_profit_rate) if month.operating_profit_rate is not None else 0.0,
                    'ordinary_profit_rate': float(month.ordinary_profit_rate) if month.ordinary_profit_rate is not None else 0.0,
                    'is_budget': month.is_budget,  # 予算データかどうかのフラグを保持
                }


        # 12ヶ月分のデータを作成
        # 決算月を考慮して表示月を計算
        from ..models import Company
        company = this_company
        fiscal_month = company.fiscal_month if hasattr(company, 'fiscal_month') else 1
        
        full_month_data = []
        actual_months_count = 0  # 実際のデータがある月のカウント
        for period in range(1, 13):
            # 決算月を基準に表示月を計算（period=1が決算月の次の月）
            display_month = (fiscal_month + period - 1) % 12
            if display_month == 0:
                display_month = 12
            
            if period in monthly_data_dict:
                full_month_data.append({
                    **monthly_data_dict[period], 
                    'period': period,
                    'display_month': display_month
                })
                actual_months_count += 1
            else:
                full_month_data.append({
                    'period': period,
                    'display_month': display_month,
                    'id': f'temp_{random.randint(10000, 99999)}',
                    'sales': 0,
                    'gross_profit': 0,
                    'operating_profit': 0,
                    'ordinary_profit': 0,
                    'gross_profit_rate': 0,
                    'operating_profit_rate': 0,
                    'ordinary_profit_rate': 0,
                    'is_budget': False,  # データが存在しない場合は実績として扱う
                })

        monthly_summaries.append({
            'year': year,
            'data': full_month_data,
            'actual_months_count': actual_months_count
        })

    return monthly_summaries


def get_debt_list(
    this_company: Company
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[Debt], List[Debt], List[Debt]]:
    """
    選択済みの会社の借入データを取得し、集計情報を返します。
    
    借入データを取得し、アクティブな借入、非表示の借入、リスケ済みの借入、
    完済済みの借入に分類します。また、月次残高や決算期残高の集計も行います。
    
    Args:
        this_company: 対象となる会社オブジェクト
        
    Returns:
        Tuple containing:
        - debt_list: アクティブな借入のリスト（辞書形式）
        - debt_list_totals: 集計情報の辞書
        - debt_list_nodisplay: 非表示の借入リスト
        - debt_list_rescheduled: リスケ済みの借入リスト
        - debt_list_finished: 完済済みの借入リスト
        
    Example:
        >>> company = Company.objects.get(id='...')
        >>> debt_list, totals, nodisplay, rescheduled, finished = get_debt_list(company)
        >>> print(totals['total_monthly_repayment'])
        500000
    """
    # 対象となる借入の絞り込み
    # N+1問題を回避するため、関連オブジェクトを事前取得
    debts = Debt.objects.filter(
        company=this_company
    ).select_related(
        'financial_institution',
        'secured_type',
        'company'
    )

    debt_list = []
    debt_list_rescheduled = []
    debt_list_nodisplay = []
    debt_list_finished = []
    total_monthly_repayment = 0
    total_balances_monthly = [0] * 12  # Initialize with 12 zeros
    total_interest_amount_monthly = [0] * 12  # Initialize with 12 zeros
    total_balance_fy1 = 0
    total_balance_fy2 = 0
    total_balance_fy3 = 0
    total_balance_fy4 = 0
    total_balance_fy5 = 0
    # 返済開始している or していないで処理を分ける
    for debt in debts:
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
                'company': debt.company.name,
                'financial_institution': debt.financial_institution,
                'financial_institution_short_name': debt.financial_institution.short_name,
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


def get_debt_list_byAny(
    summary_field_label: str,
    debt_list: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    借入リストを指定されたフィールドで集計します。
    
    金融機関や保証区分など、指定されたフィールドごとに借入を集計し、
    元本、月返済額、月次残高、決算期残高の合計を計算します。
    
    Args:
        summary_field_label: 集計するフィールドのキー（例: 'financial_institution', 'secured_type'）
        debt_list: 借入データのリスト（辞書形式）
        
    Returns:
        集計結果のリスト。各要素は以下のキーを含む:
        - summary_field_label: 集計フィールドの値
        - principal: 元本合計
        - monthly_repayment: 月返済額合計
        - balances_monthly: 月次残高のリスト（12ヶ月分）
        - balance_fy1: 決算期1の残高合計
        
    Example:
        >>> debt_list = [{'financial_institution': bank1, 'principal': 1000000, ...}, ...]
        >>> by_bank = get_debt_list_byAny('financial_institution', debt_list)
        >>> print(by_bank[0]['principal'])
        5000000
    """
    summary_field = summary_field_label.strip("'")
    debt_list_byAny = {}

    for debt in debt_list:
        if debt[summary_field_label] not in debt_list_byAny:
            debt_list_byAny[debt[summary_field_label]] = {
                'principal': 0,
                'monthly_repayment': 0,
                'balances_monthly': [0] * 12,  # Initialize with 12 zeros
                'balance_fy1': 0,
            }

        debt_list_byAny[debt[summary_field_label]]['principal'] += debt['principal']
        debt_list_byAny[debt[summary_field_label]]['monthly_repayment'] += debt['monthly_repayment']
        debt_list_byAny[debt[summary_field_label]]['balance_fy1'] += debt['balance_fy1']

        # Sum up the monthly balances
        for i in range(12):
            debt_list_byAny[debt[summary_field_label]]['balances_monthly'][i] += debt['balances_monthly'][i]
    # Convert the dictionary to a list of dictionaries
    debt_list_byAny = [{summary_field_label: summary_field, **values} for summary_field, values in debt_list_byAny.items()]

    return debt_list_byAny


def get_debt_list_byBankAndSecuredType(
    debt_list: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    借入リストを金融機関と保証区分の組み合わせで集計します。
    
    金融機関と保証区分の組み合わせごとに借入を集計し、
    元本、月返済額、月次残高、決算期残高の合計を計算します。
    
    Args:
        debt_list: 借入データのリスト（辞書形式）
        
    Returns:
        集計結果のリスト。各要素は以下のキーを含む:
        - financial_institution: 金融機関オブジェクト
        - secured_type: 保証区分オブジェクト
        - principal: 元本合計
        - monthly_repayment: 月返済額合計
        - balances_monthly: 月次残高のリスト（12ヶ月分）
        - balance_fy1: 決算期1の残高合計
        
    Example:
        >>> debt_list = [{'financial_institution': bank1, 'secured_type': type1, ...}, ...]
        >>> by_bank_and_type = get_debt_list_byBankAndSecuredType(debt_list)
        >>> print(by_bank_and_type[0]['principal'])
        3000000
    """
    debt_list_byBankAndSecuredType = {}

    for debt in debt_list:
        key = (debt['financial_institution'], debt['secured_type'])
        if key not in debt_list_byBankAndSecuredType:
            debt_list_byBankAndSecuredType[key] = {
                'principal': 0,
                'monthly_repayment': 0,
                'balances_monthly': [0] * 12,  # Initialize with 12 zeros
                'balance_fy1': 0,
            }

        debt_list_byBankAndSecuredType[key]['principal'] += debt['principal']
        debt_list_byBankAndSecuredType[key]['monthly_repayment'] += debt['monthly_repayment']
        debt_list_byBankAndSecuredType[key]['balance_fy1'] += debt['balance_fy1']

        # Sum up the monthly balances
        for i in range(12):
            debt_list_byBankAndSecuredType[key]['balances_monthly'][i] += debt['balances_monthly'][i]

    # Convert the dictionary to a list of dictionaries
    debt_list_byBankAndSecuredType = [
        {
            'financial_institution': key[0],
            'secured_type': key[1],
            **values
        } for key, values in debt_list_byBankAndSecuredType.items()
    ]

    return debt_list_byBankAndSecuredType


def get_YearlyFiscalSummary(
    this_company: Company,
    years_ago: int = 0
) -> Optional[FiscalSummary_Year]:
    """
    指定された年数前の年度決算サマリーを取得します。
    
    Args:
        this_company: 対象となる会社オブジェクト
        years_ago: 最新年度から何年前か（デフォルト: 0 = 最新年度）
        
    Returns:
        年度決算サマリーオブジェクト。データが存在しない場合はNone。
        
    Example:
        >>> company = Company.objects.get(id='...')
        >>> summary = get_YearlyFiscalSummary(company, years_ago=1)
        >>> print(summary.year)
        2022
    """
    # 最新の年度を取得
    latest_year = FiscalSummary_Year.objects.filter(
        company=this_company
    ).select_related('company').aggregate(Max('year'))['year__max']
    
    if latest_year is None:
        return None  # データが存在しない場合

    # 指定された年数分前の年度を計算
    target_year = latest_year - years_ago

    # 対象年度のFiscalSummary_Yearオブジェクトを取得
    fiscal_summary_year = FiscalSummary_Year.objects.filter(
        company=this_company,
        year=target_year
    ).select_related('company').first()

    return fiscal_summary_year


def get_yearly_summaries(
    this_company: Company,
    num_years: int
) -> List[Dict[str, Any]]:
    """
    指定された年数分の年度決算サマリーを取得します。
    
    Args:
        this_company: 対象となる会社オブジェクト
        num_years: 取得する年数
        
    Returns:
        年度サマリーのリスト。各要素は以下のキーを含む:
        - year: 年度
        - sales: 売上高
        - gross_profit: 粗利益
        - operating_profit: 営業利益
        - ordinary_profit: 経常利益
        
    Example:
        >>> company = Company.objects.get(id='...')
        >>> summaries = get_yearly_summaries(company, num_years=3)
        >>> print(summaries[0]['year'])
        2023
    """
    # 直近num_years分のデータを取得
    yearly_summaries = []
    for year in range(num_years):
        data = get_YearlyFiscalSummary(this_company, years_ago=year)
        if data:
            yearly_summaries.append({
                'year': data.year,
                'sales': data.sales,
                'gross_profit': data.gross_profit,
                'operating_profit': data.operating_profit,
                'ordinary_profit': data.ordinary_profit
            })
    return yearly_summaries

