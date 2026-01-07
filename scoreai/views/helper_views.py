"""
ヘルパー関数・ビュー
"""
from typing import Optional
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse

from ..models import UserCompany
from ..forms import ChatForm


@login_required
def select_company(request: HttpRequest, this_company: str) -> HttpResponse:
    """会社を選択する
    
    ユーザーが選択した会社を設定します。
    
    Args:
        request: HTTPリクエストオブジェクト
        this_company: 選択する会社のID
        
    Returns:
        リダイレクトレスポンス（indexページへ）
    """
    user = request.user
    
    # Get the previously selected company
    previous_company = UserCompany.objects.filter(
        user=user,
        is_selected=True
    ).select_related('user', 'company').first()
    
    # Set all user companies to is_selected=False
    UserCompany.objects.filter(user=user).update(is_selected=False)
    
    # Set the selected company to is_selected=True
    new_company = UserCompany.objects.filter(
        user=user,
        company_id=this_company
    ).select_related('user', 'company').first()
    
    if new_company:
        new_company.is_selected = True
        new_company.save()
        
        # Create success message
        if previous_company:
            messages.warning(
                request,
                f'対象の会社を{previous_company.company.name}から{new_company.company.name}に変更しました。'
            )
        else:
            messages.warning(
                request,
                f'対象の会社を{new_company.company.name}に設定しました。'
            )
    else:
        messages.error(request, '指定された会社が見つかりません。')
    
    return redirect('index')


def chat_view(request: HttpRequest) -> HttpResponse:
    """チャットビュー（非推奨）
    
    注意: この関数は非推奨です。IndexViewのpostメソッドを使用してください。
    
    Args:
        request: HTTPリクエストオブジェクト
        
    Returns:
        レンダリングされたレスポンス
    """
    from ..models import Debt
    from ..utils.gemini import get_financial_advice
    import logging
    
    logger = logging.getLogger(__name__)
    response_message = None
    # N+1問題を回避するため、関連オブジェクトを事前取得
    debts = Debt.objects.select_related(
        'financial_institution',
        'secured_type',
        'company'
    ).all()

    if request.method == 'POST':
        form = ChatForm(request.POST)
        if form.is_valid():
            user_message = form.cleaned_data['message']

            # Google Gemini APIを使用して財務アドバイスを取得
            try:
                response_message = get_financial_advice(
                    user_message=user_message
                )
                
                if not response_message:
                    response_message = "アドバイスの生成中にエラーが発生しました。しばらくしてから再度お試しください。"
                    logger.warning(
                        "Gemini API returned empty response",
                        extra={'user': request.user.id if request.user.is_authenticated else None}
                    )
            except Exception as e:
                response_message = "APIへの接続中にエラーが発生しました。しばらくしてから再度お試しください。"
                logger.error(
                    f"Gemini API error: {e}",
                    exc_info=True,
                    extra={'user': request.user.id if request.user.is_authenticated else None}
                )
    else:
        form = ChatForm()

    return render(request, 'scoreai/chat.html', {'form': form, 'response_message': response_message})

