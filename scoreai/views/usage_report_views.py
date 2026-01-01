"""
利用状況レポート機能のビュー
"""
from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
from calendar import monthrange
import csv
import json

from ..models import Firm, FirmUsageTracking, FirmCompany, AIConsultationHistory, Company
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
        
        # 各Companyごとの利用数を取得
        company_usage = self._get_company_usage_summary(months)
        context['company_usage'] = company_usage
        
        return context
    
    def _get_usage_data(self, months: int) -> Dict[str, Any]:
        """利用状況データを取得"""
        now = timezone.now()
        labels = []
        ai_consultation = []
        ocr = []
        
        # 過去Nヶ月のデータを取得（重複を避けるため、年月のセットを使用）
        seen_months = set()
        month_data_list = []
        
        # 現在の月から過去Nヶ月を正確に計算
        current_year = now.year
        current_month = now.month
        
        for i in range(months):
            # 過去iヶ月前の年月を計算
            target_year = current_year
            target_month = current_month - i
            
            # 月が0以下になった場合の処理
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            
            # 重複チェック
            month_key = (target_year, target_month)
            if month_key in seen_months:
                continue
            seen_months.add(month_key)
            
            # 利用状況を取得
            usage = FirmUsageTracking.objects.filter(
                firm=self.firm,
                year=target_year,
                month=target_month
            ).first()
            
            ai_count = usage.ai_consultation_count if usage else 0
            ocr_count = usage.ocr_count if usage else 0
            
            month_data_list.append({
                'year': target_year,
                'month': target_month,
                'label': f"{target_year}年{target_month}月",
                'ai_consultation': ai_count,
                'ocr': ocr_count,
            })
        
        # 古い月から新しい月へソート（昇順）
        month_data_list.sort(key=lambda x: (x['year'], x['month']))
        
        # ソート後のデータからlabelsとデータを抽出
        for month_data in month_data_list:
            labels.append(month_data['label'])
            ai_consultation.append(month_data['ai_consultation'])
            ocr.append(month_data['ocr'])
        
        # テーブル表示用のデータを準備（古い月から新しい月へ昇順）
        table_data = []
        for i in range(len(labels)):
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
    
    def _get_company_usage_summary(self, months: int) -> list:
        """各Companyごとの利用数サマリーを取得"""
        now = timezone.now()
        
        # Firmに紐づく全てのCompanyを取得
        firm_companies = FirmCompany.objects.filter(
            firm=self.firm,
            active=True
        ).select_related('company')
        
        # 期間の開始日を正確に計算（Nヶ月前の月初）
        # _get_usage_dataと同じ方法で期間を計算
        current_year = now.year
        current_month = now.month
        
        # 最も古い月を計算
        oldest_year = current_year
        oldest_month = current_month - (months - 1)
        
        # 月が0以下になった場合の処理
        while oldest_month <= 0:
            oldest_month += 12
            oldest_year -= 1
        
        # その月の1日0時0分を開始日とする
        start_date = timezone.make_aware(datetime(oldest_year, oldest_month, 1))
        
        company_usage_list = []
        
        for firm_company in firm_companies:
            company = firm_company.company
            
            # 期間内のAI相談回数を取得
            # FirmUsageTrackingと同じ条件でカウントするため、
            # 各月ごとにFirmUsageTrackingのデータを参照する
            total_ai_count = 0
            
            # 過去Nヶ月の各月について、FirmUsageTrackingから取得
            seen_months = set()
            for i in range(months):
                target_year = current_year
                target_month = current_month - i
                
                while target_month <= 0:
                    target_month += 12
                    target_year -= 1
                
                month_key = (target_year, target_month)
                if month_key in seen_months:
                    continue
                seen_months.add(month_key)
                
                # その月の開始日と終了日を計算
                _, last_day = monthrange(target_year, target_month)
                month_start = timezone.make_aware(datetime(target_year, target_month, 1))
                month_end = timezone.make_aware(datetime(target_year, target_month, last_day, 23, 59, 59))
                
                # その月のCompanyのAI相談回数を取得（Company Userのみ）
                ai_count = AIConsultationHistory.objects.filter(
                    company=company,
                    created_at__gte=month_start,
                    created_at__lte=month_end,
                    user__is_company_user=True
                ).count()
                
                total_ai_count += ai_count
            
            # OCR回数は現時点ではCompany別に追跡していないため、0を返す
            # 将来的にOCR履歴テーブルができたら実装
            ocr_count = 0
            
            # 合計利用回数
            total_count = total_ai_count + ocr_count
            
            if total_count > 0:  # 利用があるCompanyのみ表示
                company_usage_list.append({
                    'company_id': str(company.id),
                    'company_name': company.name,
                    'ai_consultation': total_ai_count,
                    'ocr': ocr_count,
                    'total': total_count,
                })
        
        # 合計利用回数でソート（降順）
        company_usage_list.sort(key=lambda x: x['total'], reverse=True)
        
        return company_usage_list


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
        
        # 過去Nヶ月のデータを取得（重複を避けるため、年月のセットを使用）
        seen_months = set()
        month_data_list = []
        
        # 現在の月から過去Nヶ月を正確に計算
        current_year = now.year
        current_month = now.month
        
        for i in range(months):
            # 過去iヶ月前の年月を計算
            target_year = current_year
            target_month = current_month - i
            
            # 月が0以下になった場合の処理
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            
            # 重複チェック
            month_key = (target_year, target_month)
            if month_key in seen_months:
                continue
            seen_months.add(month_key)
            
            # その月の開始日と終了日を計算
            _, last_day = monthrange(target_year, target_month)
            month_start = timezone.make_aware(datetime(target_year, target_month, 1))
            month_end = timezone.make_aware(datetime(target_year, target_month, last_day, 23, 59, 59))
            
            # AI相談回数を取得（Company Userのみ）
            ai_count = AIConsultationHistory.objects.filter(
                company=company,
                created_at__gte=month_start,
                created_at__lte=month_end,
                user__is_company_user=True
            ).count()
            
            month_data_list.append({
                'year': target_year,
                'month': target_month,
                'label': f"{target_year}年{target_month}月",
                'ai_consultation': ai_count,
                'ocr': 0,  # OCR回数は現時点ではCompany別に追跡していないため、0を返す
            })
        
        # 古い月から新しい月へソート（昇順）
        month_data_list.sort(key=lambda x: (x['year'], x['month']))
        
        # ソート後のデータからlabelsとデータを抽出
        for month_data in month_data_list:
            labels.append(month_data['label'])
            ai_consultation.append(month_data['ai_consultation'])
            ocr.append(month_data['ocr'])
        
        # テーブル表示用のデータを準備（古い月から新しい月へ昇順）
        table_data = []
        for i in range(len(labels)):
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

