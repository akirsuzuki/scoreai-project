"""
エクスポート機能のビュー
"""
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from datetime import datetime

from ..models import Debt, FiscalSummary_Year, FiscalSummary_Month, UserCompany
from ..services.export_service import ExportService
from ..mixins import SelectedCompanyMixin


@login_required
@require_http_methods(["GET"])
def export_debts(request, format_type='csv'):
    """
    借入データをエクスポート
    
    Args:
        request: HTTPリクエスト
        format_type: エクスポート形式（csv, excel, pdf）
        
    Returns:
        HttpResponse with exported data
    """
    # 選択された会社を取得
    selected_company = UserCompany.objects.filter(
        user=request.user,
        is_selected=True
    ).select_related('company').first()
    
    if not selected_company:
        return JsonResponse({'error': '選択された会社がありません。'}, status=400)
    
    this_company = selected_company.company
    
    # フィルタリングパラメータを取得
    search = request.GET.get('search', '')
    financial_institution_id = request.GET.get('financial_institution')
    secured_type_id = request.GET.get('secured_type')
    is_rescheduled = request.GET.get('is_rescheduled')
    is_nodisplay = request.GET.get('is_nodisplay')
    
    # クエリセットを構築
    queryset = Debt.objects.filter(
        company=this_company
    ).select_related(
        'financial_institution',
        'secured_type'
    )
    
    # フィルタリング
    if search:
        queryset = queryset.filter(
            Q(financial_institution__name__icontains=search) |
            Q(financial_institution__short_name__icontains=search) |
            Q(secured_type__name__icontains=search)
        )
    if financial_institution_id:
        queryset = queryset.filter(financial_institution_id=financial_institution_id)
    if secured_type_id:
        queryset = queryset.filter(secured_type_id=secured_type_id)
    if is_rescheduled == 'true':
        queryset = queryset.filter(is_rescheduled=True)
    elif is_rescheduled == 'false':
        queryset = queryset.filter(is_rescheduled=False)
    if is_nodisplay == 'true':
        queryset = queryset.filter(is_nodisplay=True)
    elif is_nodisplay == 'false':
        queryset = queryset.filter(is_nodisplay=False)
    
    # ヘッダー
    headers = [
        '金融機関', '実行日', '返済開始日', '元本（円）', '利息（%）',
        '月返済額（円）', '返済回数', '残り回数', '保証協会',
        '経営者保証', '担保', 'リスケ', '非表示'
    ]
    
    # データ
    data = []
    for debt in queryset.order_by('-issue_date'):
        data.append([
            debt.financial_institution.short_name if debt.financial_institution else '',
            debt.issue_date.strftime('%Y-%m-%d') if debt.issue_date else '',
            debt.start_date.strftime('%Y-%m-%d') if debt.start_date else '',
            debt.principal,
            float(debt.interest_rate) if debt.interest_rate else 0,
            debt.monthly_repayment,
            debt.payment_terms,
            debt.remaining_months,
            debt.secured_type.name if debt.secured_type else '',
            'あり' if debt.is_securedby_management else 'なし',
            'あり' if debt.is_collateraled else 'なし',
            'あり' if debt.is_rescheduled else 'なし',
            'あり' if debt.is_nodisplay else 'なし',
        ])
    
    # ファイル名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename_base = f"借入データ_{this_company.name}_{timestamp}"
    
    # エクスポート
    try:
        if format_type == 'csv':
            filename = f"{filename_base}.csv"
            return ExportService.export_to_csv(headers, data, filename, encoding='utf-8-sig')
        elif format_type == 'excel':
            filename = f"{filename_base}.xlsx"
            title = f"借入データ - {this_company.name}"
            return ExportService.export_to_excel(headers, data, filename, title=title)
        elif format_type == 'pdf':
            filename = f"{filename_base}.pdf"
            title = f"借入データ - {this_company.name}"
            additional_info = {
                '会社名': this_company.name,
                'エクスポート日時': datetime.now().strftime('%Y年%m月%d日 %H:%M:%S'),
                '件数': len(data)
            }
            return ExportService.export_to_pdf(title, headers, data, filename, additional_info)
        else:
            return JsonResponse({'error': 'サポートされていない形式です。'}, status=400)
    except ImportError as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def export_fiscal_summary_year(request, format_type='csv', year_id=None):
    """
    決算年次データをエクスポート
    
    Args:
        request: HTTPリクエスト
        format_type: エクスポート形式（csv, excel, pdf）
        year_id: 年度ID（Noneの場合はすべて）
        
    Returns:
        HttpResponse with exported data
    """
    # 選択された会社を取得
    selected_company = UserCompany.objects.filter(
        user=request.user,
        is_selected=True
    ).select_related('company').first()
    
    if not selected_company:
        return JsonResponse({'error': '選択された会社がありません。'}, status=400)
    
    this_company = selected_company.company
    
    # クエリセットを構築
    if year_id:
        queryset = FiscalSummary_Year.objects.filter(
            company=this_company,
            id=year_id,
            is_budget=False
        )
    else:
        queryset = FiscalSummary_Year.objects.filter(
            company=this_company,
            is_budget=False
        )
    
    # ヘッダー
    headers = [
        '年度', '現金及び預金合計（千円）', '売上債権合計（千円）', '棚卸資産合計（千円）',
        '流動資産合計（千円）', '有形固定資産合計（千円）', '固定資産合計（千円）',
        '資産の部合計（千円）', '流動負債合計（千円）', '固定負債合計（千円）',
        '負債の部合計（千円）', '純資産の部合計（千円）', '売上高（千円）',
        '粗利益（千円）', '営業利益（千円）', '経常利益（千円）', '当期純利益（千円）'
    ]
    
    # データ
    data = []
    for year_data in queryset.order_by('-year'):
        data.append([
            year_data.year,
            year_data.cash_and_deposits or 0,
            year_data.accounts_receivable or 0,
            year_data.inventory or 0,
            year_data.total_current_assets or 0,
            year_data.total_tangible_fixed_assets or 0,
            year_data.total_fixed_assets or 0,
            year_data.total_assets or 0,
            year_data.total_current_liabilities or 0,
            year_data.total_long_term_liabilities or 0,
            year_data.total_liabilities or 0,
            year_data.total_net_assets or 0,
            year_data.sales or 0,
            year_data.gross_profit or 0,
            year_data.operating_profit or 0,
            year_data.ordinary_profit or 0,
            year_data.net_profit or 0,
        ])
    
    # ファイル名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename_base = f"決算年次データ_{this_company.name}_{timestamp}"
    
    # エクスポート
    try:
        if format_type == 'csv':
            filename = f"{filename_base}.csv"
            return ExportService.export_to_csv(headers, data, filename, encoding='shift-jis')
        elif format_type == 'excel':
            filename = f"{filename_base}.xlsx"
            title = f"決算年次データ - {this_company.name}"
            return ExportService.export_to_excel(headers, data, filename, title=title)
        elif format_type == 'pdf':
            filename = f"{filename_base}.pdf"
            title = f"決算年次データ - {this_company.name}"
            additional_info = {
                '会社名': this_company.name,
                'エクスポート日時': datetime.now().strftime('%Y年%m月%d日 %H:%M:%S'),
                '件数': len(data)
            }
            return ExportService.export_to_pdf(title, headers, data, filename, additional_info)
        else:
            return JsonResponse({'error': 'サポートされていない形式です。'}, status=400)
    except ImportError as e:
        return JsonResponse({'error': str(e)}, status=400)

