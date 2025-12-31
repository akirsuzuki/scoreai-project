"""
利用状況レポート機能のビュー
"""
from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
import csv
import json

from ..models import Firm, FirmUsageTracking, FirmCompany, AIConsultationHistory
from ..mixins import ErrorHandlingMixin, FirmOwnerMixin
import logging

logger = logging.getLogger(__name__)


class UsageReportView(FirmOwnerMixin, TemplateView):
    """利用状況の詳細レポートビュー"""
    template_name = 'scoreai/usage_report.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = '利用状況レポート'
        context['firm'] = self.firm
        
        # 表示する月数を取得（デフォルト: 6ヶ月）
        months = int(self.request.GET.get('months', 6))
        months = max(1, min(months, 24))  # 1〜24ヶ月の範囲
        
        # 利用状況データを取得
        usage_data = self._get_usage_data(months)
        context['usage_data'] = usage_data
        context['months'] = months
        
        # グラフ用のデータを準備
        context['chart_data'] = json.dumps({
            'labels': usage_data['labels'],
            'ai_consultation': usage_data['ai_consultation'],
            'ocr': usage_data['ocr'],
        })
        
        return context
    
    def _get_usage_data(self, months: int) -> Dict[str, Any]:
        """利用状況データを取得"""
        now = timezone.now()
        labels = []
        ai_consultation = []
        ocr = []
        
        # 過去Nヶ月のデータを取得
        for i in range(months - 1, -1, -1):
            target_date = now - timedelta(days=30 * i)
            year = target_date.year
            month = target_date.month
            
            labels.append(f"{year}年{month}月")
            
            # 利用状況を取得
            usage = FirmUsageTracking.objects.filter(
                firm=self.firm,
                year=year,
                month=month
            ).first()
            
            if usage:
                ai_consultation.append(usage.ai_consultation_count)
                ocr.append(usage.ocr_count)
            else:
                ai_consultation.append(0)
                ocr.append(0)
        
        # テーブル表示用のデータを準備（最新のものから表示）
        table_data = []
        for i in range(len(labels) - 1, -1, -1):
            table_data.append({
                'label': labels[i],
                'ai_consultation': ai_consultation[i],
                'ocr': ocr[i],
            })
        
        return {
            'labels': labels,
            'ai_consultation': ai_consultation,
            'ocr': ocr,
            'table_data': table_data,
        }


class UsageReportExportView(FirmOwnerMixin, TemplateView):
    """利用状況レポートのエクスポートビュー"""
    
    def get(self, request, firm_id, format='csv'):
        """CSVまたはExcel形式でエクスポート"""
        months = int(request.GET.get('months', 6))
        months = max(1, min(months, 24))
        
        if format == 'csv':
            return self._export_csv(months)
        else:
            return JsonResponse({'error': 'Unsupported format'}, status=400)
    
    def _export_csv(self, months: int) -> HttpResponse:
        """CSV形式でエクスポート"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="usage_report_{self.firm.id}_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        # BOMを追加してExcelで正しく開けるようにする
        response.write('\ufeff')
        
        writer = csv.writer(response)
        
        # ヘッダー
        writer.writerow(['年月', 'AI相談回数', 'OCR読み込み回数'])
        
        # データ
        now = timezone.now()
        for i in range(months - 1, -1, -1):
            target_date = now - timedelta(days=30 * i)
            year = target_date.year
            month = target_date.month
            
            usage = FirmUsageTracking.objects.filter(
                firm=self.firm,
                year=year,
                month=month
            ).first()
            
            if usage:
                writer.writerow([
                    f"{year}年{month}月",
                    usage.ai_consultation_count,
                    usage.ocr_count,
                ])
            else:
                writer.writerow([
                    f"{year}年{month}月",
                    0,
                    0,
                ])
        
        return response


class CompanyUsageReportView(FirmOwnerMixin, TemplateView):
    """Company別の利用状況レポートビュー"""
    template_name = 'scoreai/company_usage_report.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        company_id = kwargs.get('company_id')
        
        # Companyを取得
        from ..models import Company
        company = FirmCompany.objects.filter(
            firm=self.firm,
            company_id=company_id,
            active=True
        ).select_related('company').first()
        
        if not company:
            from django.http import Http404
            raise Http404("Company not found")
        
        context['title'] = f'{company.company.name} - 利用状況'
        context['firm'] = self.firm
        context['company'] = company.company
        
        # 表示する月数を取得（デフォルト: 6ヶ月）
        months = int(self.request.GET.get('months', 6))
        months = max(1, min(months, 24))
        
        # 利用状況データを取得
        usage_data = self._get_company_usage_data(company.company, months)
        context['usage_data'] = usage_data
        context['months'] = months
        
        # グラフ用のデータを準備
        context['chart_data'] = json.dumps({
            'labels': usage_data['labels'],
            'ai_consultation': usage_data['ai_consultation'],
            'ocr': usage_data['ocr'],
        })
        
        return context
    
    def _get_company_usage_data(self, company, months: int) -> Dict[str, Any]:
        """Company別の利用状況データを取得"""
        now = timezone.now()
        labels = []
        ai_consultation = []
        ocr = []
        
        # 過去Nヶ月のデータを取得
        for i in range(months - 1, -1, -1):
            target_date = now - timedelta(days=30 * i)
            year = target_date.year
            month = target_date.month
            
            labels.append(f"{year}年{month}月")
            
            # AI相談回数を取得
            ai_count = AIConsultationHistory.objects.filter(
                company=company,
                created_at__year=year,
                created_at__month=month
            ).count()
            
            ai_consultation.append(ai_count)
            
            # OCR回数は現時点ではCompany別に追跡していないため、0を返す
            # 将来的にOCR履歴テーブルができたら実装
            ocr.append(0)
        
        return {
            'labels': labels,
            'ai_consultation': ai_consultation,
            'ocr': ocr,
        }

