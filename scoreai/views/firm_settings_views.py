"""
Firm設定管理機能のビュー
"""
from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, UpdateView
from django.contrib import messages
from django.shortcuts import redirect
from django.db import transaction
from django import forms

from ..models import Firm
from ..mixins import ErrorHandlingMixin, FirmOwnerMixin


class FirmSettingsForm(forms.ModelForm):
    """Firm設定フォーム"""
    class Meta:
        model = Firm
        fields = [
            'entity_type', 'name', 'representative_name', 'website_url',
            'postal_code', 'prefecture', 'city', 'address', 'building',
            'invoice_number'
        ]
        widgets = {
            'entity_type': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例：○○税理士事務所、○○コンサルティング株式会社'
            }),
            'representative_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '代表者のお名前'
            }),
            'website_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1000001',
                'maxlength': '7',
                'id': 'postal_code'
            }),
            'prefecture': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '都道府県',
                'id': 'prefecture',
                'readonly': 'readonly'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '市区町村',
                'id': 'city',
                'readonly': 'readonly'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '町名・番地（例：丸の内1-1-1）'
            }),
            'building': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ビル名・階数（例：○○ビル3F）'
            }),
            'invoice_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'T1234567890123',
                'maxlength': '14'
            }),
        }
        labels = {
            'entity_type': '個人/法人区分',
            'name': '事務所名',
            'representative_name': '代表者名',
            'website_url': 'Webサイト',
            'postal_code': '郵便番号',
            'prefecture': '都道府県',
            'city': '市区町村',
            'address': '町名・番地',
            'building': 'ビル名・階数',
            'invoice_number': 'インボイス登録番号',
        }
        help_texts = {
            'postal_code': 'ハイフンなしで入力してください',
            'invoice_number': 'T+13桁の番号（任意）',
        }
    
    def __init__(self, *args, **kwargs):
        super(FirmSettingsForm, self).__init__(*args, **kwargs)
        # 編集時はentity_typeは必須ではない
        self.fields['entity_type'].required = False
        self.fields['name'].required = True
        self.fields['representative_name'].required = True
        # 任意フィールド
        self.fields['website_url'].required = False
        self.fields['postal_code'].required = False
        self.fields['prefecture'].required = False
        self.fields['city'].required = False
        self.fields['address'].required = False
        self.fields['building'].required = False
        self.fields['invoice_number'].required = False
    
    def clean_postal_code(self):
        """郵便番号のバリデーション"""
        postal_code = self.cleaned_data.get('postal_code')
        if postal_code:
            # ハイフンを除去
            postal_code = postal_code.replace('-', '').replace('ー', '')
            if not postal_code.isdigit() or len(postal_code) != 7:
                raise forms.ValidationError('郵便番号は7桁の数字で入力してください')
        return postal_code
    
    def clean_invoice_number(self):
        """インボイス登録番号のバリデーション"""
        invoice_number = self.cleaned_data.get('invoice_number')
        if invoice_number:
            invoice_number = invoice_number.upper()
            if not invoice_number.startswith('T') or len(invoice_number) != 14:
                raise forms.ValidationError('インボイス登録番号はT+13桁の形式で入力してください')
            if not invoice_number[1:].isdigit():
                raise forms.ValidationError('T以降は13桁の数字を入力してください')
        return invoice_number


class FirmSettingsView(FirmOwnerMixin, UpdateView):
    """Firm設定管理ビュー"""
    model = Firm
    form_class = FirmSettingsForm
    template_name = 'scoreai/firm_settings.html'
    
    def get_object(self):
        """編集対象のFirmを取得"""
        return self.firm
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Firm設定'
        context['show_title_card'] = False
        context['firm'] = self.firm
        return context
    
    def form_valid(self, form):
        """フォームが有効な場合の処理"""
        messages.success(self.request, 'Firm設定を更新しました。')
        return super().form_valid(form)
    
    def get_success_url(self):
        """成功時のリダイレクト先"""
        return self.request.path

