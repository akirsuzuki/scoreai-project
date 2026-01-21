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
    target_year: int,
    previous_year: Optional[int] = None
) -> Dict[str, Any]:
    """
    予算対象年度末の借入金残高を計算（Debtモデルのbalance_fy1プロパティを使用）
    
    Args:
        company: 会社オブジェクト
        target_year: 予算対象年度
        previous_year: 前期年度（指定がない場合は自動計算）
        
    Returns:
        借入金情報の辞書（短期借入金、長期借入金、合計など）
    """
    # 会社の決算月を取得
    fiscal_month = company.fiscal_month
    
    # 現在の日付を取得
    current_date = datetime.now()
    current_year = current_date.year
    current_month = current_date.month
    
    # 前期年度を計算（指定がない場合）
    if previous_year is None:
        # 最新の実績年度を取得
        latest_actual = FiscalSummary_Year.objects.filter(
            company=company,
            is_budget=False,
            is_draft=False
        ).order_by('-year').first()
        if latest_actual:
            previous_year = latest_actual.year
        else:
            # 実績がない場合は現在年度を前期とする
            if current_month <= fiscal_month:
                previous_year = current_year - 1
            else:
                previous_year = current_year
    
    # target_yearが前期から何期後かを計算
    years_ahead = target_year - previous_year
    
    # 借入情報を取得
    debts = Debt.objects.filter(
        company=company,
        is_nodisplay=False
    ).select_related('financial_institution', 'secured_type')
    
    total_short_term_balance = 0
    total_long_term_balance = 0
    total_interest_expense = 0
    debt_list = []
    
    for debt in debts:
        # 年度末時点の残高を計算（Debtモデルのプロパティを使用）
        if years_ahead == 1:
            # 次の決算期（FY1）
            balance = debt.balance_fy1
        elif years_ahead == 2:
            # 2期後（FY2）
            balance = debt.balance_fy2
        elif years_ahead == 3:
            # 3期後（FY3）
            balance = debt.balance_fy3
        elif years_ahead == 4:
            # 4期後（FY4）
            balance = debt.balance_fy4
        elif years_ahead == 5:
            # 5期後（FY5）
            balance = debt.balance_fy5
        else:
            # それ以外の場合は手動計算
            if years_ahead <= 0:
                # 過去または現在の年度の場合
                balance = debt.balances_monthly[0] if hasattr(debt, 'balances_monthly') and len(debt.balances_monthly) > 0 else debt.principal
            else:
                # 5期以降の場合はbalance_fy5を使用
                balance = debt.balance_fy5
        
        # 残高が負の値になる場合は0に補正
        balance = max(0, balance)
        
        # 短期/長期の分類（1年以内に返済予定の場合は短期）
        remaining_months = debt.remaining_months
        # years_ahead年後の残高を考慮して残存期間を調整
        adjusted_remaining_months = remaining_months - (years_ahead * 12)
        
        if adjusted_remaining_months <= 12 and adjusted_remaining_months > 0:
            # 1年以内に返済予定の場合は短期借入金
            total_short_term_balance += balance
        else:
            # それ以外は長期借入金
            total_long_term_balance += balance
        
        # 年間利息の概算計算（月次利息 × 12）
        monthly_interest = debt.interest_amount_monthly[0] if hasattr(debt, 'interest_amount_monthly') and len(debt.interest_amount_monthly) > 0 else 0
        total_interest_expense += monthly_interest * 12
        
        debt_list.append({
            'financial_institution': debt.financial_institution.name,
            'principal': debt.principal,
            'interest_rate': float(debt.interest_rate),
            'monthly_repayment': debt.monthly_repayment,
            'balance_at_year_end': int(balance),
            'remaining_months': max(0, int(adjusted_remaining_months)),
        })
    
    return {
        'total_short_term_loans': int(total_short_term_balance),
        'total_long_term_loans': int(total_long_term_balance),
        'total_loans': int(total_short_term_balance + total_long_term_balance),
        'total_interest_expense': int(total_interest_expense),
        'debt_list': debt_list,
        'target_year': target_year,
        'previous_year': previous_year,
        'years_ahead': years_ahead,
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
    
    # 前期実績データ（より詳細な財務諸表データを含める）
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
        'accounts_payable': previous_actual.accounts_payable,
        'total_current_liabilities': previous_actual.total_current_liabilities,
    })
    
    # 借入金情報（予算対象年度末の残高）- Debtモデルのbalance_fy1プロパティを使用
    debt_info = calculate_debt_balance_at_year_end(company, target_year, previous_actual.year)
    
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
        system_instruction = """あなたは財務会計の専門家です。前期実績データ、入力された条件、および借入金の翌期末残高数値を基に、財務会計的に適切な財務諸表の数値を生成してください。

重要な原則：
1. 貸借対照表の整合性を必ず確保してください（資産合計 = 負債合計 + 純資産合計）
2. 借入金情報のtotal_short_term_loansとtotal_long_term_loansを正確に反映してください
3. 前期実績の財務比率やトレンドを考慮して、現実的で実現可能な数値を設定してください
4. 投資予定額は固定資産に反映し、借入予定額は借入金に反映してください
5. 資本金増加予定額は資本金と現金に反映してください
6. 損益計算書と貸借対照表の整合性を保ってください（当期純利益は利益剰余金に反映）

返答は必ずJSON形式で返してください。説明文は不要です。"""
        template = """【会社情報】
会社名: {company_name}
業種: {industry}
規模: {size}
決算月: {fiscal_month}月

【前期実績（{previous_year}年）】
{previous_fiscal_summary}

【借入金情報（{target_year}年度末予測残高）】
以下の情報は、各借入金の返済スケジュールに基づいて計算された{target_year}年度末時点の残高です。
{debt_info}

【予算策定条件】
- 対象年度: {target_year}年
- 売上高成長率: {sales_growth_rate}%
- 投資予定額: {investment_amount}千円（固定資産に加算）
- 借入予定額: {borrowing_amount}千円（借入金に加算、現金にも反映）
- 資本金増加予定額: {capital_increase}千円（資本金と現金に加算）

【予算作成の指示】
上記の情報を基に、{target_year}年度の財務諸表（損益計算書・貸借対照表）の予算を作成してください。

重要な注意事項：
1. 借入金情報のtotal_short_term_loansとtotal_long_term_loansを正確に使用してください
2. 貸借対照表の整合性を確保してください（資産合計 = 負債合計 + 純資産合計）
3. 前期実績の財務比率（売上高営業利益率、ROA、ROEなど）を参考にしてください
4. 投資予定額は固定資産に加算し、借入予定額は借入金と現金に反映してください
5. 資本金増加予定額は資本金と現金に反映してください
6. 当期純利益は利益剰余金に加算してください（前期利益剰余金 + 当期純利益）

以下のフィールドを含むJSON形式で返してください（単位：千円）：
- sales: 売上高
- gross_profit: 粗利益
- operating_profit: 営業利益
- ordinary_profit: 経常利益
- net_profit: 当期純利益
- total_assets: 資産の部合計（流動資産合計 + 固定資産合計）
- total_liabilities: 負債の部合計
- total_net_assets: 純資産の部合計（資本金 + 利益剰余金など）
- capital_stock: 資本金（前期 + 資本金増加予定額）
- retained_earnings: 利益剰余金（前期 + 当期純利益）
- short_term_loans_payable: 短期借入金（借入金情報のtotal_short_term_loans + 新規借入の短期分）
- long_term_loans_payable: 長期借入金（借入金情報のtotal_long_term_loans + 新規借入の長期分）
- total_current_assets: 流動資産合計
- total_fixed_assets: 固定資産合計（前期 + 投資予定額）
- cash_and_deposits: 現金及び預金（前期 + 借入予定額 + 資本金増加予定額 - 投資予定額 + 営業キャッシュフロー）
- accounts_receivable: 売上債権（売上高に応じた適切な金額）
- inventory: 棚卸資産（売上高に応じた適切な金額）

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
                system_instruction = """あなたは財務会計の専門家です。前期実績データ、入力された条件、および借入金の翌期末残高数値を基に、財務会計的に適切な財務諸表の数値を生成してください。

重要な原則：
1. 貸借対照表の整合性を必ず確保してください（資産合計 = 負債合計 + 純資産合計）
2. 借入金情報のtotal_short_term_loansとtotal_long_term_loansを正確に反映してください
3. 前期実績の財務比率やトレンドを考慮して、現実的で実現可能な数値を設定してください
4. 投資予定額は固定資産に反映し、借入予定額は借入金に反映してください
5. 資本金増加予定額は資本金と現金に反映してください
6. 損益計算書と貸借対照表の整合性を保ってください（当期純利益は利益剰余金に反映）

返答は必ずJSON形式で返してください。説明文は不要です。"""
                template = """【会社情報】
会社名: {company_name}
業種: {industry}
規模: {size}
決算月: {fiscal_month}月

【前期実績（{previous_year}年）】
{previous_fiscal_summary}

【借入金情報（{target_year}年度末予測残高）】
以下の情報は、各借入金の返済スケジュールに基づいて計算された{target_year}年度末時点の残高です。
{debt_info}

【予算策定条件】
- 対象年度: {target_year}年
- 売上高成長率: {sales_growth_rate}%
- 投資予定額: {investment_amount}千円（固定資産に加算）
- 借入予定額: {borrowing_amount}千円（借入金に加算、現金にも反映）
- 資本金増加予定額: {capital_increase}千円（資本金と現金に加算）

【予算作成の指示】
上記の情報を基に、{target_year}年度の財務諸表（損益計算書・貸借対照表）の予算を作成してください。

重要な注意事項：
1. 借入金情報のtotal_short_term_loansとtotal_long_term_loansを正確に使用してください
2. 貸借対照表の整合性を確保してください（資産合計 = 負債合計 + 純資産合計）
3. 前期実績の財務比率（売上高営業利益率、ROA、ROEなど）を参考にしてください
4. 投資予定額は固定資産に加算し、借入予定額は借入金と現金に反映してください
5. 資本金増加予定額は資本金と現金に反映してください
6. 当期純利益は利益剰余金に加算してください（前期利益剰余金 + 当期純利益）

以下のフィールドを含むJSON形式で返してください（単位：千円）：
- sales: 売上高
- gross_profit: 粗利益
- operating_profit: 営業利益
- ordinary_profit: 経常利益
- net_profit: 当期純利益
- total_assets: 資産の部合計（流動資産合計 + 固定資産合計）
- total_liabilities: 負債の部合計
- total_net_assets: 純資産の部合計（資本金 + 利益剰余金など）
- capital_stock: 資本金（前期 + 資本金増加予定額）
- retained_earnings: 利益剰余金（前期 + 当期純利益）
- short_term_loans_payable: 短期借入金（借入金情報のtotal_short_term_loans + 新規借入の短期分）
- long_term_loans_payable: 長期借入金（借入金情報のtotal_long_term_loans + 新規借入の長期分）
- total_current_assets: 流動資産合計
- total_fixed_assets: 固定資産合計（前期 + 投資予定額）
- cash_and_deposits: 現金及び預金（前期 + 借入予定額 + 資本金増加予定額 - 投資予定額 + 営業キャッシュフロー）
- accounts_receivable: 売上債権（売上高に応じた適切な金額）
- inventory: 棚卸資産（売上高に応じた適切な金額）

JSONのみを返してください。説明文は不要です。"""
    
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

