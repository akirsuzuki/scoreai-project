"""
OCR機能関連のビュー
"""
from typing import Any, Dict
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.generic import FormView
from django.urls import reverse_lazy
import logging

from ..mixins import SelectedCompanyMixin, TransactionMixin
from ..models import FiscalSummary_Year, FiscalSummary_Month
from ..forms import OcrUploadForm
try:
    from ..utils.ocr import (
        extract_text_from_image,
        extract_text_from_pdf,
        parse_financial_statement_from_text
    )
except ImportError:
    # OCR機能が利用できない場合のフォールバック
    extract_text_from_image = None
    extract_text_from_pdf = None
    parse_financial_statement_from_text = None

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
        return context

    def form_valid(self, form):
        """フォームバリデーション成功時の処理"""
        # OCR機能が利用可能かチェック
        if extract_text_from_image is None or extract_text_from_pdf is None:
            messages.error(
                self.request,
                'OCR機能が利用できません。必要なライブラリがインストールされているか確認してください。'
            )
            return self.form_invalid(form)
        
        uploaded_file = form.cleaned_data['file']
        file_type = form.cleaned_data.get('file_type', 'auto')
        override_flag = form.cleaned_data.get('override_flag', False)
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
                    return self.form_invalid(form)

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
                return self.form_invalid(form)

            # テキストから決算書データをパース
            parsed_data = parse_financial_statement_from_text(extracted_text)

            # 年度の確定
            if not fiscal_year:
                fiscal_year = parsed_data.get('year')
                if not fiscal_year:
                    messages.error(
                        self.request,
                        '年度を自動検出できませんでした。手動で年度を入力してください。'
                    )
                    return self.form_invalid(form)

            # FiscalSummary_Yearの作成または取得
            fiscal_summary_year, created = FiscalSummary_Year.objects.get_or_create(
                year=fiscal_year,
                company=self.this_company,
                defaults={'is_draft': True}
            )

            if not created and not override_flag:
                messages.error(
                    self.request,
                    f'{fiscal_year}年のデータは既に存在します。上書きする場合は「既存データを上書きする」を選択してください。'
                )
                return self.form_invalid(form)

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
                self.request,
                f'OCR読み込みが完了しました。{fiscal_year}年のデータを更新しました。'
            )

            # 抽出されたテキストをログに記録（デバッグ用）
            logger.info(
                f"OCR extracted text (first 500 chars): {extracted_text[:500]}",
                extra={'user': self.request.user.id}
            )

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
            return self.form_invalid(form)

        return super().form_valid(form)

