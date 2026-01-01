"""
予算策定用のAIユーティリティ関数
"""
import json
import logging
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime

from django.utils import timezone
from ..models import (
    Company,
    FiscalSummary_Year,
    Debt,
    AIConsultationType,
    AIConsultationScript,
    UserAIConsultationScript,
)
from .gemini import get_gemini_response
from .ai_consultation_data import get_company_info, make_json_serializable_for_prompt

logger = logging.getLogger(__name__)


def calculate_debt_balance_at_year_end(
    company: Company,
    target_year: int
) -> Dict[str, Any]:
    """
    予算対象年度末の借入金残高を計算
    
    Args:
        company: 会社オブジェクト
        target_year: 予算対象年度
        
    Returns:
        借入金情報の辞書（短期借入金、長期借入金、合計など）
    """
    # 会社の決算月を取得
    fiscal_month = company.fiscal_month
    
    # 予算対象年度末の日付を計算
    # 例：決算月が5月、target_yearが2025の場合、2025年5月31日が年度末
    year_end_date = datetime(target_year, fiscal_month, 1)
    
    # 現在の日付から年度末までの月数を計算
    current_date = datetime.now()
    if current_date.year < target_year:
        # 未来の年度の場合
        months_to_year_end = (target_year - current_date.year) * 12 + (fiscal_month - current_date.month)
    elif current_date.year == target_year:
        # 同じ年度の場合
        if current_date.month <= fiscal_month:
            months_to_year_end = fiscal_month - current_date.month
        else:
            # 既に決算月を過ぎている場合（次の年度末まで）
            months_to_year_end = (12 - current_date.month) + fiscal_month
    else:
        # 過去の年度の場合（通常は発生しないが、念のため）
        months_to_year_end = 0
    
    # 借入情報を取得
    debts = Debt.objects.filter(
        company=company,
        is_nodisplay=False
    ).select_related('financial_institution', 'secured_type')
    
    total_long_term_balance = 0
    total_interest_expense = 0
    debt_list = []
    
    for debt in debts:
        # 返済開始日からの経過月数を計算
        start_date = debt.start_date
        elapsed_months = (current_date.year - start_date.year) * 12 + (current_date.month - start_date.month)
        
        # 年度末までの経過月数
        months_from_start = elapsed_months + months_to_year_end
        
        # 年度末時点の残高を計算
        if months_from_start <= 0:
            # 返済開始前の場合
            balance = debt.principal
        else:
            # 返済開始後の場合
            balance, interest = debt.balance_after_months(months_from_start)
            total_interest_expense += interest * 12  # 年間利息（簡易計算）
        
        # 全ての借入金を長期借入金として扱う（1年未満の返済も含む）
        total_long_term_balance += balance
        
        remaining_months = debt.remaining_months - months_to_year_end
        debt_list.append({
            'financial_institution': debt.financial_institution.name,
            'principal': debt.principal,
            'interest_rate': float(debt.interest_rate),
            'monthly_repayment': debt.monthly_repayment,
            'balance_at_year_end': balance,
            'remaining_months': max(0, remaining_months),
        })
    
    return {
        'total_short_term_loans': 0,  # 短期借入金は使用しない
        'total_long_term_loans': int(total_long_term_balance),  # 全て長期借入金として扱う
        'total_loans': int(total_long_term_balance),
        'total_interest_expense': int(total_interest_expense),
        'debt_list': debt_list,
    }


def get_budget_data(
    company: Company,
    target_year: int,
    previous_actual: FiscalSummary_Year
) -> Dict[str, Any]:
    """
    予算策定に必要なデータを取得
    
    Args:
        company: 会社オブジェクト
        target_year: 予算対象年度
        previous_actual: 前期実績
        
    Returns:
        予算策定用データの辞書
    """
    # 会社情報
    company_info = get_company_info(company)
    
    # 前期実績データ
    previous_fiscal_summary = make_json_serializable_for_prompt({
        'year': previous_actual.year,
        'sales': previous_actual.sales,
        'gross_profit': previous_actual.gross_profit,
        'operating_profit': previous_actual.operating_profit,
        'ordinary_profit': previous_actual.ordinary_profit,
        'net_profit': previous_actual.net_profit,
        'total_assets': previous_actual.total_assets,
        'total_liabilities': previous_actual.total_liabilities,
        'total_net_assets': previous_actual.total_net_assets,
        'capital_stock': previous_actual.capital_stock,
        'retained_earnings': previous_actual.retained_earnings,
        'short_term_loans_payable': previous_actual.short_term_loans_payable,
        'long_term_loans_payable': previous_actual.long_term_loans_payable,
        'total_current_assets': previous_actual.total_current_assets,
        'total_fixed_assets': previous_actual.total_fixed_assets,
        'cash_and_deposits': previous_actual.cash_and_deposits,
        'accounts_receivable': previous_actual.accounts_receivable,
        'inventory': previous_actual.inventory,
    })
    
    # 借入金情報（予算対象年度末の残高）
    debt_info = calculate_debt_balance_at_year_end(company, target_year)
    
    return {
        'company_info': company_info,
        'previous_fiscal_summary': previous_fiscal_summary,
        'debt_info': debt_info,
        'target_year': target_year,
    }


def build_budget_prompt(
    company: Company,
    target_year: int,
    sales_growth_rate: Decimal,
    investment_amount: int,
    borrowing_amount: int,
    capital_increase: int,
    previous_actual: FiscalSummary_Year,
    user_script: Optional[UserAIConsultationScript] = None
) -> Tuple[str, Optional[str]]:
    """
    予算策定用のプロンプトを構築
    
    Args:
        company: 会社オブジェクト
        target_year: 予算対象年度
        sales_growth_rate: 売上高成長率（%）
        investment_amount: 投資予定額（千円）
        borrowing_amount: 借入予定額（千円）
        capital_increase: 資本金増加予定額（千円）
        previous_actual: 前期実績
        user_script: ユーザー用スクリプト（オプション）
        
    Returns:
        (prompt, system_instruction)のタプル
    """
    # スクリプトを取得
    consultation_type = AIConsultationType.objects.filter(name='予算策定').first()
    if not consultation_type:
        # 予算策定タイプが存在しない場合はデフォルトのプロンプトを使用
        system_instruction = """あなたは財務分析の専門家です。前期実績と指定された条件を基に、適切な予算を作成してください。
予算は現実的で実現可能な数値である必要があります。借入金残高の計算も正確に行ってください。
返答は必ずJSON形式で返してください。説明文は不要です。"""
        template = """【会社情報】
会社名: {company_name}
業種: {industry}
規模: {size}
決算月: {fiscal_month}月

【前期実績（{previous_year}年）】
{previous_fiscal_summary}

【借入金情報（{target_year}年度末予測残高）】
{debt_info}

【予算策定条件】
- 対象年度: {target_year}年
- 売上高成長率: {sales_growth_rate}%
- 投資予定額: {investment_amount}千円
- 借入予定額: {borrowing_amount}千円
- 資本金増加予定額: {capital_increase}千円

上記の情報を基に、{target_year}年度の予算を作成してください。
予算はJSON形式で返してください。以下のフィールドを含めてください（単位：千円）：
- sales: 売上高
- gross_profit: 粗利益
- operating_profit: 営業利益
- ordinary_profit: 経常利益
- net_profit: 当期純利益
- total_assets: 資産の部合計
- total_liabilities: 負債の部合計
- total_net_assets: 純資産の部合計
- capital_stock: 資本金
- retained_earnings: 利益剰余金
- short_term_loans_payable: 短期借入金（借入金情報のtotal_short_term_loansを反映）
- long_term_loans_payable: 長期借入金（借入金情報のtotal_long_term_loansを反映）
- total_current_assets: 流動資産合計
- total_fixed_assets: 固定資産合計（投資予定額を加算）
- cash_and_deposits: 現金及び預金
- accounts_receivable: 売上債権
- inventory: 棚卸資産

JSONのみを返してください。説明文は不要です。"""
    else:
        # スクリプトを取得（ユーザー用 → システム用の順）
        if user_script:
            system_instruction = user_script.system_instruction
            template = user_script.prompt_template
        else:
            script = AIConsultationScript.objects.filter(
                consultation_type=consultation_type,
                is_active=True,
                is_default=True
            ).first()
            if script:
                system_instruction = script.system_instruction
                template = script.default_prompt_template
            else:
                # デフォルトのプロンプト
                system_instruction = """あなたは財務分析の専門家です。前期実績と指定された条件を基に、適切な予算を作成してください。
予算は現実的で実現可能な数値である必要があります。借入金残高の計算も正確に行ってください。
返答は必ずJSON形式で返してください。説明文は不要です。"""
                template = """【会社情報】
会社名: {company_name}
業種: {industry}
規模: {size}
決算月: {fiscal_month}月

【前期実績（{previous_year}年）】
{previous_fiscal_summary}

【借入金情報（{target_year}年度末予測残高）】
{debt_info}

【予算策定条件】
- 対象年度: {target_year}年
- 売上高成長率: {sales_growth_rate}%
- 投資予定額: {investment_amount}千円
- 借入予定額: {borrowing_amount}千円
- 資本金増加予定額: {capital_increase}千円

上記の情報を基に、{target_year}年度の予算を作成してください。
予算はJSON形式で返してください。"""
    
    # データを取得
    budget_data = get_budget_data(company, target_year, previous_actual)
    
    # テンプレート変数を準備
    template_vars = {
        'company_name': budget_data['company_info'].get('name', ''),
        'industry': budget_data['company_info'].get('industry', ''),
        'size': budget_data['company_info'].get('size', ''),
        'fiscal_month': budget_data['company_info'].get('fiscal_month', 3),
        'previous_year': previous_actual.year,
        'target_year': target_year,
        'sales_growth_rate': float(sales_growth_rate),
        'investment_amount': investment_amount,
        'borrowing_amount': borrowing_amount,
        'capital_increase': capital_increase,
        'previous_fiscal_summary': json.dumps(budget_data['previous_fiscal_summary'], default=str, ensure_ascii=False, indent=2),
        'debt_info': json.dumps(budget_data['debt_info'], default=str, ensure_ascii=False, indent=2),
    }
    
    # テンプレートを展開
    prompt = template.format(**template_vars)
    
    return prompt, system_instruction


def generate_budget_with_ai(
    company: Company,
    target_year: int,
    sales_growth_rate: Decimal,
    investment_amount: int,
    borrowing_amount: int,
    capital_increase: int,
    previous_actual: FiscalSummary_Year,
    user_script: Optional[UserAIConsultationScript] = None
) -> Dict[str, Any]:
    """
    AIを使用して予算を生成
    
    Args:
        company: 会社オブジェクト
        target_year: 予算対象年度
        sales_growth_rate: 売上高成長率（%）
        investment_amount: 投資予定額（千円）
        borrowing_amount: 借入予定額（千円）
        capital_increase: 資本金増加予定額（千円）
        previous_actual: 前期実績
        user_script: ユーザー用スクリプト（オプション）
        
    Returns:
        予算データの辞書
    """
    # プロンプトを構築
    prompt, system_instruction = build_budget_prompt(
        company=company,
        target_year=target_year,
        sales_growth_rate=sales_growth_rate,
        investment_amount=investment_amount,
        borrowing_amount=borrowing_amount,
        capital_increase=capital_increase,
        previous_actual=previous_actual,
        user_script=user_script
    )
    
    # AIに問い合わせ
    logger.info(f"Generating budget with AI for {company.name}, year {target_year}")
    ai_response = get_gemini_response(
        prompt=prompt,
        system_instruction=system_instruction
    )
    
    if not ai_response:
        raise ValueError("AIからの応答が取得できませんでした。")
    
    # JSONをパース
    try:
        # 応答からJSON部分を抽出（```json ... ``` の形式の場合）
        if '```json' in ai_response:
            json_start = ai_response.find('```json') + 7
            json_end = ai_response.find('```', json_start)
            json_str = ai_response[json_start:json_end].strip()
        elif '```' in ai_response:
            json_start = ai_response.find('```') + 3
            json_end = ai_response.find('```', json_start)
            json_str = ai_response[json_start:json_end].strip()
        else:
            json_str = ai_response.strip()
        
        budget_data = json.loads(json_str)
        
        # 必須フィールドをチェック
        required_fields = [
            'sales', 'gross_profit', 'operating_profit', 'ordinary_profit', 'net_profit',
            'total_assets', 'total_liabilities', 'total_net_assets',
            'capital_stock', 'retained_earnings',
            'short_term_loans_payable', 'long_term_loans_payable',
            'total_current_assets', 'total_fixed_assets',
            'cash_and_deposits', 'accounts_receivable', 'inventory',
        ]
        
        for field in required_fields:
            if field not in budget_data:
                logger.warning(f"Missing field in AI response: {field}")
                budget_data[field] = 0
        
        # 整数に変換
        for key, value in budget_data.items():
            if isinstance(value, (int, float)):
                budget_data[key] = int(value)
        
        # 予算データに必要な追加フィールドを設定
        budget_data['year'] = target_year
        budget_data['is_budget'] = True
        budget_data['is_draft'] = False
        
        return budget_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}")
        logger.error(f"AI response: {ai_response}")
        raise ValueError(f"AIからの応答をJSONとして解析できませんでした: {str(e)}")

