"""
ダッシュボード（IndexView）関連のビュー
"""
from typing import Any, Dict
from django.shortcuts import render
from django.contrib import messages
from django.utils import timezone
from django.views import generic
import logging

from ..mixins import SelectedCompanyMixin
from ..models import Debt, FiscalSummary_Year, FiscalSummary_Month
from .utils import (
    get_monthly_summaries,
    calculate_total_monthly_summaries,
    get_debt_list,
    get_debt_list_byAny,
)

logger = logging.getLogger(__name__)


class IndexView(SelectedCompanyMixin, generic.TemplateView):
    """ダッシュボードビュー
    
    財務サマリー、借入情報を提供するメインダッシュボードです。
    """
    template_name = 'scoreai/index.html'

    def get(self, request, *args, **kwargs):
        """GETリクエストの処理
        
        Args:
            request: HTTPリクエストオブジェクト
            *args: 位置引数
            **kwargs: キーワード引数
            
        Returns:
            レンダリングされたレスポンス。エラー時はhelp.htmlを表示。
        """
        try:
            context = self.get_context_data()
            return render(request, self.template_name, context)
        except Debt.DoesNotExist:
            messages.info(request, '借入情報がありません。')
            return render(request, 'scoreai/help.html')
        except Company.DoesNotExist:
            messages.warning(request, '会社情報が設定されていません。')
            # 会社選択ページにリダイレクト（存在する場合）
            return render(request, 'scoreai/help.html')
        except Exception as e:
            logger.error(
                f"Unexpected error in IndexView.get: {e}",
                exc_info=True,
                extra={'user': request.user.id if request.user.is_authenticated else None}
            )
            messages.error(
                request,
                'システムエラーが発生しました。管理者にお問い合わせください。'
            )
            return render(request, 'scoreai/500.html', status=500)

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得
        
        Args:
            **kwargs: 追加のキーワード引数
            
        Returns:
            コンテキストデータの辞書
        """
        context = super().get_context_data(**kwargs)
        
        # ダッシュボードでは下書きデータも含めて取得（進行中の年度を表示するため）
        # まず、下書きを含む年度を取得
        from django.db.models import Q
        latest_years_with_draft = FiscalSummary_Year.objects.filter(
            company=self.this_company,
            is_budget=False
        ).values_list('year', flat=True).distinct().order_by('-year')[:3]
        latest_years_with_draft = sorted(latest_years_with_draft, reverse=True)
        
        # 月次データを取得（下書きも含む）
        monthly_summaries = []
        for year in latest_years_with_draft:
            # 下書きも含めて実績データを取得（is_budget=False）
            monthly_data = FiscalSummary_Month.objects.filter(
                fiscal_summary_year__company=self.this_company,
                fiscal_summary_year__year=year,
                fiscal_summary_year__is_budget=False,
                is_budget=False
            ).select_related('fiscal_summary_year', 'fiscal_summary_year__company').order_by('period')
            
            # 月データを辞書に変換
            monthly_data_dict = {}
            for month in monthly_data:
                if month.period:
                    monthly_data_dict[month.period] = {
                        'id': month.id,
                        'sales': float(month.sales) if month.sales is not None else 0.0,
                        'gross_profit': float(month.gross_profit) if month.gross_profit is not None else 0.0,
                        'operating_profit': float(month.operating_profit) if month.operating_profit is not None else 0.0,
                        'ordinary_profit': float(month.ordinary_profit) if month.ordinary_profit is not None else 0.0,
                        'gross_profit_rate': float(month.gross_profit_rate) if month.gross_profit_rate is not None else 0.0,
                        'operating_profit_rate': float(month.operating_profit_rate) if month.operating_profit_rate is not None else 0.0,
                        'ordinary_profit_rate': float(month.ordinary_profit_rate) if month.ordinary_profit_rate is not None else 0.0,
                    }
            
            # 12ヶ月分のデータを作成
            import random
            full_month_data = []
            actual_months_count = 0
            for period in range(1, 13):
                if period in monthly_data_dict:
                    full_month_data.append({**monthly_data_dict[period], 'period': period})
                    actual_months_count += 1
                else:
                    full_month_data.append({
                        'period': period,
                        'id': f'temp_{random.randint(10000, 99999)}',
                        'sales': 0,
                        'gross_profit': 0,
                        'operating_profit': 0,
                        'ordinary_profit': 0,
                        'gross_profit_rate': 0,
                        'operating_profit_rate': 0,
                        'ordinary_profit_rate': 0,
                    })
            
            monthly_summaries.append({
                'year': year,
                'data': full_month_data,
                'actual_months_count': actual_months_count
            })
        monthly_summaries_total = calculate_total_monthly_summaries(
            monthly_summaries,
            year_index=0,
            period_count=13
        )
        monthly_summaries_total_last_year = calculate_total_monthly_summaries(
            monthly_summaries,
            year_index=1,
            period_count=monthly_summaries[0]['actual_months_count'] if monthly_summaries else 0
        )

        # ラベル情報
        fiscal_month = self.this_company.fiscal_month
        months_label = [(fiscal_month + i) % 12 or 12 for i in range(1, 13)]

        # 借入情報の取得
        debt_list, debt_list_totals, debt_list_nodisplay, debt_list_rescheduled, debt_list_finished = get_debt_list(
            self.this_company
        )
        debt_list = sorted(debt_list, key=lambda x: x['balances_monthly'][0], reverse=True)
        debt_list_byBank = get_debt_list_byAny('financial_institution', debt_list)
        debt_list_bySecuredType = get_debt_list_byAny('secured_type', debt_list)

        # Calculate weighted_average_interest using service layer
        from ..services.debt_service import DebtService
        weighted_average_interest = DebtService.calculate_weighted_average_interest(
            debt_list_totals['total_interest_amount_monthly'],
            debt_list_totals['total_balances_monthly']
        )

        # 予算実績比較データを取得（最新年度、下書きも含む）
        latest_year = latest_years_with_draft[0] if latest_years_with_draft else timezone.now().year
        budget_year = FiscalSummary_Year.objects.filter(
            company=self.this_company,
            year=latest_year,
            is_budget=True
        ).first()
        
        actual_year = FiscalSummary_Year.objects.filter(
            company=self.this_company,
            year=latest_year,
            is_budget=False
        ).order_by('-is_draft').first()  # 下書きも含め、非下書きを優先
        
        # 月次予算実績比較データ
        budget_monthly = []
        actual_monthly = []
        if budget_year:
            budget_monthly = FiscalSummary_Month.objects.filter(
                fiscal_summary_year=budget_year,
                is_budget=True
            ).order_by('period')
        if actual_year:
            actual_monthly = FiscalSummary_Month.objects.filter(
                fiscal_summary_year=actual_year,
                is_budget=False
            ).order_by('period')
        
        # 予算データをチャート用に整形（最新年度の予算のみ）
        budget_chart_data = {
            'sales': [0] * 12,
            'gross_profit': [0] * 12,
            'operating_profit': [0] * 12,
        }
        if budget_monthly:
            for month in budget_monthly:
                if month.period and 1 <= month.period <= 12:
                    budget_chart_data['sales'][month.period - 1] = float(month.sales or 0)
                    budget_chart_data['gross_profit'][month.period - 1] = float(month.gross_profit or 0)
                    budget_chart_data['operating_profit'][month.period - 1] = float(month.operating_profit or 0)
        
        # 実績データをチャート用に整形（最新年度の実績のみ）
        actual_chart_data = {
            'sales': [0] * 12,
            'gross_profit': [0] * 12,
            'operating_profit': [0] * 12,
        }
        if actual_monthly:
            for month in actual_monthly:
                if month.period and 1 <= month.period <= 12:
                    actual_chart_data['sales'][month.period - 1] = float(month.sales or 0)
                    actual_chart_data['gross_profit'][month.period - 1] = float(month.gross_profit or 0)
                    actual_chart_data['operating_profit'][month.period - 1] = float(month.operating_profit or 0)

        context.update({
            'title': 'ダッシュボード',
            'show_title_card': False,  # ダッシュボードではタイトルカードを非表示
            'today': timezone.now().date(),
            'months_label': months_label,
            'monthly_summaries': monthly_summaries,
            'monthly_summaries_total': monthly_summaries_total,
            'monthly_summaries_total_last_year': monthly_summaries_total_last_year,
            'debt_list': debt_list,
            'debt_list_totals': debt_list_totals,
            'debt_list_byBank': debt_list_byBank,
            'debt_list_bySecuredType': debt_list_bySecuredType,
            'weighted_average_interest': weighted_average_interest,
            # 予算実績比較データ
            'budget_year': budget_year,
            'actual_year': actual_year,
            'budget_monthly': budget_monthly,
            'actual_monthly': actual_monthly,
            'budget_chart_data': budget_chart_data,  # チャート用の予算データ
            'actual_chart_data': actual_chart_data,  # チャート用の実績データ
            'latest_year': latest_year,  # チャートで予算の年度を表示するために追加
        })
        return context

