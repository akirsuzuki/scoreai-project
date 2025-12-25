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
    from django.conf import settings
    import requests
    from ..models import Debt
    
    response_message = None
    debts = Debt.objects.all()

    if request.method == 'POST':
        form = ChatForm(request.POST)
        if form.is_valid():
            user_message = form.cleaned_data['message']

            # Prepare the API request to ChatGPT
            headers = {
                'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
                'Content-Type': 'application/json',
            }
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": user_message}],
            }
            try:
                api_response = requests.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers=headers,
                    json=data,
                    timeout=30
                )

                if api_response.status_code == 200:
                    response_message = api_response.json()['choices'][0]['message']['content']
                else:
                    response_message = (
                        f"エラーが発生しました: {api_response.status_code} - {api_response.text}"
                    )
            except requests.RequestException as e:
                response_message = "APIへの接続中にエラーが発生しました。しばらくしてから再度お試しください。"
    else:
        form = ChatForm()

    return render(request, 'scoreai/chat.html', {'form': form, 'response_message': response_message})

