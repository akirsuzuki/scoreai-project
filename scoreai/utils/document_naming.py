"""
ドキュメントファイル名の自動生成ユーティリティ
"""
from typing import Optional
from datetime import datetime
from ..models import Company


def generate_document_filename(
    company: Company,
    document_type: str,
    subfolder_type: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    fiscal_month: Optional[int] = None,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    financial_institution_name: Optional[str] = None,
    contract_partner: Optional[str] = None,
    file_extension: str = 'pdf'
) -> str:
    """
    ドキュメントファイル名を自動生成
    
    Args:
        company: 会社オブジェクト
        document_type: ドキュメントタイプ（financial_statement, trial_balance, loan_contract, contract）
        subfolder_type: サブフォルダタイプ（balance_sheet, profit_loss, monthly_pl, department_pl, lease, sales, rental）
        fiscal_year: 年度（西暦）
        fiscal_month: 決算月
        period_start: 期間開始（例: "2024年10月"）
        period_end: 期間終了（例: "2024年12月"）
        financial_institution_name: 金融機関名（金銭消費貸借契約書の場合）
        contract_partner: 契約相手（契約書の場合）
        file_extension: ファイル拡張子（デフォルト: pdf）
    
    Returns:
        生成されたファイル名
    """
    # 会社名を取得
    company_name = company.name
    
    # ファイル名の基本部分
    filename_parts = [company_name]
    
    if document_type == 'financial_statement':
        # 決算書: 株式会社XX_決算報告書_2024年12月期
        if fiscal_year and fiscal_month:
            filename_parts.append('決算報告書')
            filename_parts.append(f'{fiscal_year}年{fiscal_month}月期')
        else:
            filename_parts.append('決算報告書')
            if fiscal_year:
                filename_parts.append(f'{fiscal_year}年')
    
    elif document_type == 'trial_balance':
        # 試算表: 株式会社XX_試算表_貸借対照表_2024年10月単月
        filename_parts.append('試算表')
        
        if subfolder_type:
            subfolder_names = {
                'balance_sheet': '貸借対照表',
                'profit_loss': '損益計算書',
                'monthly_pl': '月次推移損益計算書',
                'department_pl': '部門別損益計算書',
            }
            filename_parts.append(subfolder_names.get(subfolder_type, subfolder_type))
        
        # 期間の表記
        if period_start and period_end:
            if period_start == period_end:
                # 単月の場合
                filename_parts.append(f'{period_start}単月')
            else:
                # 複数月の場合
                filename_parts.append(f'{period_start}-{period_end}')
        elif period_start:
            filename_parts.append(f'{period_start}単月')
        elif fiscal_year and fiscal_month:
            filename_parts.append(f'{fiscal_year}年{fiscal_month}月単月')
    
    elif document_type == 'loan_contract':
        # 金銭消費貸借契約書: 株式会社XX_金銭消費貸借契約書_2024年12月_みずほ銀行
        filename_parts.append('金銭消費貸借契約書')
        
        # 日付（現在の日付または指定された日付）
        if fiscal_year and fiscal_month:
            filename_parts.append(f'{fiscal_year}年{fiscal_month}月')
        else:
            now = datetime.now()
            filename_parts.append(f'{now.year}年{now.month}月')
        
        if financial_institution_name:
            filename_parts.append(financial_institution_name)
    
    elif document_type == 'contract':
        # 契約書: 株式会社XX_XX契約書_2024年12月_オリックス株式会社
        if subfolder_type:
            contract_names = {
                'lease': 'リース契約書',
                'sales': '商品売買契約',
                'rental': '賃貸借契約',
            }
            contract_name = contract_names.get(subfolder_type, '契約書')
            filename_parts.append(contract_name)
        else:
            filename_parts.append('契約書')
        
        # 日付
        if fiscal_year and fiscal_month:
            filename_parts.append(f'{fiscal_year}年{fiscal_month}月')
        else:
            now = datetime.now()
            filename_parts.append(f'{now.year}年{now.month}月')
        
        if contract_partner:
            filename_parts.append(contract_partner)
    
    # ファイル名を結合
    filename = '_'.join(filename_parts)
    
    # ファイル拡張子を追加
    if not filename.endswith(f'.{file_extension}'):
        filename = f'{filename}.{file_extension}'
    
    return filename


def get_folder_path(
    document_type: str,
    subfolder_type: Optional[str] = None
) -> str:
    """
    フォルダパスを取得
    
    Args:
        document_type: ドキュメントタイプ
        subfolder_type: サブフォルダタイプ
    
    Returns:
        フォルダパス（例: "試算表/貸借対照表"）
    """
    folder_names = {
        'financial_statement': '決算書',
        'trial_balance': '試算表',
        'loan_contract': '金銭消費貸借契約書',
        'contract': '契約書',
    }
    
    subfolder_names = {
        'balance_sheet': '貸借対照表',
        'profit_loss': '損益計算書',
        'monthly_pl': '月次推移損益計算書',
        'department_pl': '部門別損益計算書',
        'lease': 'リース契約書',
        'sales': '商品売買契約',
        'rental': '賃貸借契約',
    }
    
    folder_path = folder_names.get(document_type, document_type)
    
    if subfolder_type and subfolder_type in subfolder_names:
        folder_path = f'{folder_path}/{subfolder_names[subfolder_type]}'
    
    return folder_path

