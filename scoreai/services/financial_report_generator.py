"""
財務会議資料生成サービス

CSVファイルから財務会議用のExcel資料を自動生成する。
- 部門別損益計算書（PL）
- 月次推移損益計算書
- 貸借対照表（BS）
- エグゼクティブサマリー
"""
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Union, BinaryIO, List
from io import BytesIO, StringIO
from decimal import Decimal
import pandas as pd

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side, NamedStyle
from openpyxl.utils import get_column_letter
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.worksheet.page import PageMargins, PrintPageSetup

from ..utils.csv_utils import detect_encoding

logger = logging.getLogger(__name__)


@dataclass
class ReportConfig:
    """レポート設定"""
    company_name: str
    fiscal_year: int
    target_month: int
    target_year: int
    target_f_rate: float = 0.30      # 原価率目標
    target_l_rate: float = 0.30      # 人件費率目標
    target_fl_rate: float = 0.60    # FL率目標
    target_current_ratio: float = 200.0   # 流動比率目標
    target_equity_ratio: float = 30.0     # 自己資本比率目標


class FinancialReportGenerator:
    """財務会議資料ジェネレーター"""
    
    # 色定義
    COLORS = {
        'header_bg': 'E6F0FF',      # ヘッダー背景（薄い青）
        'header_font': '1F4E79',    # ヘッダー文字色
        'section_bg': 'F2F2F2',     # セクション背景（薄いグレー）
        'total_bg': 'DCE6F1',       # 合計行背景
        'highlight_good': 'C6EFCE', # 良好（緑）
        'highlight_bad': 'FFC7CE',  # 注意（赤）
        'border_color': 'B4B4B4',   # 罫線色
    }
    
    def __init__(self, config: ReportConfig):
        """
        Args:
            config: レポート設定
        """
        self.config = config
        self.pl_bumon_df: Optional[pd.DataFrame] = None
        self.pl_bumon_zenki_df: Optional[pd.DataFrame] = None
        self.pl_suii_df: Optional[pd.DataFrame] = None
        self.pl_suii_zenki_df: Optional[pd.DataFrame] = None
        self.bs_df: Optional[pd.DataFrame] = None
        
        # スタイル定義
        self._init_styles()
    
    def _init_styles(self):
        """スタイルを初期化"""
        self.thin_border = Border(
            left=Side(style='thin', color=self.COLORS['border_color']),
            right=Side(style='thin', color=self.COLORS['border_color']),
            top=Side(style='thin', color=self.COLORS['border_color']),
            bottom=Side(style='thin', color=self.COLORS['border_color'])
        )
        
        self.header_fill = PatternFill(
            start_color=self.COLORS['header_bg'],
            end_color=self.COLORS['header_bg'],
            fill_type='solid'
        )
        
        self.header_font = Font(
            bold=True,
            size=10,
            color=self.COLORS['header_font']
        )
        
        self.section_fill = PatternFill(
            start_color=self.COLORS['section_bg'],
            end_color=self.COLORS['section_bg'],
            fill_type='solid'
        )
        
        self.total_fill = PatternFill(
            start_color=self.COLORS['total_bg'],
            end_color=self.COLORS['total_bg'],
            fill_type='solid'
        )
    
    def load_data(
        self,
        pl_bumon_file: Optional[Union[str, bytes, BinaryIO]] = None,
        pl_bumon_zenki_file: Optional[Union[str, bytes, BinaryIO]] = None,
        pl_suii_file: Optional[Union[str, bytes, BinaryIO]] = None,
        pl_suii_zenki_file: Optional[Union[str, bytes, BinaryIO]] = None,
        bs_file: Optional[Union[str, bytes, BinaryIO]] = None,
    ) -> None:
        """
        CSVファイルを読み込む
        
        Args:
            pl_bumon_file: 部門別PL（当期）
            pl_bumon_zenki_file: 部門別PL（前期）
            pl_suii_file: PL月次推移（当期）
            pl_suii_zenki_file: PL月次推移（前期）
            bs_file: 貸借対照表
        """
        if pl_bumon_file:
            self.pl_bumon_df = self._read_csv(pl_bumon_file)
            logger.info(f"部門別PL（当期）を読み込みました: {self.pl_bumon_df.shape}")
        
        if pl_bumon_zenki_file:
            self.pl_bumon_zenki_df = self._read_csv(pl_bumon_zenki_file)
            logger.info(f"部門別PL（前期）を読み込みました: {self.pl_bumon_zenki_df.shape}")
        
        if pl_suii_file:
            self.pl_suii_df = self._read_csv(pl_suii_file)
            logger.info(f"PL月次推移（当期）を読み込みました: {self.pl_suii_df.shape}")
        
        if pl_suii_zenki_file:
            self.pl_suii_zenki_df = self._read_csv(pl_suii_zenki_file)
            logger.info(f"PL月次推移（前期）を読み込みました: {self.pl_suii_zenki_df.shape}")
        
        if bs_file:
            self.bs_df = self._read_csv(bs_file)
            logger.info(f"貸借対照表を読み込みました: {self.bs_df.shape}")
    
    def _read_csv(self, file: Union[str, bytes, BinaryIO]) -> pd.DataFrame:
        """
        CSVファイルを読み込んでDataFrameに変換
        
        Args:
            file: ファイルパス、バイト列、またはファイルオブジェクト
            
        Returns:
            pandas.DataFrame
        """
        # ファイルパスの場合
        if isinstance(file, str):
            with open(file, 'rb') as f:
                content = f.read()
        # バイト列の場合
        elif isinstance(file, bytes):
            content = file
        # ファイルオブジェクトの場合
        else:
            content = file.read()
            if hasattr(file, 'seek'):
                file.seek(0)
        
        # エンコーディング検出
        encoding = detect_encoding(content)
        
        # 複数のエンコーディングを試す
        encodings_to_try = [encoding, 'shift-jis', 'utf-8', 'cp932', 'euc-jp']
        
        for enc in encodings_to_try:
            try:
                decoded = content.decode(enc)
                df = pd.read_csv(StringIO(decoded), header=0)
                logger.debug(f"CSV読み込み成功: encoding={enc}")
                return df
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                logger.warning(f"CSV読み込みエラー (encoding={enc}): {e}")
                continue
        
        raise ValueError("CSVファイルのエンコーディングを検出できませんでした。")
    
    def generate(self) -> BytesIO:
        """
        Excel財務会議資料を生成
        
        Returns:
            BytesIO: 生成されたExcelファイル
        """
        wb = Workbook()
        
        # デフォルトシートを削除
        default_sheet = wb.active
        
        # 各シートを生成
        self._build_executive_summary(wb)
        self._build_pl_bumon(wb)
        self._build_pl_suii(wb)
        self._build_bs(wb)
        
        # デフォルトシートを削除（他のシートがある場合）
        if len(wb.sheetnames) > 1:
            del wb[default_sheet.title]
        
        # BytesIOに保存
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        return output
    
    def _build_executive_summary(self, wb: Workbook) -> None:
        """エグゼクティブサマリーシートを作成"""
        ws = wb.create_sheet(title="エグゼクティブサマリー")
        
        # ページ設定（A4縦）
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.page_setup.orientation = 'portrait'
        ws.page_setup.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 1
        ws.page_margins = PageMargins(left=0.5, right=0.5, top=0.5, bottom=0.5)
        
        row = 1
        
        # タイトル
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws.cell(row=row, column=1)
        cell.value = f"{self.config.company_name} 財務会議資料"
        cell.font = Font(bold=True, size=16)
        cell.alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[row].height = 30
        row += 1
        
        # サブタイトル
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws.cell(row=row, column=1)
        cell.value = f"{self.config.target_year}年{self.config.target_month}月度 / 第{self.config.fiscal_year}期"
        cell.font = Font(size=12)
        cell.alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[row].height = 25
        row += 2
        
        # 経営指標セクション
        row = self._add_summary_section(ws, row, "売上・利益", [
            ("当月売上高", self._get_current_month_sales(), "円"),
            ("累計売上高", self._get_cumulative_sales(), "円"),
            ("当月粗利益", self._get_current_month_gross_profit(), "円"),
            ("累計粗利益", self._get_cumulative_gross_profit(), "円"),
            ("当月営業利益", self._get_current_month_operating_profit(), "円"),
            ("累計営業利益", self._get_cumulative_operating_profit(), "円"),
        ])
        row += 1
        
        # 利益率セクション
        row = self._add_summary_section(ws, row, "利益率", [
            ("粗利益率", self._get_gross_profit_rate(), "%"),
            ("営業利益率", self._get_operating_profit_rate(), "%"),
            ("原価率（F率）", self._get_f_rate(), "%", self.config.target_f_rate * 100),
            ("人件費率（L率）", self._get_l_rate(), "%", self.config.target_l_rate * 100),
            ("FL率", self._get_fl_rate(), "%", self.config.target_fl_rate * 100),
        ])
        row += 1
        
        # 財務指標セクション
        row = self._add_summary_section(ws, row, "財務指標", [
            ("流動比率", self._get_current_ratio(), "%", self.config.target_current_ratio),
            ("自己資本比率", self._get_equity_ratio(), "%", self.config.target_equity_ratio),
        ])
        
        # 列幅設定
        ws.column_dimensions['A'].width = 5
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 18
        ws.column_dimensions['D'].width = 10
        ws.column_dimensions['E'].width = 15
        ws.column_dimensions['F'].width = 10
    
    def _add_summary_section(
        self,
        ws,
        start_row: int,
        section_title: str,
        items: List[tuple]
    ) -> int:
        """サマリーセクションを追加"""
        row = start_row
        
        # セクションタイトル
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws.cell(row=row, column=1)
        cell.value = f"■ {section_title}"
        cell.font = Font(bold=True, size=11)
        cell.fill = self.section_fill
        ws.row_dimensions[row].height = 22
        row += 1
        
        # ヘッダー
        headers = ['', '項目', '実績', '単位', '目標', '達成率']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col)
            cell.value = header
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.border = self.thin_border
            cell.alignment = Alignment(horizontal='center', vertical='center')
        row += 1
        
        # データ行
        for item in items:
            name = item[0]
            value = item[1]
            unit = item[2]
            target = item[3] if len(item) > 3 else None
            
            ws.cell(row=row, column=2).value = name
            ws.cell(row=row, column=2).border = self.thin_border
            
            # 値のフォーマット
            if value is not None:
                if unit == "円":
                    ws.cell(row=row, column=3).value = value
                    ws.cell(row=row, column=3).number_format = '#,##0'
                else:
                    ws.cell(row=row, column=3).value = value
                    ws.cell(row=row, column=3).number_format = '0.0'
            else:
                ws.cell(row=row, column=3).value = "-"
            ws.cell(row=row, column=3).border = self.thin_border
            ws.cell(row=row, column=3).alignment = Alignment(horizontal='right')
            
            ws.cell(row=row, column=4).value = unit
            ws.cell(row=row, column=4).border = self.thin_border
            ws.cell(row=row, column=4).alignment = Alignment(horizontal='center')
            
            # 目標
            if target is not None:
                ws.cell(row=row, column=5).value = target
                ws.cell(row=row, column=5).number_format = '0.0'
            else:
                ws.cell(row=row, column=5).value = "-"
            ws.cell(row=row, column=5).border = self.thin_border
            ws.cell(row=row, column=5).alignment = Alignment(horizontal='right')
            
            # 達成率
            if target is not None and value is not None and target != 0:
                achievement = (value / target) * 100
                ws.cell(row=row, column=6).value = f"{achievement:.1f}%"
                # 色分け（原価率系は逆転）
                if name in ['原価率（F率）', '人件費率（L率）', 'FL率']:
                    if achievement <= 100:
                        ws.cell(row=row, column=6).fill = PatternFill(
                            start_color=self.COLORS['highlight_good'],
                            end_color=self.COLORS['highlight_good'],
                            fill_type='solid'
                        )
                    else:
                        ws.cell(row=row, column=6).fill = PatternFill(
                            start_color=self.COLORS['highlight_bad'],
                            end_color=self.COLORS['highlight_bad'],
                            fill_type='solid'
                        )
                else:
                    if achievement >= 100:
                        ws.cell(row=row, column=6).fill = PatternFill(
                            start_color=self.COLORS['highlight_good'],
                            end_color=self.COLORS['highlight_good'],
                            fill_type='solid'
                        )
                    elif achievement < 80:
                        ws.cell(row=row, column=6).fill = PatternFill(
                            start_color=self.COLORS['highlight_bad'],
                            end_color=self.COLORS['highlight_bad'],
                            fill_type='solid'
                        )
            else:
                ws.cell(row=row, column=6).value = "-"
            ws.cell(row=row, column=6).border = self.thin_border
            ws.cell(row=row, column=6).alignment = Alignment(horizontal='center')
            
            row += 1
        
        return row
    
    def _build_pl_bumon(self, wb: Workbook) -> None:
        """部門別PLシートを作成"""
        if self.pl_bumon_df is None:
            logger.warning("部門別PLデータがありません")
            return
        
        ws = wb.create_sheet(title="部門別PL")
        
        # ページ設定（A3横）
        ws.page_setup.paperSize = ws.PAPERSIZE_A3
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 1
        ws.print_title_cols = 'A:B'  # A列とB列を繰り返し印刷
        ws.page_margins = PageMargins(left=0.3, right=0.3, top=0.3, bottom=0.3)
        
        # タイトル
        row = 1
        ws.merge_cells(f'A{row}:D{row}')
        cell = ws.cell(row=row, column=1)
        cell.value = f"部門別損益計算書 - {self.config.target_year}年{self.config.target_month}月"
        cell.font = Font(bold=True, size=14)
        cell.alignment = Alignment(horizontal='left', vertical='center')
        ws.row_dimensions[row].height = 25
        row += 2
        
        # DataFrameをシートに書き込み
        self._write_dataframe_to_sheet(ws, self.pl_bumon_df, start_row=row)
    
    def _build_pl_suii(self, wb: Workbook) -> None:
        """PL月次推移シートを作成"""
        if self.pl_suii_df is None:
            logger.warning("PL月次推移データがありません")
            return
        
        ws = wb.create_sheet(title="PL月次推移")
        
        # ページ設定（A3横）
        ws.page_setup.paperSize = ws.PAPERSIZE_A3
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 1
        ws.print_title_cols = 'A:A'  # A列を繰り返し印刷
        ws.page_margins = PageMargins(left=0.3, right=0.3, top=0.3, bottom=0.3)
        
        # タイトル
        row = 1
        ws.merge_cells(f'A{row}:D{row}')
        cell = ws.cell(row=row, column=1)
        cell.value = f"月次推移損益計算書 - 第{self.config.fiscal_year}期"
        cell.font = Font(bold=True, size=14)
        cell.alignment = Alignment(horizontal='left', vertical='center')
        ws.row_dimensions[row].height = 25
        row += 2
        
        # DataFrameをシートに書き込み
        self._write_dataframe_to_sheet(ws, self.pl_suii_df, start_row=row)
    
    def _build_bs(self, wb: Workbook) -> None:
        """貸借対照表シートを作成"""
        if self.bs_df is None:
            logger.warning("貸借対照表データがありません")
            return
        
        ws = wb.create_sheet(title="貸借対照表")
        
        # ページ設定（A4縦）
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.page_setup.orientation = 'portrait'
        ws.page_setup.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 1
        ws.page_margins = PageMargins(left=0.5, right=0.5, top=0.5, bottom=0.5)
        
        # タイトル
        row = 1
        ws.merge_cells(f'A{row}:D{row}')
        cell = ws.cell(row=row, column=1)
        cell.value = f"貸借対照表 - {self.config.target_year}年{self.config.target_month}月末時点"
        cell.font = Font(bold=True, size=14)
        cell.alignment = Alignment(horizontal='left', vertical='center')
        ws.row_dimensions[row].height = 25
        row += 2
        
        # DataFrameをシートに書き込み
        self._write_dataframe_to_sheet(ws, self.bs_df, start_row=row, is_bs=True)
    
    def _write_dataframe_to_sheet(
        self,
        ws,
        df: pd.DataFrame,
        start_row: int = 1,
        is_bs: bool = False
    ) -> None:
        """DataFrameをシートに書き込み"""
        # ヘッダー行
        for col_num, column_name in enumerate(df.columns, 1):
            cell = ws.cell(row=start_row, column=col_num)
            cell.value = column_name
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.border = self.thin_border
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        
        # データ行
        for row_idx, row_data in enumerate(df.itertuples(index=False), start_row + 1):
            for col_num, value in enumerate(row_data, 1):
                cell = ws.cell(row=row_idx, column=col_num)
                
                # 値の設定
                if pd.isna(value):
                    cell.value = ""
                elif isinstance(value, (int, float)):
                    cell.value = value
                    cell.number_format = '#,##0'
                else:
                    cell.value = str(value)
                
                cell.border = self.thin_border
                
                # 数値列は右寄せ
                if isinstance(value, (int, float)) and not pd.isna(value):
                    cell.alignment = Alignment(horizontal='right', vertical='center')
                else:
                    cell.alignment = Alignment(horizontal='left', vertical='center')
                
                # セクション行のスタイリング（BSの場合）
                if is_bs and col_num == 1:
                    str_value = str(value) if not pd.isna(value) else ""
                    if str_value in ['資産の部', '負債の部', '純資産の部', '流動資産', '固定資産', '流動負債', '固定負債']:
                        for c in range(1, len(df.columns) + 1):
                            ws.cell(row=row_idx, column=c).fill = self.section_fill
                            ws.cell(row=row_idx, column=c).font = Font(bold=True)
        
        # 列幅の自動調整
        for col_num in range(1, len(df.columns) + 1):
            column_letter = get_column_letter(col_num)
            max_length = len(str(df.columns[col_num - 1]))
            
            for row in ws.iter_rows(min_row=start_row, max_row=start_row + len(df), min_col=col_num, max_col=col_num):
                for cell in row:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
            
            # 日本語文字は幅が広いので調整
            adjusted_width = min(max_length * 1.5 + 2, 30)
            ws.column_dimensions[column_letter].width = adjusted_width
    
    # ==================== データ取得メソッド ====================
    
    def _get_value_from_suii(self, account_name: str, column_name: str) -> Optional[float]:
        """PL月次推移から値を取得"""
        if self.pl_suii_df is None:
            return None
        
        try:
            # 勘定科目列を探す
            account_col = None
            for col in self.pl_suii_df.columns:
                if '勘定科目' in str(col) or col == self.pl_suii_df.columns[0]:
                    account_col = col
                    break
            
            if account_col is None:
                return None
            
            # 該当行を検索
            mask = self.pl_suii_df[account_col].astype(str).str.contains(account_name, na=False)
            if mask.any():
                row = self.pl_suii_df[mask].iloc[0]
                # 列を探す
                for col in self.pl_suii_df.columns:
                    if column_name in str(col):
                        value = row[col]
                        if pd.notna(value):
                            return float(value)
            return None
        except Exception as e:
            logger.warning(f"値の取得に失敗: {account_name}, {column_name}, {e}")
            return None
    
    def _get_current_month_sales(self) -> Optional[float]:
        """当月売上高を取得"""
        return self._get_value_from_suii('売上高', f'{self.config.target_month}月')
    
    def _get_cumulative_sales(self) -> Optional[float]:
        """累計売上高を取得"""
        return self._get_value_from_suii('売上高', '合計')
    
    def _get_current_month_gross_profit(self) -> Optional[float]:
        """当月粗利益を取得"""
        return self._get_value_from_suii('粗利益', f'{self.config.target_month}月')
    
    def _get_cumulative_gross_profit(self) -> Optional[float]:
        """累計粗利益を取得"""
        return self._get_value_from_suii('粗利益', '合計')
    
    def _get_current_month_operating_profit(self) -> Optional[float]:
        """当月営業利益を取得"""
        return self._get_value_from_suii('営業利益', f'{self.config.target_month}月')
    
    def _get_cumulative_operating_profit(self) -> Optional[float]:
        """累計営業利益を取得"""
        return self._get_value_from_suii('営業利益', '合計')
    
    def _get_gross_profit_rate(self) -> Optional[float]:
        """粗利益率を計算"""
        sales = self._get_cumulative_sales()
        gross_profit = self._get_cumulative_gross_profit()
        if sales and gross_profit and sales != 0:
            return (gross_profit / sales) * 100
        return None
    
    def _get_operating_profit_rate(self) -> Optional[float]:
        """営業利益率を計算"""
        sales = self._get_cumulative_sales()
        operating_profit = self._get_cumulative_operating_profit()
        if sales and operating_profit and sales != 0:
            return (operating_profit / sales) * 100
        return None
    
    def _get_f_rate(self) -> Optional[float]:
        """原価率を計算"""
        sales = self._get_cumulative_sales()
        cost = self._get_value_from_suii('売上原価', '合計')
        if sales and cost and sales != 0:
            return (cost / sales) * 100
        return None
    
    def _get_l_rate(self) -> Optional[float]:
        """人件費率を計算"""
        sales = self._get_cumulative_sales()
        labor = self._get_value_from_suii('人件費', '合計')
        if sales and labor and sales != 0:
            return (labor / sales) * 100
        return None
    
    def _get_fl_rate(self) -> Optional[float]:
        """FL率を計算"""
        f_rate = self._get_f_rate()
        l_rate = self._get_l_rate()
        if f_rate is not None and l_rate is not None:
            return f_rate + l_rate
        return None
    
    def _get_value_from_bs(self, account_name: str) -> Optional[float]:
        """BSから値を取得"""
        if self.bs_df is None:
            return None
        
        try:
            # 勘定科目列を探す
            account_col = None
            for col in self.bs_df.columns:
                if '勘定科目' in str(col):
                    account_col = col
                    break
            
            if account_col is None:
                # 2番目の列を使用
                account_col = self.bs_df.columns[1] if len(self.bs_df.columns) > 1 else self.bs_df.columns[0]
            
            # 該当行を検索
            mask = self.bs_df[account_col].astype(str).str.contains(account_name, na=False)
            if mask.any():
                row = self.bs_df[mask].iloc[0]
                # 期末残高列を探す
                for col in self.bs_df.columns:
                    if '期末残高' in str(col):
                        value = row[col]
                        if pd.notna(value):
                            return float(value)
            return None
        except Exception as e:
            logger.warning(f"BS値の取得に失敗: {account_name}, {e}")
            return None
    
    def _get_current_ratio(self) -> Optional[float]:
        """流動比率を計算"""
        current_assets = self._get_value_from_bs('流動資産合計')
        current_liabilities = self._get_value_from_bs('流動負債合計')
        if current_assets and current_liabilities and current_liabilities != 0:
            return (current_assets / current_liabilities) * 100
        return None
    
    def _get_equity_ratio(self) -> Optional[float]:
        """自己資本比率を計算"""
        equity = self._get_value_from_bs('純資産合計')
        total_assets = self._get_value_from_bs('資産合計')
        if equity and total_assets and total_assets != 0:
            return (equity / total_assets) * 100
        return None
