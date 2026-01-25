"""
財務会議資料生成ビュー
"""
import logging
from datetime import datetime
from io import BytesIO
from typing import Any, Dict

from django.http import HttpResponse
from django.views.generic import FormView
from django.contrib import messages
from django.utils import timezone

from ..mixins import SelectedCompanyMixin
from ..forms import FinancialReportForm
from ..models import CloudStorageSetting
from ..services.financial_report_generator import FinancialReportGenerator, ReportConfig

logger = logging.getLogger(__name__)


class FinancialReportView(SelectedCompanyMixin, FormView):
    """財務会議資料生成ビュー"""
    template_name = 'scoreai/financial_report_form.html'
    form_class = FinancialReportForm
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = '財務会議資料生成'
        context['show_title_card'] = False
        context['company'] = self.this_company
        
        # クラウドストレージ連携状況を取得
        try:
            storage_setting = CloudStorageSetting.objects.get(
                user=self.request.user,
                company=self.this_company,
                is_active=True
            )
            context['storage_connected'] = True
            context['storage_type'] = storage_setting.get_storage_type_display()
        except CloudStorageSetting.DoesNotExist:
            context['storage_connected'] = False
            context['storage_type'] = None
        
        # デフォルト値を設定
        now = timezone.now()
        context['default_year'] = now.year
        context['default_month'] = now.month
        
        return context
    
    def get_initial(self):
        """フォームの初期値を設定"""
        initial = super().get_initial()
        now = timezone.now()
        initial['target_year'] = now.year
        initial['target_month'] = now.month
        return initial
    
    def form_valid(self, form):
        """フォームが有効な場合の処理"""
        try:
            # ReportConfigを作成
            config = ReportConfig(
                company_name=self.this_company.name,
                target_month=form.cleaned_data['target_month'],
                target_year=form.cleaned_data['target_year'],
                target_f_rate=float(form.cleaned_data.get('target_f_rate') or 30) / 100,
                target_l_rate=float(form.cleaned_data.get('target_l_rate') or 30) / 100,
                target_fl_rate=float(form.cleaned_data.get('target_fl_rate') or 60) / 100,
                target_current_ratio=float(form.cleaned_data.get('target_current_ratio') or 200),
                target_equity_ratio=float(form.cleaned_data.get('target_equity_ratio') or 30),
            )
            
            # ジェネレーターを作成
            generator = FinancialReportGenerator(config)
            
            # CSVファイルを読み込み
            generator.load_data(
                pl_bumon_file=form.cleaned_data['pl_bumon_file'],
                pl_bumon_zenki_file=form.cleaned_data.get('pl_bumon_zenki_file'),
                pl_suii_file=form.cleaned_data['pl_suii_file'],
                pl_suii_zenki_file=form.cleaned_data.get('pl_suii_zenki_file'),
                bs_file=form.cleaned_data['bs_file'],
            )
            
            # Excel生成
            excel_output = generator.generate()
            
            # ファイル名を生成
            filename = self._generate_filename(config)
            
            # クラウドストレージに保存（連携している場合）
            self._save_to_cloud_storage(excel_output, filename)
            
            # ダウンロードレスポンスを作成
            excel_output.seek(0)
            response = HttpResponse(
                excel_output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except ValueError as e:
            logger.error(f"財務会議資料生成エラー: {e}")
            messages.error(self.request, f'CSVファイルの読み込みエラー: {e}')
            return self.form_invalid(form)
        except Exception as e:
            logger.exception(f"財務会議資料生成で予期しないエラー: {e}")
            messages.error(self.request, f'レポート生成中にエラーが発生しました: {e}')
            return self.form_invalid(form)
    
    def _generate_filename(self, config: ReportConfig) -> str:
        """ファイル名を生成"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        company_name = self.this_company.name.replace(' ', '_').replace('/', '_')
        return f"財務会議資料_{company_name}_{config.target_year}年{config.target_month}月_{timestamp}.xlsx"
    
    def _save_to_cloud_storage(self, excel_output: BytesIO, filename: str) -> None:
        """クラウドストレージに保存"""
        try:
            storage_setting = CloudStorageSetting.objects.get(
                user=self.request.user,
                company=self.this_company,
                is_active=True
            )
        except CloudStorageSetting.DoesNotExist:
            logger.info("クラウドストレージ連携なし - ダウンロードのみ")
            return
        
        try:
            # ファイル内容を取得
            excel_output.seek(0)
            file_content = excel_output.read()
            excel_output.seek(0)  # 元に戻す
            
            if storage_setting.storage_type == 'google_drive':
                from ..utils.storage.google_drive import GoogleDriveAdapter
                
                adapter = GoogleDriveAdapter(
                    user=self.request.user,
                    access_token=storage_setting.access_token,
                    refresh_token=storage_setting.refresh_token
                )
                
                # ルートフォルダを取得
                root_folder_id = storage_setting.root_folder_id
                if not root_folder_id:
                    logger.warning("Google Driveルートフォルダが設定されていません")
                    return
                
                # 「財務会議資料」フォルダを取得または作成
                folder_name = "財務会議資料"
                folder = adapter.get_or_create_folder(folder_name, root_folder_id)
                
                # ファイルをアップロード
                uploaded_file = adapter.upload_file(
                    file_content=file_content,
                    filename=filename,
                    folder_id=folder['id'],
                    mime_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
                logger.info(f"Google Driveにファイルをアップロードしました: {uploaded_file.get('id')}")
                messages.success(self.request, f'Google Driveに保存しました: {folder_name}/{filename}')
                
            elif storage_setting.storage_type == 'box':
                from ..utils.storage.box import BoxAdapter
                
                adapter = BoxAdapter(
                    user=self.request.user,
                    access_token=storage_setting.access_token,
                    refresh_token=storage_setting.refresh_token
                )
                
                # ルートフォルダを取得
                root_folder_id = storage_setting.root_folder_id
                if not root_folder_id:
                    logger.warning("Boxルートフォルダが設定されていません")
                    return
                
                # 「財務会議資料」フォルダを取得または作成
                folder_name = "財務会議資料"
                folder = adapter.get_or_create_folder(folder_name, root_folder_id)
                
                # ファイルをアップロード
                uploaded_file = adapter.upload_file(
                    file_content=file_content,
                    filename=filename,
                    folder_id=folder['id']
                )
                
                logger.info(f"Boxにファイルをアップロードしました: {uploaded_file.get('id')}")
                messages.success(self.request, f'Boxに保存しました: {folder_name}/{filename}')
                
            else:
                logger.info(f"未対応のストレージタイプ: {storage_setting.storage_type}")
                
        except Exception as e:
            logger.error(f"クラウドストレージへの保存に失敗: {e}")
            messages.warning(self.request, f'クラウドストレージへの保存に失敗しました（ダウンロードは正常に行われます）: {e}')
