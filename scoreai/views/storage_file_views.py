"""
ストレージからのファイル読み込み関連のビュー
"""
from typing import Any, Dict
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, View
from django.http import JsonResponse
from io import BytesIO
import logging

from ..mixins import SelectedCompanyMixin, TransactionMixin
from ..models import CloudStorageSetting, UploadedDocument
from ..utils.storage.google_drive import GoogleDriveAdapter
from ..utils.storage.box import BoxAdapter
from ..utils.ocr import (
    extract_text_from_image,
    extract_text_from_pdf,
    parse_financial_statement_from_text,
    parse_loan_contract_from_text
)

logger = logging.getLogger(__name__)


class StorageFileListView(SelectedCompanyMixin, LoginRequiredMixin, ListView):
    """ストレージ内のファイル一覧"""
    template_name = 'scoreai/storage_file_list.html'
    context_object_name = 'files'
    paginate_by = 20
    
    def get_queryset(self):
        """アップロード済みドキュメントを取得"""
        return UploadedDocument.objects.filter(
            user=self.request.user,
            company=self.this_company
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = 'ストレージファイル一覧'
        
        # ストレージ設定を取得（選択中のCompanyに基づく）
        try:
            storage_setting = CloudStorageSetting.objects.get(
                user=self.request.user,
                company=self.this_company,
                is_active=True
            )
            context['storage_setting'] = storage_setting
        except CloudStorageSetting.DoesNotExist:
            context['storage_setting'] = None
        
        return context


class StorageFileProcessView(SelectedCompanyMixin, TransactionMixin, LoginRequiredMixin, View):
    """ストレージからファイルをダウンロードしてOCR処理"""
    
    def post(self, request, *args, **kwargs):
        """ファイルをダウンロードしてOCR処理"""
        file_id = request.POST.get('file_id')
        document_id = request.POST.get('document_id')
        
        if not file_id and not document_id:
            messages.error(request, 'ファイルIDまたはドキュメントIDが必要です。')
            return redirect('storage_file_list')
        
        try:
            # UploadedDocumentからファイル情報を取得
            if document_id:
                uploaded_doc = get_object_or_404(
                    UploadedDocument,
                    id=document_id,
                    user=request.user,
                    company=self.this_company
                )
                file_id = uploaded_doc.file_id
                document_type = uploaded_doc.document_type
            else:
                uploaded_doc = None
                document_type = request.POST.get('document_type', 'financial_statement')
            
            # ストレージ設定を取得（選択中のCompanyに基づく）
            storage_setting = CloudStorageSetting.objects.get(
                user=request.user,
                company=self.this_company,
                is_active=True
            )
            
            # ストレージアダプターを初期化
            if storage_setting.storage_type == 'google_drive':
                adapter = GoogleDriveAdapter(
                    user=request.user,
                    access_token=storage_setting.access_token,
                    refresh_token=storage_setting.refresh_token
                )
            elif storage_setting.storage_type == 'box':
                adapter = BoxAdapter(
                    user=request.user,
                    access_token=storage_setting.access_token,
                    refresh_token=storage_setting.refresh_token
                )
            else:
                messages.error(request, f'ストレージタイプ {storage_setting.get_storage_type_display()} はまだサポートされていません。')
                return redirect('storage_file_list')
            
            # ファイル情報を取得
            file_info = adapter.get_file_info(file_id)
            
            # ファイルをダウンロード
            file_content = adapter.download_file(file_id)
            
            # ファイルをBytesIOに変換
            file_io = BytesIO(file_content)
            file_io.name = file_info['name']
            
            # MIMEタイプからファイルタイプを判定
            mime_type = file_info.get('mimeType', '')
            if mime_type == 'application/pdf':
                file_type = 'pdf'
            elif mime_type.startswith('image/'):
                file_type = 'image'
            else:
                # ファイル名から拡張子を判定
                file_name = file_info['name'].lower()
                if file_name.endswith('.pdf'):
                    file_type = 'pdf'
                elif file_name.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    file_type = 'image'
                else:
                    messages.error(request, 'サポートされていないファイル形式です。')
                    return redirect('storage_file_list')
            
            # OCRでテキストを抽出
            if file_type == 'pdf':
                extracted_text = extract_text_from_pdf(file_io)
            else:
                extracted_text = extract_text_from_image(file_io)
            
            if not extracted_text:
                messages.error(request, 'テキストの抽出に失敗しました。')
                return redirect('storage_file_list')
            
            # 書類タイプに応じてパース
            if document_type == 'loan_contract':
                parsed_data = parse_loan_contract_from_text(extracted_text)
                parsed_data['document_type'] = 'loan_contract'
                
                # 金銭消費貸借契約書の保存処理
                return self._save_loan_contract_from_storage(request, parsed_data, uploaded_doc)
            else:
                parsed_data = parse_financial_statement_from_text(extracted_text)
                parsed_data['document_type'] = 'financial_statement'
                
                # 年度の取得
                fiscal_year = request.POST.get('fiscal_year')
                if not fiscal_year:
                    fiscal_year = parsed_data.get('year')
                
                if not fiscal_year:
                    messages.error(request, '年度を指定してください。')
                    return redirect('storage_file_list')
                
                # 決算書の保存処理
                return self._save_financial_statement_from_storage(
                    request, parsed_data, int(fiscal_year), uploaded_doc
                )
        
        except Exception as e:
            logger.error(
                f"Storage file processing error: {e}",
                exc_info=True,
                extra={'user': request.user.id}
            )
            messages.error(request, f'ファイル処理中にエラーが発生しました: {str(e)}')
            return redirect('storage_file_list')
    
    def _save_financial_statement_from_storage(self, request, parsed_data, fiscal_year, uploaded_doc):
        """ストレージから取得した決算書データを保存"""
        from ..models import FiscalSummary_Year
        
        # FiscalSummary_Yearの作成または取得
        # versionは常に1で固定（defaultsに含めない、モデルのdefault=1が適用される）
        fiscal_summary_year, created = FiscalSummary_Year.objects.get_or_create(
            year=fiscal_year,
            company=self.this_company,
            is_budget=False,  # 実績データとして明示的に指定
            defaults={'is_draft': True}
        )
        
        # データの更新
        update_fields = {}
        if parsed_data.get('sales'):
            update_fields['sales'] = parsed_data['sales']
        if parsed_data.get('gross_profit'):
            update_fields['gross_profit'] = parsed_data['gross_profit']
        if parsed_data.get('operating_profit'):
            update_fields['operating_profit'] = parsed_data['operating_profit']
        if parsed_data.get('ordinary_profit'):
            update_fields['ordinary_profit'] = parsed_data['ordinary_profit']
        if parsed_data.get('net_profit'):
            update_fields['net_profit'] = parsed_data['net_profit']
        
        if update_fields:
            for field, value in update_fields.items():
                setattr(fiscal_summary_year, field, value)
            fiscal_summary_year.save()
        
        # UploadedDocumentを更新
        if uploaded_doc:
            uploaded_doc.is_data_saved = True
            uploaded_doc.saved_to_model = 'FiscalSummary_Year'
            uploaded_doc.saved_record_id = fiscal_summary_year.id
            uploaded_doc.save()
        
        messages.success(
            request,
            f'OCR読み込みが完了しました。{fiscal_year}年のデータを更新しました。'
        )
        
        return redirect('fiscal_summary_year_list')
    
    def _save_loan_contract_from_storage(self, request, parsed_data, uploaded_doc):
        """ストレージから取得した金銭消費貸借契約書データを保存"""
        from decimal import Decimal
        from ..models import Debt, FinancialInstitution, SecuredType
        
        # 必須フィールドのチェック
        if not parsed_data.get('financial_institution_name'):
            messages.error(request, '金融機関名が検出できませんでした。')
            return redirect('storage_file_list')
        
        if not parsed_data.get('principal'):
            messages.error(request, '借入元本が検出できませんでした。')
            return redirect('storage_file_list')
        
        # 金融機関の取得または作成
        financial_institution, _ = FinancialInstitution.objects.get_or_create(
            name=parsed_data['financial_institution_name'],
            defaults={
                'short_name': parsed_data['financial_institution_name'][:24],
                'JBAcode': '000000',
                'bank_category': 'その他',
            }
        )
        
        # デフォルトの保証協会を取得
        secured_type = SecuredType.objects.first()
        if not secured_type:
            messages.error(request, '保証協会が登録されていません。')
            return redirect('storage_file_list')
        
        # Debtオブジェクトの作成
        debt = Debt(
            company=self.this_company,
            financial_institution=financial_institution,
            principal=parsed_data.get('principal', 0),
            issue_date=parsed_data.get('issue_date') or self.this_company.created_at.date(),
            start_date=parsed_data.get('start_date') or self.this_company.created_at.date(),
            interest_rate=Decimal(str(parsed_data.get('interest_rate', 0))),
            monthly_repayment=parsed_data.get('monthly_repayment', 0),
            is_securedby_management=parsed_data.get('is_securedby_management', False),
            is_collateraled=parsed_data.get('is_collateraled', False),
            secured_type=secured_type,
        )
        debt.save()
        
        # UploadedDocumentを更新
        if uploaded_doc:
            uploaded_doc.is_data_saved = True
            uploaded_doc.saved_to_model = 'Debt'
            uploaded_doc.saved_record_id = debt.id
            uploaded_doc.save()
        
        messages.success(request, 'OCR読み込みが完了しました。金銭消費貸借契約書のデータを登録しました。')
        
        return redirect('debt_detail', pk=debt.id)

