"""
Mixin classes for views
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.contrib import messages
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class ErrorHandlingMixin:
    """Mixin to add consistent error handling to views"""
    
    def dispatch(self, request, *args, **kwargs):
        """Dispatch method with error handling"""
        try:
            return super().dispatch(request, *args, **kwargs)
        except ValueError as e:
            logger.warning(
                f"ValueError in {self.__class__.__name__}.dispatch: {e}",
                extra={'user': request.user.id if request.user.is_authenticated else None}
            )
            messages.warning(request, str(e))
            from django.shortcuts import redirect
            return redirect('index')
        except PermissionError as e:
            logger.warning(
                f"PermissionError in {self.__class__.__name__}.dispatch: {e}",
                extra={'user': request.user.id if request.user.is_authenticated else None}
            )
            messages.error(request, 'この操作を実行する権限がありません。')
            from django.shortcuts import redirect
            return redirect('index')
        except Exception as e:
            logger.error(
                f"Unexpected error in {self.__class__.__name__}.dispatch: {e}",
                exc_info=True,
                extra={'user': request.user.id if request.user.is_authenticated else None}
            )
            messages.error(
                request,
                '予期しないエラーが発生しました。管理者にお問い合わせください。'
            )
            raise


class SelectedCompanyMixin(LoginRequiredMixin, ErrorHandlingMixin):
    """Mixin to ensure views only operate on data related to the user's currently selected company."""
    
    @property
    def this_company(self):
        """Get the currently selected company for the user"""
        from .models import UserCompany
        
        user_company = UserCompany.objects.filter(
            user=self.request.user,
            is_selected=True
        ).select_related('company', 'user').first()
        
        if not user_company:
            raise ValueError("選択された会社がありません。")
        
        return user_company.company
    
    @property
    def this_firm(self):
        """Get the currently selected firm for the user"""
        from .models import UserFirm, FirmCompany, UserCompany
        
        # まず、ユーザーの選択されたCompanyとFirmを取得
        user_company = UserCompany.objects.filter(
            user=self.request.user,
            is_selected=True
        ).select_related('company', 'user').first()
        
        if not user_company:
            raise ValueError("選択された会社がありません。")
        
        user_firm = UserFirm.objects.filter(
            user=self.request.user,
            is_selected=True
        ).select_related('firm', 'user').first()
        
        if not user_firm:
            raise ValueError("選択されたFirmがありません。")
        
        # CompanyがこのFirmに属しているか確認（まずactive=Trueで検索、見つからない場合はactive条件なしで検索）
        firm_company = FirmCompany.objects.filter(
            firm=user_firm.firm,
            company=user_company.company,
            active=True
        ).first()
        
        # active=Trueで見つからない場合、active条件なしで検索
        if not firm_company:
            firm_company = FirmCompany.objects.filter(
                firm=user_firm.firm,
                company=user_company.company
            ).first()
        
        # それでも見つからない場合、Companyに関連するFirmCompanyを検索して、ユーザーが選択したFirmと一致するものを探す
        if not firm_company:
            # Companyに関連するFirmCompanyを検索
            company_firms = FirmCompany.objects.filter(
                company=user_company.company
            ).select_related('firm')
            
            # ユーザーが選択したFirmと一致するものを探す
            for cf in company_firms:
                if cf.firm.id == user_firm.firm.id:
                    firm_company = cf
                    break
        
        # それでも見つからない場合は、ユーザーが選択したFirmをそのまま返す
        # （FirmCompanyの関係が存在しない場合でも、ユーザーがそのCompanyとFirmにアクセスできる可能性がある）
        if not firm_company:
            logger.warning(
                f"FirmCompany relationship not found for company {user_company.company.id} and firm {user_firm.firm.id}, "
                f"but returning selected firm anyway"
            )
            return user_firm.firm
        
        return user_firm.firm


class TransactionMixin:
    """Mixin to add transaction management to views"""
    
    @transaction.atomic
    def form_valid(self, form):
        """Wrap form_valid in a transaction"""
        try:
            return super().form_valid(form)
        except ValidationError as e:
            logger.error(
                f"Validation error in {self.__class__.__name__}.form_valid: {e}",
                exc_info=True,
                extra={'user': self.request.user.id if self.request.user.is_authenticated else None}
            )
            messages.error(
                self.request,
                f'バリデーションエラー: {", ".join(e.messages) if hasattr(e, "messages") else str(e)}'
            )
            return self.form_invalid(form)
        except Exception as e:
            logger.error(
                f"Error in {self.__class__.__name__}.form_valid: {e}",
                exc_info=True,
                extra={'user': self.request.user.id if self.request.user.is_authenticated else None}
            )
            messages.error(
                self.request,
                'データの保存中にエラーが発生しました。管理者にお問い合わせください。'
            )
            raise


class TransactionErrorHandlingMixin(TransactionMixin, ErrorHandlingMixin):
    """Combined mixin for transaction management and error handling"""
    pass
