"""
ダッシュボード（IndexView）関連のビュー
"""
from typing import Any, Dict
from django.shortcuts import render
from django.contrib import messages
from django.utils import timezone
from django.views import generic
import logging
import json

from ..mixins import SelectedCompanyMixin
from ..models import Debt, FiscalSummary_Year, FiscalSummary_Month, Company
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
        
        # 月次データを取得（下書きも含む）
        # get_monthly_summaries内部で、同一年月・同一タイプのデータがある場合は
        # 実績（非下書き）が優先されるようにソート処理されている
        monthly_summaries = get_monthly_summaries(self.this_company, num_years=3)
        
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

        # ラベル情報（決算月の次の月から開始、決算月が最後）
        fiscal_month = self.this_company.fiscal_month
        months_label = [((fiscal_month + i) % 12) or 12 for i in range(1, 13)]

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
        latest_year = monthly_summaries[0]['year'] if monthly_summaries else timezone.now().year
        budget_year = FiscalSummary_Year.objects.filter(
            company=self.this_company,
            year=latest_year,
            is_budget=True
        ).first()
        
        actual_year = FiscalSummary_Year.objects.filter(
            company=self.this_company,
            year=latest_year,
            is_budget=False
        ).order_by('is_draft').first()  # 下書きも含め、非下書きを優先
        
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

        # 予算達成状況の計算（経過月数分）
        budget_achievement = {
            'sales': None,
            'operating_profit': None,
            'sales_forecast': None,
            'operating_profit_forecast': None,
            'elapsed_months': 0,
        }
        
        # 実績データがある場合は経過月数を計算
        if actual_monthly:
            elapsed_months = len([m for m in actual_monthly if m.period and 1 <= m.period <= 12])
            budget_achievement['elapsed_months'] = elapsed_months
            
            # 予算データと実績データの両方が存在する場合のみ達成率を計算
            if budget_monthly and elapsed_months > 0:
                # 経過月数分の予算合計
                budget_sales_total = sum([float(m.sales or 0) for m in budget_monthly if m.period and 1 <= m.period <= elapsed_months])
                budget_operating_profit_total = sum([float(m.operating_profit or 0) for m in budget_monthly if m.period and 1 <= m.period <= elapsed_months])
                
                # 経過月数分の実績合計
                actual_sales_total = sum([float(m.sales or 0) for m in actual_monthly if m.period and 1 <= m.period <= elapsed_months])
                actual_operating_profit_total = sum([float(m.operating_profit or 0) for m in actual_monthly if m.period and 1 <= m.period <= elapsed_months])
                
                # 達成率を計算
                if budget_sales_total > 0:
                    budget_achievement['sales'] = (actual_sales_total / budget_sales_total) * 100
                else:
                    budget_achievement['sales'] = 0
                
                if budget_operating_profit_total != 0:
                    budget_achievement['operating_profit'] = (actual_operating_profit_total / budget_operating_profit_total) * 100 if budget_operating_profit_total > 0 else 0
                else:
                    budget_achievement['operating_profit'] = 0
                
                # 着地見込みを計算（年間予算に対する現在のペース）
                if budget_year and elapsed_months > 0:
                    # 年間予算
                    annual_budget_sales = float(budget_year.sales or 0)
                    annual_budget_operating_profit = float(budget_year.operating_profit or 0)
                    
                    # 現在の月平均実績
                    monthly_avg_sales = actual_sales_total / elapsed_months
                    monthly_avg_operating_profit = actual_operating_profit_total / elapsed_months
                    
                    # 年間着地見込み（月平均 × 12）
                    budget_achievement['sales_forecast'] = monthly_avg_sales * 12
                    budget_achievement['operating_profit_forecast'] = monthly_avg_operating_profit * 12

        # JSON形式でチャート用データを準備
        monthly_summaries_json = json.dumps(monthly_summaries, ensure_ascii=False)
        months_label_json = json.dumps(months_label, ensure_ascii=False)
        budget_chart_data_json = json.dumps(budget_chart_data, ensure_ascii=False)
        actual_chart_data_json = json.dumps(actual_chart_data, ensure_ascii=False)

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
            'budget_chart_data_json': budget_chart_data_json,  # JSON形式の予算データ
            'actual_chart_data_json': actual_chart_data_json,  # JSON形式の実績データ
            'monthly_summaries_json': monthly_summaries_json,  # JSON形式の月次サマリー
            'months_label_json': months_label_json,  # JSON形式の月ラベル
            'latest_year': latest_year,  # チャートで予算の年度を表示するために追加
            'budget_achievement': budget_achievement,  # 予算達成状況
        })
        return context

