"""
ダッシュボード（IndexView）関連のビュー
"""
from typing import Any, Dict
from django.shortcuts import render
from django.conf import settings
from django.contrib import messages
from django.utils import timezone
from django.views import generic
import requests
import logging

from ..mixins import SelectedCompanyMixin
from ..models import Debt
from ..forms import ChatForm
from .utils import (
    get_monthly_summaries,
    calculate_total_monthly_summaries,
    get_debt_list,
    get_debt_list_byAny,
)

logger = logging.getLogger(__name__)


class IndexView(SelectedCompanyMixin, generic.TemplateView):
    """ダッシュボードビュー
    
    財務サマリー、借入情報、AIチャット機能を提供するメインダッシュボードです。
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
            context['form'] = ChatForm()
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

    def post(self, request, *args, **kwargs):
        """POSTリクエストの処理（AIチャット機能）
        
        Args:
            request: HTTPリクエストオブジェクト
            *args: 位置引数
            **kwargs: キーワード引数
            
        Returns:
            レンダリングされたレスポンス（AI応答を含む）
        """
        context = self.get_context_data()
        form = ChatForm(request.POST)
        if form.is_valid():
            user_message = form.cleaned_data['message']
            selected_company = self.get_selected_company()
            debts = Debt.objects.filter(
                company=self.this_company
            ).select_related(
                'financial_institution',
                'secured_type',
                'company'
            )

            # 債務情報を文字列にフォーマット
            debt_info = "\n".join([
                f"債務{i+1}: {debt.principal}円 (金利: {debt.interest_rate}%)"
                for i, debt in enumerate(debts)
            ])

            # プロンプトを作成
            prompt = f"""以下の債務情報に基づいて、最適な返済計画についてアドバイスしてください：
            {debt_info}
            ユーザーの質問: {user_message}
            総債務額、平均金利、そして最も効果的な返済方法を提案してください。"""

            # Prepare the API request to ChatGPT
            headers = {
                'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
                'Content-Type': 'application/json',
            }
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": "あなたは財務アドバイザーです。与えられた債務情報に基づいて、最適な返済計画を提案してください。"
                    },
                    {"role": "user", "content": prompt}
                ],
            }

            try:
                api_response = requests.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers=headers,
                    json=data,
                    timeout=30
                )

                if api_response.status_code == 200:
                    context['response_message'] = api_response.json()['choices'][0]['message']['content']
                else:
                    context['response_message'] = (
                        f"エラーが発生しました: {api_response.status_code} - {api_response.text}"
                    )
                    logger.error(
                        f"OpenAI API error: {api_response.status_code} - {api_response.text}",
                        extra={'user': request.user.id}
                    )
            except requests.RequestException as e:
                context['response_message'] = "APIへの接続中にエラーが発生しました。しばらくしてから再度お試しください。"
                logger.error(
                    f"OpenAI API request error: {e}",
                    exc_info=True,
                    extra={'user': request.user.id}
                )

        context['form'] = form
        return render(request, self.template_name, context)

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

