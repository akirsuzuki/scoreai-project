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
from ..models import Debt
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
        except Exception as e:
            # データを取得できない場合は help.html に遷移
            logger.error(
                f"Error in IndexView.get: {e}",
                exc_info=True,
                extra={'user': request.user.id if request.user.is_authenticated else None}
            )
            messages.error(
                request,
                'データの取得中にエラーが発生しました。管理者にお問い合わせください。'
            )
            return render(request, 'scoreai/help.html')

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得
        
        Args:
            **kwargs: 追加のキーワード引数
            
        Returns:
            コンテキストデータの辞書
        """
        context = super().get_context_data(**kwargs)
        
        monthly_summaries = get_monthly_summaries(self.this_company, 3)
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

        # Calculate weighted_average_interest for each month
        weighted_average_interest = [
            interest / balance if balance != 0 else 0
            for interest, balance in zip(
                12 * debt_list_totals['total_interest_amount_monthly'],
                debt_list_totals['total_balances_monthly']
            )
        ]

        context.update({
            'title': 'ダッシュボード',
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
        })
        return context

