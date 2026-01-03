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
    MeetingMinutes,
    Stakeholder_name,
)

logger = logging.getLogger(__name__)


def get_fiscal_summary_data(company: Company, year: Optional[int] = None, is_budget: Optional[bool] = None) -> Dict[str, Any]:
    """決算書データを取得
    
    Args:
        company: 会社
        year: 年度（指定がない場合は最新の実績データ）
        is_budget: 予算か実績か（指定がない場合は実績データ）
    """
    query = FiscalSummary_Year.objects.filter(
        company=company,
        is_draft=False
    )
    
    if year is not None:
        query = query.filter(year=year)
    if is_budget is not None:
        query = query.filter(is_budget=is_budget)
    
    if year is None and is_budget is None:
        # デフォルトは最新の実績データ
        query = query.filter(is_budget=False)
    
    fiscal = query.order_by('-year', '-is_budget').first()
    
    if not fiscal:
        return {}
    
    return {
        'year': fiscal.year,
        'is_budget': fiscal.is_budget,
        'sales': fiscal.sales,
        'gross_profit': fiscal.gross_profit,
        'operating_profit': fiscal.operating_profit,
        'ordinary_profit': fiscal.ordinary_profit,
        'net_profit': fiscal.net_profit,
        'total_assets': fiscal.total_assets,
        'total_liabilities': fiscal.total_liabilities,
        'total_net_assets': fiscal.total_net_assets,
        'capital_stock': fiscal.capital_stock,
        'retained_earnings': fiscal.retained_earnings,
    }


def get_available_fiscal_summaries(company: Company) -> Dict[str, list]:
    """利用可能な決算書データの一覧を取得
    直近3年の実績と直近1年の予算を返す
    
    Returns:
        {
            'actual': [{'year': 2025, 'id': '...'}, ...],
            'budget': [{'year': 2025, 'id': '...'}, ...]
        }
    """
    from django.utils import timezone
    current_year = timezone.now().year
    
    # 直近3年の実績データ
    actual_summaries = FiscalSummary_Year.objects.filter(
        company=company,
        is_draft=False,
        is_budget=False,
        year__gte=current_year - 2
    ).order_by('-year').values('id', 'year')
    
    # 直近1年の予算データ
    budget_summaries = FiscalSummary_Year.objects.filter(
        company=company,
        is_draft=False,
        is_budget=True,
        year__gte=current_year
    ).order_by('-year').values('id', 'year')
    
    return {
        'actual': list(actual_summaries),
        'budget': list(budget_summaries),
    }


def get_debt_data(company: Company) -> list:
    """借入情報を取得
    条件: remaining_months > 0 かつ is_nodisplay=False かつ is_rescheduled=False
    """
    debts = Debt.objects.filter(
        company=company,
        is_nodisplay=False,
        is_rescheduled=False
    ).select_related('financial_institution', 'secured_type')
    
    # remaining_months > 0 の条件をPythonでフィルタリング（プロパティのため）
    result = []
    for debt in debts:
        if debt.remaining_months > 0:
            result.append({
                'financial_institution': debt.financial_institution.name,
                'principal': debt.principal,
                'interest_rate': float(debt.interest_rate),
                'monthly_repayment': debt.monthly_repayment,
                'remaining_months': debt.remaining_months,
                'is_securedby_management': debt.is_securedby_management,
                'is_collateraled': debt.is_collateraled,
            })
    
    return result


def get_monthly_data(company: Company, year: Optional[int] = None, is_budget: Optional[bool] = None) -> list:
    """月次推移データを取得
    
    Args:
        company: 会社
        year: 年度（指定がない場合は最新の実績データ）
        is_budget: 予算か実績か（指定がない場合は実績データ）
    """
    query = FiscalSummary_Month.objects.filter(
        fiscal_summary_year__company=company,
        fiscal_summary_year__is_draft=False
    ).select_related('fiscal_summary_year')
    
    if year is not None:
        query = query.filter(fiscal_summary_year__year=year)
    if is_budget is not None:
        query = query.filter(fiscal_summary_year__is_budget=is_budget, is_budget=is_budget)
    
    if year is None and is_budget is None:
        # デフォルトは最新の実績データ
        query = query.filter(fiscal_summary_year__is_budget=False, is_budget=False)
    
    monthly_data = query.order_by(
        '-fiscal_summary_year__year', '-period'
    )
    
    return [
        {
            'year': m.fiscal_summary_year.year,
            'is_budget': m.is_budget,
            'period': m.period,
            'sales': m.sales,
            'gross_profit': m.gross_profit,
            'operating_profit': m.operating_profit,
            'ordinary_profit': m.ordinary_profit,
        }
        for m in monthly_data
    ]


def get_available_monthly_summaries(company: Company) -> Dict[str, list]:
    """利用可能な月次データの一覧を取得
    直近3年の実績と直近1年の予算を返す
    
    Returns:
        {
            'actual': [{'year': 2025, 'fiscal_summary_year_id': '...'}, ...],
            'budget': [{'year': 2025, 'fiscal_summary_year_id': '...'}, ...]
        }
    """
    from django.utils import timezone
    from django.db.models import Max
    current_year = timezone.now().year
    
    # 直近3年の実績データ（年度ごとにグループ化）
    actual_summaries = FiscalSummary_Month.objects.filter(
        fiscal_summary_year__company=company,
        fiscal_summary_year__is_draft=False,
        fiscal_summary_year__is_budget=False,
        is_budget=False,
        fiscal_summary_year__year__gte=current_year - 2
    ).values('fiscal_summary_year__year', 'fiscal_summary_year__id').annotate(
        max_period=Max('period')
    ).order_by('-fiscal_summary_year__year')
    
    # 直近1年の予算データ（年度ごとにグループ化）
    budget_summaries = FiscalSummary_Month.objects.filter(
        fiscal_summary_year__company=company,
        fiscal_summary_year__is_draft=False,
        fiscal_summary_year__is_budget=True,
        is_budget=True,
        fiscal_summary_year__year__gte=current_year
    ).values('fiscal_summary_year__year', 'fiscal_summary_year__id').annotate(
        max_period=Max('period')
    ).order_by('-fiscal_summary_year__year')
    
    return {
        'actual': [
            {
                'year': item['fiscal_summary_year__year'],
                'fiscal_summary_year_id': item['fiscal_summary_year__id'],
                'max_period': item['max_period']
            }
            for item in actual_summaries
        ],
        'budget': [
            {
                'year': item['fiscal_summary_year__year'],
                'fiscal_summary_year_id': item['fiscal_summary_year__id'],
                'max_period': item['max_period']
            }
            for item in budget_summaries
        ],
    }


def get_meeting_minutes_data(company: Company) -> list:
    """議事録データを取得（直近10件）"""
    meeting_minutes = MeetingMinutes.objects.filter(
        company=company
    ).order_by('-meeting_date', '-created_at')[:10]
    
    return [
        {
            'meeting_date': str(mm.meeting_date),
            'category': mm.get_category_display(),
            'notes': mm.notes[:500] if len(mm.notes) > 500 else mm.notes,  # 最初の500文字のみ
        }
        for mm in meeting_minutes
    ]


def get_stakeholder_data(company: Company) -> list:
    """株主情報を取得"""
    stakeholders = Stakeholder_name.objects.filter(
        company=company
    ).order_by('name')
    
    return [
        {
            'name': sh.name,
            'is_representative': sh.is_representative,
            'is_board_member': sh.is_board_member,
            'is_related_person': sh.is_related_person,
            'is_employee': sh.is_employee,
            'memo': sh.memo,
        }
        for sh in stakeholders
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


def get_consultation_data(
    consultation_type: AIConsultationType, 
    company: Company,
    selected_data_types: Optional[list] = None,
    selected_fiscal_years: Optional[list] = None,
    selected_monthly_years: Optional[list] = None
) -> Dict[str, Any]:
    """相談タイプに応じたデータを収集
    
    Args:
        consultation_type: 相談タイプ
        company: 会社
        selected_data_types: 選択されたデータタイプのリスト（Noneの場合は全て取得）
        selected_fiscal_years: 選択された決算書データのリスト [{'year': 2025, 'is_budget': False}, ...]
        selected_monthly_years: 選択された月次データのリスト [{'year': 2025, 'is_budget': False}, ...]
    """
    data = {
        'company_info': get_company_info(company),
    }
    
    # 選択されたデータタイプが指定されている場合のみ、それらを取得
    if selected_data_types is not None:
        if 'fiscal_summary' in selected_data_types:
            # 選択された年度の決算書データを取得
            if selected_fiscal_years:
                fiscal_summaries = []
                for item in selected_fiscal_years:
                    fiscal_data = get_fiscal_summary_data(
                        company, 
                        year=item.get('year'),
                        is_budget=item.get('is_budget')
                    )
                    if fiscal_data:
                        fiscal_summaries.append(fiscal_data)
                if fiscal_summaries:
                    data['fiscal_summary'] = fiscal_summaries if len(fiscal_summaries) > 1 else fiscal_summaries[0]
            else:
                # デフォルトは最新の実績データ
                data['fiscal_summary'] = get_fiscal_summary_data(company)
        
        if 'debt_info' in selected_data_types:
            data['debt_info'] = get_debt_data(company)
        
        if 'monthly_data' in selected_data_types:
            # 選択された年度の月次データを取得
            if selected_monthly_years:
                monthly_data_list = []
                for item in selected_monthly_years:
                    monthly_data = get_monthly_data(
                        company,
                        year=item.get('year'),
                        is_budget=item.get('is_budget')
                    )
                    if monthly_data:
                        monthly_data_list.extend(monthly_data)
                if monthly_data_list:
                    data['monthly_data'] = monthly_data_list
            else:
                # デフォルトは最新の実績データ
                data['monthly_data'] = get_monthly_data(company)
        
        if 'meeting_minutes' in selected_data_types:
            data['meeting_minutes'] = get_meeting_minutes_data(company)
        
        if 'stakeholder_name' in selected_data_types:
            data['stakeholder_name'] = get_stakeholder_data(company)
    else:
        # 後方互換性のため、相談タイプに応じたデータを取得
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
    user_script: Optional[UserAIConsultationScript] = None,
    faq_script: Optional[str] = None
) -> Tuple[str, Optional[str]]:
    """相談タイプに応じたプロンプトを構築
    
    Args:
        consultation_type: 相談タイプ
        user_message: ユーザーのメッセージ
        company_data: 会社データ
        user_script: ユーザー用スクリプト（オプション）
        faq_script: FAQ用スクリプト（オプション、最優先）
    
    Returns:
        (prompt, system_instruction)のタプル
    """
    # スクリプトを取得（FAQ用 → ユーザー用 → システム用の順）
    if faq_script:
        # FAQのスクリプトを使用（システムプロンプトのみ）
        system_instruction = faq_script
        # テンプレートはシステム用のデフォルトを使用
        script = AIConsultationScript.objects.filter(
            consultation_type=consultation_type,
            is_active=True,
            is_default=True
        ).first()
        if script:
            template = script.default_prompt_template
        else:
            template = """【会社情報】
会社名: {company_name}
業種: {industry}
規模: {size}

【ユーザーの質問】
{user_message}

上記の情報を基に、具体的で実践的なアドバイスを提供してください。"""
    elif user_script:
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
            system_instruction = f"与えられた情報に基づいて、{consultation_type.name}に関する実践的で具体的なアドバイスを提供してください。"
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
                fiscal_summary = company_data['fiscal_summary']
                # リストの場合はそのまま、単一の場合はリストに変換
                if isinstance(fiscal_summary, list):
                    fiscal_summary_serialized = make_json_serializable_for_prompt(fiscal_summary)
                else:
                    fiscal_summary_serialized = make_json_serializable_for_prompt([fiscal_summary])
                # default=strを追加して、ULIDなどのシリアライズできないオブジェクトを確実に文字列に変換
                template_vars['fiscal_summary'] = json.dumps(fiscal_summary_serialized, default=str, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Failed to serialize fiscal_summary: {e}")
                # エラーが発生した場合は空のJSON配列を設定
                template_vars['fiscal_summary'] = "[]"
        
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
        
        # 議事録データがある場合（ULIDを文字列に変換してからJSON化）
        if 'meeting_minutes' in company_data:
            try:
                meeting_minutes = make_json_serializable_for_prompt(company_data['meeting_minutes'])
                template_vars['meeting_minutes'] = json.dumps(meeting_minutes, default=str, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Failed to serialize meeting_minutes: {e}")
                template_vars['meeting_minutes'] = "[]"
        
        # 株主情報がある場合（ULIDを文字列に変換してからJSON化）
        if 'stakeholder_name' in company_data:
            try:
                stakeholder_name = make_json_serializable_for_prompt(company_data['stakeholder_name'])
                template_vars['stakeholder_name'] = json.dumps(stakeholder_name, default=str, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Failed to serialize stakeholder_name: {e}")
                template_vars['stakeholder_name'] = "[]"
        
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

