"""
OCR機能関連のビュー
"""
from typing import Any, Dict, Optional
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.generic import FormView
from django.urls import reverse_lazy
from django.utils import timezone
from io import BytesIO
import logging

from ..mixins import SelectedCompanyMixin, TransactionMixin
from ..models import (
    FiscalSummary_Year, FiscalSummary_Month, Debt, FinancialInstitution, SecuredType,
    CloudStorageSetting, UploadedDocument
)
from ..forms import OcrUploadForm
from ..utils.document_naming import generate_document_filename, get_folder_path
try:
    from ..utils.ocr import (
        extract_text_from_image,
        extract_text_from_pdf,
        parse_financial_statement_from_text,
        parse_loan_contract_from_text
    )
except ImportError:
    # OCR機能が利用できない場合のフォールバック
    extract_text_from_image = None
    extract_text_from_pdf = None
    parse_financial_statement_from_text = None
    parse_loan_contract_from_text = None

logger = logging.getLogger(__name__)


class ImportFiscalSummaryFromOcrView(SelectedCompanyMixin, TransactionMixin, FormView):
    """OCRを使用した決算書インポートビュー"""
    template_name = 'scoreai/import_fiscal_summary_ocr.html'
    form_class = OcrUploadForm
    success_url = reverse_lazy('fiscal_summary_year_list')

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = '決算書OCR読み込み'
        
        # プレビューデータがセッションに保存されている場合は取得
        if 'ocr_preview_data' in self.request.session:
            context['preview_data'] = self.request.session['ocr_preview_data']
            context['preview_file_name'] = self.request.session.get('ocr_preview_file_name', '')
            context['preview_fiscal_year'] = self.request.session.get('ocr_preview_fiscal_year')
        
        return context

    def _process_ocr(self, form) -> Dict[str, Any]:
        """
        OCR処理を実行してパース結果を返す
        
        Returns:
            パースされたデータの辞書。エラー時はNone
        """
        # OCR機能が利用可能かチェック
        if extract_text_from_image is None or extract_text_from_pdf is None:
            messages.error(
                self.request,
                'OCR機能が利用できません。必要なライブラリがインストールされているか確認してください。'
            )
            return None
        
        uploaded_file = form.cleaned_data['file']
        file_type = form.cleaned_data.get('file_type', 'auto')
        document_type = form.cleaned_data.get('document_type', 'financial_statement')
        fiscal_year = form.cleaned_data.get('fiscal_year')

        try:
            # ファイルタイプの判定
            if file_type == 'auto':
                # ファイル名から拡張子を判定
                file_name = uploaded_file.name.lower()
                if file_name.endswith('.pdf'):
                    file_type = 'pdf'
                elif file_name.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    file_type = 'image'
                else:
                    messages.error(
                        self.request,
                        'サポートされていないファイル形式です。PDFまたは画像ファイルをアップロードしてください。'
                    )
                    return None

            # OCRでテキストを抽出
            if file_type == 'pdf':
                extracted_text = extract_text_from_pdf(uploaded_file)
            else:
                extracted_text = extract_text_from_image(uploaded_file)

            if not extracted_text:
                messages.error(
                    self.request,
                    'テキストの抽出に失敗しました。画像の品質を確認してください。'
                )
                return None

            # 書類タイプに応じてパース
            if document_type == 'loan_contract':
                # 金銭消費貸借契約書をパース
                parsed_data = parse_loan_contract_from_text(extracted_text)
                parsed_data['document_type'] = 'loan_contract'
            else:
                # 決算書をパース
                parsed_data = parse_financial_statement_from_text(extracted_text)
                parsed_data['document_type'] = 'financial_statement'
                
                # 年度の確定
                if not fiscal_year:
                    fiscal_year = parsed_data.get('year')
                    if not fiscal_year:
                        messages.error(
                            self.request,
                            '年度を自動検出できませんでした。手動で年度を入力してください。'
                        )
                        return None
                
                parsed_data['fiscal_year'] = fiscal_year
            
            parsed_data['extracted_text_preview'] = extracted_text[:500]  # プレビュー用に最初の500文字
            
            return parsed_data

        except Exception as e:
            logger.error(
                f"OCR processing error: {e}",
                exc_info=True,
                extra={'user': self.request.user.id}
            )
            messages.error(
                self.request,
                f'OCR処理中にエラーが発生しました: {str(e)}'
            )
            return None

    def post(self, request, *args, **kwargs):
        """POSTリクエストの処理"""
        action = request.POST.get('action', 'preview')
        
        # 保存アクションでセッションにデータがある場合は、フォームバリデーションをスキップ
        if action == 'save' and 'ocr_preview_data' in request.session:
            # セッションからデータを取得して直接保存処理を実行
            parsed_data = request.session['ocr_preview_data']
            document_type = parsed_data.get('document_type', 'financial_statement')
            override_flag = request.session.get('ocr_preview_override_flag', False)
            
            # ファイルを再取得（フォームから）
            uploaded_file = request.FILES.get('file')
            if uploaded_file:
                request.session['ocr_uploaded_file'] = uploaded_file
            
            try:
                if document_type == 'loan_contract':
                    # 金銭消費貸借契約書の保存
                    return self._save_loan_contract(request, parsed_data, override_flag)
                else:
                    # 決算書の保存
                    fiscal_year = request.session.get('ocr_preview_fiscal_year')
                    return self._save_financial_statement(request, parsed_data, fiscal_year, override_flag)

            except Exception as e:
                logger.error(
                    f"OCR save error: {e}",
                    exc_info=True,
                    extra={'user': request.user.id}
                )
                messages.error(
                    request,
                    f'データの保存中にエラーが発生しました: {str(e)}'
                )
                return self.get(request, *args, **kwargs)
        
        # 通常のフォーム処理
        return super().post(request, *args, **kwargs)
    
    def _save_financial_statement(self, request, parsed_data, fiscal_year, override_flag):
        """決算書データの保存"""
        # FiscalSummary_Yearの作成または取得
        fiscal_summary_year, created = FiscalSummary_Year.objects.get_or_create(
            year=fiscal_year,
            company=self.this_company,
            defaults={'is_draft': True}
        )

        if not created and not override_flag:
            messages.error(
                request,
                f'{fiscal_year}年のデータは既に存在します。上書きする場合は「既存データを上書きする」を選択してください。'
            )
            # セッションをクリア
            if 'ocr_preview_data' in request.session:
                del request.session['ocr_preview_data']
            return self.get(request)

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

        messages.success(
            request,
            f'OCR読み込みが完了しました。{fiscal_year}年のデータを更新しました。'
        )

        # Google Driveにファイルを保存（オプション）
        uploaded_file = request.FILES.get('file') or request.session.get('ocr_uploaded_file')
        if uploaded_file:
            self._save_to_cloud_storage(
                request,
                uploaded_file,
                'financial_statement',
                None,
                fiscal_year=fiscal_year,
                fiscal_month=None
            )

        # セッションをクリア
        self._clear_session(request)

        return redirect(self.success_url)
    
    def _save_loan_contract(self, request, parsed_data, override_flag):
        """金銭消費貸借契約書データの保存"""
        from decimal import Decimal
        
        # 必須フィールドのチェック
        if not parsed_data.get('financial_institution_name'):
            messages.error(
                request,
                '金融機関名が検出できませんでした。手動で入力してください。'
            )
            return self.get(request)
        
        if not parsed_data.get('principal'):
            messages.error(
                request,
                '借入元本が検出できませんでした。手動で入力してください。'
            )
            return self.get(request)
        
        # 金融機関の取得または作成
        financial_institution, _ = FinancialInstitution.objects.get_or_create(
            name=parsed_data['financial_institution_name'],
            defaults={
                'short_name': parsed_data['financial_institution_name'][:24],
                'JBAcode': '000000',  # デフォルト値
                'bank_category': 'その他',
            }
        )
        
        # デフォルトの保証協会を取得（最初のものを使用）
        secured_type = SecuredType.objects.first()
        if not secured_type:
            messages.error(
                request,
                '保証協会が登録されていません。先に保証協会を登録してください。'
            )
            return self.get(request)
        
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
        
        messages.success(
            request,
            f'OCR読み込みが完了しました。金銭消費貸借契約書のデータを登録しました。'
        )

        # Google Driveにファイルを保存（オプション）
        uploaded_file = request.FILES.get('file')
        if uploaded_file:
            self._save_to_cloud_storage(
                request,
                uploaded_file,
                'loan_contract',
                None,
                financial_institution_name=parsed_data.get('financial_institution_name')
            )

        # セッションをクリア
        self._clear_session(request)

        return redirect('debt_detail', pk=debt.id)
    
    def _clear_session(self, request):
        """セッションデータをクリア"""
        if 'ocr_preview_data' in request.session:
            del request.session['ocr_preview_data']
        if 'ocr_preview_file_name' in request.session:
            del request.session['ocr_preview_file_name']
        if 'ocr_preview_fiscal_year' in request.session:
            del request.session['ocr_preview_fiscal_year']
        if 'ocr_preview_override_flag' in request.session:
            del request.session['ocr_preview_override_flag']

    def form_valid(self, form):
        """フォームバリデーション成功時の処理"""
        action = self.request.POST.get('action', 'preview')
        
        # OCR処理を実行
        parsed_data = self._process_ocr(form)
        
        if parsed_data is None:
            return self.form_invalid(form)
        
        document_type = parsed_data.get('document_type', 'financial_statement')
        override_flag = form.cleaned_data.get('override_flag', False)
        
        # プレビューモードの場合
        if action == 'preview':
            # セッションにプレビューデータを保存
            self.request.session['ocr_preview_data'] = parsed_data
            self.request.session['ocr_preview_file_name'] = form.cleaned_data['file'].name
            # ファイルをセッションに保存（バイナリデータは大きいので、ファイル名のみ保存）
            # 実際のファイルは後で再取得する必要があるため、ファイル名とパスを保存
            if document_type == 'financial_statement':
                self.request.session['ocr_preview_fiscal_year'] = parsed_data.get('fiscal_year')
            self.request.session['ocr_preview_override_flag'] = override_flag
            # ファイル情報をセッションに保存（後でGoogle Driveに保存するため）
            self.request.session['ocr_uploaded_file_name'] = form.cleaned_data['file'].name
            self.request.session['ocr_document_type'] = document_type
            
            messages.info(
                self.request,
                'OCR処理が完了しました。以下のプレビューを確認して、問題なければ「保存する」ボタンをクリックしてください。'
            )
            
            # フォームを再表示（プレビューデータ付き）
            return self.form_invalid(form)  # form_invalidを呼んでテンプレートを再表示
        
        # 保存モードの場合（セッションにデータがない場合のみ）
        elif action == 'save':
            # セッションにデータがない場合は再処理
            parsed_data = self._process_ocr(form)
            if parsed_data is None:
                return self.form_invalid(form)
            
            document_type = parsed_data.get('document_type', 'financial_statement')
            override_flag = form.cleaned_data.get('override_flag', False)
            
            try:
                if document_type == 'loan_contract':
                    # 金銭消費貸借契約書の保存
                    return self._save_loan_contract(self.request, parsed_data, override_flag)
                else:
                    # 決算書の保存
                    fiscal_year = parsed_data.get('fiscal_year')
                    return self._save_financial_statement(self.request, parsed_data, fiscal_year, override_flag)
            
            except Exception as e:
                logger.error(
                    f"OCR save error: {e}",
                    exc_info=True,
                    extra={'user': self.request.user.id}
                )
                messages.error(
                    self.request,
                    f'データの保存中にエラーが発生しました: {str(e)}'
                )
                return self.form_invalid(form)
        
        # その他のアクション
        return self.form_invalid(form)
    
    def _save_to_cloud_storage(
        self,
        request,
        uploaded_file,
        document_type: str,
        subfolder_type: Optional[str] = None,
        fiscal_year: Optional[int] = None,
        fiscal_month: Optional[int] = None,
        financial_institution_name: Optional[str] = None,
        contract_partner: Optional[str] = None
    ) -> Optional[UploadedDocument]:
        """
        アップロードされたファイルをクラウドストレージに保存
        
        Returns:
            UploadedDocumentオブジェクト、またはNone（保存失敗時）
        """
        try:
            # クラウドストレージ設定を取得
            try:
                storage_setting = CloudStorageSetting.objects.get(
                    user=request.user,
                    is_active=True
                )
            except CloudStorageSetting.DoesNotExist:
                logger.info(f"Cloud storage not configured for user {request.user.id}")
                return None
            
            # Google Driveのみ対応（他のストレージは今後実装）
            if storage_setting.storage_type != 'google_drive':
                logger.info(f"Storage type {storage_setting.storage_type} not yet supported")
                return None
            
            # Google Driveアダプターを初期化
            from ..utils.storage.google_drive import GoogleDriveAdapter
            
            adapter = GoogleDriveAdapter(
                user=request.user,
                access_token=storage_setting.access_token,
                refresh_token=storage_setting.refresh_token
            )
            
            # ファイル名を自動生成
            file_extension = uploaded_file.name.split('.')[-1] if '.' in uploaded_file.name else 'pdf'
            stored_filename = generate_document_filename(
                company=self.this_company,
                document_type=document_type,
                subfolder_type=subfolder_type,
                fiscal_year=fiscal_year,
                fiscal_month=fiscal_month,
                financial_institution_name=financial_institution_name,
                contract_partner=contract_partner,
                file_extension=file_extension
            )
            
            # フォルダパスを取得
            folder_path = get_folder_path(document_type, subfolder_type)
            
            # フォルダを取得または作成
            root_folder_id = storage_setting.root_folder_id or None
            folder_info = adapter.get_or_create_folder(folder_path, root_folder_id)
            
            # ファイルをアップロード
            # ファイルをメモリに読み込む
            uploaded_file.seek(0)  # ファイルポインタを先頭に戻す
            file_content = BytesIO(uploaded_file.read())
            file_content.seek(0)
            
            # MIMEタイプを判定
            mime_type = 'application/pdf' if file_extension.lower() == 'pdf' else f'image/{file_extension.lower()}'
            
            # アップロード
            uploaded_file_info = adapter.upload_file(
                file_content=file_content,
                filename=stored_filename,
                folder_id=folder_info['id'],
                mime_type=mime_type
            )
            
            # UploadedDocumentレコードを作成
            uploaded_doc = UploadedDocument.objects.create(
                user=request.user,
                company=self.this_company,
                document_type=document_type,
                subfolder_type=subfolder_type or '',
                original_filename=uploaded_file.name,
                stored_filename=stored_filename,
                storage_type=storage_setting.storage_type,
                file_id=uploaded_file_info['id'],
                folder_id=folder_info['id'],
                file_url=uploaded_file_info.get('webViewLink', ''),
                file_size=uploaded_file.size if hasattr(uploaded_file, 'size') else None,
                mime_type=mime_type,
                is_ocr_processed=True,
                ocr_processed_at=timezone.now(),
            )
            
            logger.info(
                f"File uploaded to cloud storage: {stored_filename} (user: {request.user.id}, company: {self.this_company.id})"
            )
            
            messages.success(
                request,
                f'ファイルを{storage_setting.get_storage_type_display()}に保存しました: {stored_filename}'
            )
            
            return uploaded_doc
            
        except Exception as e:
            logger.error(
                f"Failed to save file to cloud storage: {e}",
                exc_info=True,
                extra={'user': request.user.id}
            )
            # エラーはログに記録するが、ユーザーには通知しない（OCR処理自体は成功しているため）
            return None

