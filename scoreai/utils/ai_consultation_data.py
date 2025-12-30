"""
AI相談に必要なデータを収集するユーティリティ関数
"""
from typing import Dict, Any, Optional, Tuple
import json
import logging

def make_json_serializable_for_prompt(obj):
    """
    ULIDやその他のJSONシリアライズできないオブジェクトを文字列に変換
    プロンプト作成用の簡易版
    """
    # 基本的な型はそのまま返す
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    
    # ULID型のチェック（django_ulid.models.ulid.ULID）
    try:
        obj_type = type(obj).__name__
        if obj_type == 'ULID' or 'ulid' in str(type(obj)).lower():
            return str(obj)
    except (AttributeError, TypeError):
        pass
    
    # 辞書の場合は再帰的に処理
    if isinstance(obj, dict):
        return {key: make_json_serializable_for_prompt(value) for key, value in obj.items()}
    
    # リストやタプルの場合も再帰的に処理
    if isinstance(obj, (list, tuple)):
        return [make_json_serializable_for_prompt(item) for item in obj]
    
    # その他のオブジェクトは文字列に変換
    try:
        return str(obj)
    except (TypeError, ValueError):
        return None

from ..models import (
    AIConsultationType,
    AIConsultationScript,
    UserAIConsultationScript,
    Company,
    FiscalSummary_Year,
    FiscalSummary_Month,
    Debt,
)

logger = logging.getLogger(__name__)


def get_fiscal_summary_data(company: Company) -> Dict[str, Any]:
    """決算書データを取得"""
    latest_fiscal = FiscalSummary_Year.objects.filter(
        company=company,
        is_draft=False
    ).order_by('-year').first()
    
    if not latest_fiscal:
        return {}
    
    return {
        'year': latest_fiscal.year,
        'sales': latest_fiscal.sales,
        'gross_profit': latest_fiscal.gross_profit,
        'operating_profit': latest_fiscal.operating_profit,
        'ordinary_profit': latest_fiscal.ordinary_profit,
        'net_profit': latest_fiscal.net_profit,  # モデルでは net_profit が正しい属性名
        'total_assets': latest_fiscal.total_assets,
        'total_liabilities': latest_fiscal.total_liabilities,
        'total_net_assets': latest_fiscal.total_net_assets,
        'capital_stock': latest_fiscal.capital_stock,
        'retained_earnings': latest_fiscal.retained_earnings,
    }


def get_debt_data(company: Company) -> list:
    """借入情報を取得"""
    debts = Debt.objects.filter(
        company=company,
        is_nodisplay=False
    ).select_related('financial_institution', 'secured_type')
    
    return [
        {
            'financial_institution': debt.financial_institution.name,
            'principal': debt.principal,
            'interest_rate': float(debt.interest_rate),
            'monthly_repayment': debt.monthly_repayment,
            'remaining_months': debt.remaining_months,
            'is_securedby_management': debt.is_securedby_management,
            'is_collateraled': debt.is_collateraled,
        }
        for debt in debts
    ]


def get_monthly_data(company: Company) -> list:
    """月次推移データを取得（直近12ヶ月）"""
    monthly_data = FiscalSummary_Month.objects.filter(
        fiscal_summary_year__company=company
    ).select_related('fiscal_summary_year').order_by(
        '-fiscal_summary_year__year', '-period'
    )[:12]
    
    return [
        {
            'year': m.fiscal_summary_year.year,
            'period': m.period,
            'sales': m.sales,
            'gross_profit': m.gross_profit,
            'operating_profit': m.operating_profit,
            'ordinary_profit': m.ordinary_profit,
        }
        for m in monthly_data
    ]


def get_company_info(company: Company) -> Dict[str, Any]:
    """会社情報を取得"""
    return {
        'name': company.name,
        'industry': company.industry_classification.name if company.industry_classification else None,
        'industry_sub': company.industry_subclassification.name if company.industry_subclassification else None,
        'size': company.get_company_size_display(),
        'fiscal_month': company.fiscal_month,
    }


def get_consultation_data(consultation_type: AIConsultationType, company: Company) -> Dict[str, Any]:
    """相談タイプに応じたデータを収集"""
    data = {
        'company_info': get_company_info(company),
    }
    
    consultation_type_name = consultation_type.name
    
    if '財務' in consultation_type_name:
        data['fiscal_summary'] = get_fiscal_summary_data(company)
        data['debt_info'] = get_debt_data(company)
        data['monthly_data'] = get_monthly_data(company)
    # 補助金・助成金相談（後方互換性のため「補助金」もチェック）
    elif '補助金・助成金' in consultation_type_name or '補助金' in consultation_type_name:
        data['fiscal_summary'] = get_fiscal_summary_data(company)
        data['company_info'] = get_company_info(company)
    elif '税務' in consultation_type_name:
        data['fiscal_summary'] = get_fiscal_summary_data(company)
        data['company_info'] = get_company_info(company)
    elif '法律' in consultation_type_name:
        data['company_info'] = get_company_info(company)
    
    return data


def build_consultation_prompt(
    consultation_type: AIConsultationType,
    user_message: str,
    company_data: Dict[str, Any],
    user_script: Optional[UserAIConsultationScript] = None
) -> Tuple[str, Optional[str]]:
    """相談タイプに応じたプロンプトを構築"""
    # スクリプトを取得
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
            # デフォルトのシステムプロンプトとテンプレート
            system_instruction = f"あなたは経験豊富な{consultation_type.name}の専門家です。与えられた情報に基づいて、実践的で具体的なアドバイスを提供してください。"
            template = """【会社情報】
会社名: {company_name}
業種: {industry}
規模: {size}

【ユーザーの質問】
{user_message}

上記の情報を基に、具体的で実践的なアドバイスを提供してください。"""
    
    # データをテンプレートに埋め込む
    try:
        # 会社情報を展開
        company_info = company_data.get('company_info', {})
        
        # テンプレート変数を準備
        template_vars = {
            'user_message': user_message,
            'company_name': company_info.get('name', ''),
            'industry': company_info.get('industry', ''),
            'size': company_info.get('size', ''),
        }
        
        # 決算書データがある場合（ULIDを文字列に変換してからJSON化）
        if 'fiscal_summary' in company_data:
            try:
                fiscal_summary = make_json_serializable_for_prompt(company_data['fiscal_summary'])
                # default=strを追加して、ULIDなどのシリアライズできないオブジェクトを確実に文字列に変換
                template_vars['fiscal_summary'] = json.dumps(fiscal_summary, default=str, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Failed to serialize fiscal_summary: {e}")
                # エラーが発生した場合は空のJSONオブジェクトを設定
                template_vars['fiscal_summary'] = "{}"
        
        # 借入情報がある場合（ULIDを文字列に変換してからJSON化）
        if 'debt_info' in company_data:
            try:
                debt_info = make_json_serializable_for_prompt(company_data['debt_info'])
                # default=strを追加して、ULIDなどのシリアライズできないオブジェクトを確実に文字列に変換
                template_vars['debt_info'] = json.dumps(debt_info, default=str, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Failed to serialize debt_info: {e}")
                # エラーが発生した場合は空のJSON配列を設定
                template_vars['debt_info'] = "[]"
        
        # 月次データがある場合（ULIDを文字列に変換してからJSON化）
        if 'monthly_data' in company_data:
            try:
                monthly_data = make_json_serializable_for_prompt(company_data['monthly_data'])
                # default=strを追加して、ULIDなどのシリアライズできないオブジェクトを確実に文字列に変換
                template_vars['monthly_data'] = json.dumps(monthly_data, default=str, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Failed to serialize monthly_data: {e}")
                # エラーが発生した場合は空のJSON配列を設定
                template_vars['monthly_data'] = "[]"
        
        # テンプレートをフォーマット
        prompt = template.format(**template_vars)
        
        return prompt, system_instruction
        
    except KeyError as e:
        logger.error(f"Template variable missing: {e}")
        # フォールバック: シンプルなプロンプト
        prompt = f"【ユーザーの質問】\n{user_message}\n\n上記の質問に対して、具体的で実践的なアドバイスを提供してください。"
        return prompt, system_instruction
    except Exception as e:
        logger.error(f"Error building prompt: {e}", exc_info=True)
        prompt = f"【ユーザーの質問】\n{user_message}\n\n上記の質問に対して、具体的で実践的なアドバイスを提供してください。"
        return prompt, system_instruction

