"""
クラウドストレージ設定関連のビュー
"""
import logging
from typing import Any, Dict
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, FormView
from django.urls import reverse_lazy
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import urllib.parse

from ..mixins import SelectedCompanyMixin
from ..models import CloudStorageSetting
from ..forms import CloudStorageSettingForm

logger = logging.getLogger(__name__)


class CloudStorageSettingView(SelectedCompanyMixin, TemplateView):
    """クラウドストレージ設定画面"""
    template_name = 'scoreai/storage_setting.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = 'クラウドストレージ設定'
        context['company'] = self.this_company
        
        # 既存の設定を取得（選択中のCompanyに基づく）
        try:
            storage_setting = CloudStorageSetting.objects.get(
                user=self.request.user,
                company=self.this_company
            )
            context['storage_setting'] = storage_setting
            context['is_connected'] = storage_setting.is_active and storage_setting.storage_type
            
            # 連携状態の詳細情報を取得（接続テストは手動ボタンでのみ実行）
            if storage_setting.is_active and storage_setting.storage_type in ['google_drive', 'box']:
                # トークン状態のみ表示（接続テストは手動で実行）
                context['token_status'] = self._check_token_status(storage_setting)
                # 接続状態はセッションから取得（手動テストの結果）
                context['connection_status'] = self.request.session.get('last_connection_status', None)
            else:
                context['connection_status'] = None
                context['token_status'] = None
        except CloudStorageSetting.DoesNotExist:
            context['storage_setting'] = None
            context['is_connected'] = False
            context['connection_status'] = None
            context['token_status'] = None
        
        return context
    
    def _check_token_status(self, storage_setting: CloudStorageSetting) -> Dict[str, Any]:
        """トークンの状態を確認"""
        from django.utils import timezone
        
        token_status = {
            'has_access_token': bool(storage_setting.access_token),
            'has_refresh_token': bool(storage_setting.refresh_token),
            'token_expires_at': storage_setting.token_expires_at,
        }
        
        if storage_setting.token_expires_at:
            now = timezone.now()
            if storage_setting.token_expires_at > now:
                remaining = storage_setting.token_expires_at - now
                token_status['is_valid'] = True
                token_status['remaining_seconds'] = int(remaining.total_seconds())
                token_status['remaining_hours'] = round(remaining.total_seconds() / 3600, 1)
            else:
                token_status['is_valid'] = False
                token_status['is_expired'] = True
        else:
            token_status['is_valid'] = None
            token_status['is_expired'] = None
        
        return token_status


class GoogleDriveOAuthInitView(SelectedCompanyMixin, TemplateView):
    """Google Drive OAuth認証開始"""
    template_name = 'scoreai/storage_oauth_init.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = 'Google Drive認証'
        context['company'] = self.this_company
        context['storage_type'] = 'google_drive'
        context['storage_name'] = 'Google Drive'
        context['storage_icon'] = 'fab fa-google'
        
        # OAuth認証URLを生成
        client_id = getattr(settings, 'GOOGLE_DRIVE_CLIENT_ID', '')
        redirect_uri = getattr(settings, 'GOOGLE_DRIVE_REDIRECT_URI', '')
        
        if not client_id:
            context['error'] = 'Google Drive OAuth設定が完了していません。管理者に連絡してください。'
            return context
        
        # OAuth認証URLのパラメータ（stateにuser_idとcompany_idを含める）
        state_data = f"{self.request.user.id}:{self.this_company.id}"
        oauth_params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'https://www.googleapis.com/auth/drive.file',
            'access_type': 'offline',
            'prompt': 'consent',  # リフレッシュトークンを取得するために必要
            'state': state_data,  # CSRF対策（user_id:company_id）
        }
        
        auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode(oauth_params)
        context['auth_url'] = auth_url
        
        return context


class GoogleDriveOAuthCallbackView(SelectedCompanyMixin, TemplateView):
    """Google Drive OAuth認証コールバック"""
    template_name = 'scoreai/storage_oauth_callback.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = 'Google Drive認証中'
        context['company'] = self.this_company
        context['storage_name'] = 'Google Drive'
        return context
    
    def get(self, request, *args, **kwargs):
        """OAuth認証コールバック処理"""
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')
        
        # エラーチェック
        if error:
            messages.error(request, f'OAuth認証エラー: {error}')
            return redirect('storage_setting')
        
        # ステートの検証（CSRF対策）
        # stateは "user_id:company_id" の形式
        expected_state = f"{request.user.id}:{self.this_company.id}"
        if state != expected_state:
            messages.error(request, '認証エラー: 無効なリクエストです。')
            return redirect('storage_setting')
        
        if not code:
            messages.error(request, '認証コードが取得できませんでした。')
            return redirect('storage_setting')
        
        try:
            # アクセストークンを取得
            token_data = self._exchange_code_for_tokens(code)
            
            if not token_data:
                messages.error(request, 'トークンの取得に失敗しました。')
                return redirect('storage_setting')
            
            # ストレージ設定を保存または更新（Company単位）
            storage_setting, created = CloudStorageSetting.objects.get_or_create(
                user=request.user,
                company=self.this_company,
                defaults={
                    'storage_type': 'google_drive',
                    'access_token': token_data.get('access_token', ''),
                    'refresh_token': token_data.get('refresh_token', ''),
                    'token_expires_at': timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600)),
                    'is_active': True,
                }
            )
            
            if not created:
                # 既存の設定を更新
                storage_setting.storage_type = 'google_drive'
                storage_setting.access_token = token_data.get('access_token', '')
                if token_data.get('refresh_token'):
                    storage_setting.refresh_token = token_data.get('refresh_token', '')
                storage_setting.token_expires_at = timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600))
                storage_setting.is_active = True
                storage_setting.save()
            
            # 「S-CoreAI」ルートフォルダの作成または取得
            try:
                from ..utils.storage.google_drive import GoogleDriveAdapter
                adapter = GoogleDriveAdapter(
                    user=request.user,
                    access_token=storage_setting.access_token,
                    refresh_token=storage_setting.refresh_token
                )
                
                # 接続テスト
                if not adapter.test_connection():
                    messages.warning(request, 'Google Driveとの接続テストに失敗しました。設定を確認してください。')
                    return redirect('storage_setting')
                
                # 「S-CoreAI」フォルダを作成または取得
                if not storage_setting.root_folder_id:
                    root_folder_info = adapter.get_or_create_folder('S-CoreAI', None)
                    storage_setting.root_folder_id = root_folder_info['id']
                    storage_setting.save()
                    logger.info(f"Created root folder 'S-CoreAI' (ID: {root_folder_info['id']}) for user {request.user.id}")
                
                messages.success(
                    request,
                    'Google Driveとの連携が完了しました。あなたのGoogle Driveに「S-CoreAI」フォルダが作成されました。'
                )
            except Exception as e:
                logger.error(f"Google Drive connection test or root folder creation error: {e}", exc_info=True)
                messages.warning(request, 'Google Driveとの接続テスト中にエラーが発生しました。')
            
            return redirect('storage_setting')
            
        except Exception as e:
            logger.error(f"Google Drive OAuth callback error: {e}", exc_info=True)
            messages.error(request, f'認証処理中にエラーが発生しました: {str(e)}')
            return redirect('storage_setting')
    
    def _exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """認証コードをトークンに交換"""
        import requests
        
        client_id = getattr(settings, 'GOOGLE_DRIVE_CLIENT_ID', '')
        client_secret = getattr(settings, 'GOOGLE_DRIVE_CLIENT_SECRET', '')
        redirect_uri = getattr(settings, 'GOOGLE_DRIVE_REDIRECT_URI', '')
        
        if not client_id or not client_secret:
            logger.error("Google Drive OAuth credentials not configured")
            return None
        
        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }
        
        try:
            response = requests.post(token_url, data=token_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Token exchange error: {e}", exc_info=True)
            return None


class BoxOAuthInitView(SelectedCompanyMixin, TemplateView):
    """Box OAuth認証開始"""
    template_name = 'scoreai/storage_oauth_init.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = 'Box認証'
        context['company'] = self.this_company
        context['storage_type'] = 'box'
        context['storage_name'] = 'Box'
        context['storage_icon'] = 'fab fa-box'
        
        # OAuth認証URLを生成
        client_id = getattr(settings, 'BOX_CLIENT_ID', '')
        redirect_uri = getattr(settings, 'BOX_REDIRECT_URI', '')
        
        if not client_id:
            context['error'] = 'Box OAuth設定が完了していません。管理者に連絡してください。'
            return context
        
        # OAuth認証URLのパラメータ（stateにuser_idとcompany_idを含める）
        state_data = f"{self.request.user.id}:{self.this_company.id}"
        oauth_params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'state': state_data,  # CSRF対策（user_id:company_id）
        }
        
        auth_url = 'https://account.box.com/api/oauth2/authorize?' + urllib.parse.urlencode(oauth_params)
        context['auth_url'] = auth_url
        
        return context


class BoxOAuthCallbackView(SelectedCompanyMixin, TemplateView):
    """Box OAuth認証コールバック"""
    template_name = 'scoreai/storage_oauth_callback.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = 'Box認証中'
        context['company'] = self.this_company
        context['storage_name'] = 'Box'
        return context
    
    def get(self, request, *args, **kwargs):
        """OAuth認証コールバック処理"""
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')
        
        # エラーチェック
        if error:
            messages.error(request, f'OAuth認証エラー: {error}')
            return redirect('storage_setting')
        
        # ステートの検証（CSRF対策）
        # stateは "user_id:company_id" の形式
        expected_state = f"{request.user.id}:{self.this_company.id}"
        if state != expected_state:
            messages.error(request, '認証エラー: 無効なリクエストです。')
            return redirect('storage_setting')
        
        if not code:
            messages.error(request, '認証コードが取得できませんでした。')
            return redirect('storage_setting')
        
        try:
            # アクセストークンを取得
            token_data = self._exchange_code_for_tokens(code)
            
            if not token_data:
                messages.error(request, 'トークンの取得に失敗しました。')
                return redirect('storage_setting')
            
            # ストレージ設定を保存または更新（Company単位）
            storage_setting, created = CloudStorageSetting.objects.get_or_create(
                user=request.user,
                company=self.this_company,
                defaults={
                    'storage_type': 'box',
                    'access_token': token_data.get('access_token', ''),
                    'refresh_token': token_data.get('refresh_token', ''),
                    'token_expires_at': timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600)),
                    'is_active': True,
                }
            )
            
            if not created:
                # 既存の設定を更新
                storage_setting.storage_type = 'box'
                storage_setting.access_token = token_data.get('access_token', '')
                if token_data.get('refresh_token'):
                    storage_setting.refresh_token = token_data.get('refresh_token', '')
                storage_setting.token_expires_at = timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600))
                storage_setting.is_active = True
                storage_setting.save()
            
            # 「S-CoreAI」ルートフォルダの作成または取得
            try:
                from ..utils.storage.box import BoxAdapter
                adapter = BoxAdapter(
                    user=request.user,
                    access_token=storage_setting.access_token,
                    refresh_token=storage_setting.refresh_token
                )
                
                # 接続テスト
                if not adapter.test_connection():
                    messages.warning(request, 'Boxとの接続テストに失敗しました。設定を確認してください。')
                    return redirect('storage_setting')
                
                # 「S-CoreAI」フォルダを作成または取得
                if not storage_setting.root_folder_id:
                    root_folder_info = adapter.get_or_create_folder('S-CoreAI', None)
                    storage_setting.root_folder_id = root_folder_info['id']
                    storage_setting.save()
                    logger.info(f"Created root folder 'S-CoreAI' (ID: {root_folder_info['id']}) for user {request.user.id}")
                
                messages.success(
                    request,
                    'Boxとの連携が完了しました。あなたのBoxに「S-CoreAI」フォルダが作成されました。'
                )
            except ImportError as e:
                error_msg = str(e)
                logger.error(f"Box SDK import error: {error_msg}", exc_info=True)
                messages.error(
                    request,
                    'Box SDKがインストールされていません。管理者に連絡してください。'
                )
            except Exception as e:
                logger.error(f"Box connection test or root folder creation error: {e}", exc_info=True)
                messages.warning(request, f'Boxとの接続テスト中にエラーが発生しました: {str(e)}')
            
            return redirect('storage_setting')
            
        except Exception as e:
            logger.error(f"Box OAuth callback error: {e}", exc_info=True)
            messages.error(request, f'認証処理中にエラーが発生しました: {str(e)}')
            return redirect('storage_setting')
    
    def _exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """認証コードをトークンに交換"""
        import requests
        
        client_id = getattr(settings, 'BOX_CLIENT_ID', '')
        client_secret = getattr(settings, 'BOX_CLIENT_SECRET', '')
        redirect_uri = getattr(settings, 'BOX_REDIRECT_URI', '')
        
        if not client_id or not client_secret:
            logger.error("Box OAuth credentials not configured")
            return None
        
        token_url = 'https://api.box.com/oauth2/token'
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
        }
        
        try:
            response = requests.post(token_url, data=token_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Box token exchange error: {e}", exc_info=True)
            return None


class CloudStorageDisconnectView(SelectedCompanyMixin, TemplateView):
    """クラウドストレージ連携解除"""
    template_name = 'scoreai/storage_disconnect.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = 'クラウドストレージ連携解除'
        context['company'] = self.this_company
        return context
    
    def post(self, request, *args, **kwargs):
        """連携解除処理"""
        try:
            storage_setting = CloudStorageSetting.objects.get(
                user=request.user,
                company=self.this_company
            )
            storage_setting.is_active = False
            storage_setting.save()
            messages.success(request, 'クラウドストレージとの連携を解除しました。')
        except CloudStorageSetting.DoesNotExist:
            messages.warning(request, '連携設定が見つかりませんでした。')
        
        return redirect('storage_setting')


class CloudStorageTestConnectionView(SelectedCompanyMixin, TemplateView):
    """クラウドストレージ接続テスト"""
    
    def post(self, request, *args, **kwargs):
        """接続テスト処理"""
        try:
            storage_setting = CloudStorageSetting.objects.get(
                user=request.user,
                company=self.this_company
            )
            
            if not storage_setting.is_active:
                messages.warning(request, '連携が無効になっています。')
                request.session['last_connection_status'] = {
                    'status': 'error',
                    'message': '連携が無効になっています。'
                }
                return redirect('storage_setting')
            
            if storage_setting.storage_type == 'google_drive':
                from ..utils.storage.google_drive import GoogleDriveAdapter
                
                adapter = GoogleDriveAdapter(
                    user=request.user,
                    access_token=storage_setting.access_token,
                    refresh_token=storage_setting.refresh_token
                )
                
                # 接続テスト（内部でトークンリフレッシュも試みる）
                connection_status = self._test_google_drive_connection(storage_setting, adapter)
                
                # セッションに保存
                request.session['last_connection_status'] = connection_status
                
                # トークンがリフレッシュされた場合、データベースを更新
                if adapter.access_token != storage_setting.access_token:
                    storage_setting.access_token = adapter.access_token
                    if adapter.refresh_token:
                        storage_setting.refresh_token = adapter.refresh_token
                    # 新しいトークンの有効期限を設定（1時間後）
                    from django.utils import timezone
                    from datetime import timedelta
                    storage_setting.token_expires_at = timezone.now() + timedelta(hours=1)
                    storage_setting.save()
                    logger.info("Access token refreshed and saved to database")
                
                if connection_status['status'] == 'success':
                    messages.success(request, connection_status['message'])
                else:
                    messages.error(request, connection_status['message'])
            elif storage_setting.storage_type == 'box':
                from ..utils.storage.box import BoxAdapter
                
                adapter = BoxAdapter(
                    user=request.user,
                    access_token=storage_setting.access_token,
                    refresh_token=storage_setting.refresh_token
                )
                
                # 接続テスト（内部でトークンリフレッシュも試みる）
                connection_status = self._test_box_connection(storage_setting, adapter)
                
                # セッションに保存
                request.session['last_connection_status'] = connection_status
                
                # トークンがリフレッシュされた場合、データベースを更新
                if adapter.access_token != storage_setting.access_token:
                    storage_setting.access_token = adapter.access_token
                    if adapter.refresh_token:
                        storage_setting.refresh_token = adapter.refresh_token
                    # 新しいトークンの有効期限を設定（1時間後）
                    from django.utils import timezone
                    from datetime import timedelta
                    storage_setting.token_expires_at = timezone.now() + timedelta(hours=1)
                    storage_setting.save()
                    logger.info("Box access token refreshed and saved to database")
                
                if connection_status['status'] == 'success':
                    messages.success(request, connection_status['message'])
                else:
                    messages.error(request, connection_status['message'])
            else:
                messages.info(request, 'このストレージタイプの接続テストはまだ実装されていません。')
                request.session['last_connection_status'] = {
                    'status': 'info',
                    'message': 'このストレージタイプの接続テストはまだ実装されていません。'
                }
        except CloudStorageSetting.DoesNotExist:
            messages.warning(request, '連携設定が見つかりませんでした。')
            request.session['last_connection_status'] = {
                'status': 'error',
                'message': '連携設定が見つかりませんでした。'
            }
        except Exception as e:
            logger.error(f"Connection test error: {e}", exc_info=True)
            error_message = f'接続テスト中にエラーが発生しました: {str(e)}'
            messages.error(request, error_message)
            request.session['last_connection_status'] = {
                'status': 'error',
                'message': error_message
            }
        
        return redirect('storage_setting')
    
    def _test_box_connection(self, storage_setting: CloudStorageSetting, adapter) -> Dict[str, Any]:
        """Box APIへの接続をテスト（内部メソッド）"""
        try:
            # 接続テスト（内部でトークンリフレッシュも試みる）
            is_connected = adapter.test_connection()
            
            if is_connected:
                # ユーザー情報を取得
                try:
                    user_data = adapter.get_user_info()
                    user_info = user_data.get('user', {})
                    
                    return {
                        'status': 'success',
                        'message': 'Boxへの接続に成功しました',
                        'user_email': user_info.get('login', '不明'),
                        'user_name': user_info.get('name', '不明'),
                        'storage_limit': None,  # Box APIでは直接取得できない
                        'storage_used': None,
                    }
                except Exception as e:
                    logger.warning(f"Failed to get Box user info: {e}", exc_info=True)
                    return {
                        'status': 'success',
                        'message': 'Boxへの接続に成功しました（詳細情報の取得に失敗）',
                    }
            else:
                return {
                    'status': 'error',
                    'message': 'Boxへの接続に失敗しました。トークンの有効期限が切れている可能性があります。',
                }
        except Exception as e:
            logger.error(f"Box connection test error: {e}", exc_info=True)
            error_message = str(e)
            # エラーメッセージを簡潔にする
            if 'invalid' in error_message.lower() or 'expired' in error_message.lower():
                error_message = 'トークンが無効または期限切れです。再度認証してください。'
            elif '401' in error_message:
                error_message = '認証に失敗しました。再度認証してください。'
            return {
                'status': 'error',
                'message': f'接続テスト中にエラーが発生しました: {error_message}',
            }
    
    def _test_google_drive_connection(self, storage_setting: CloudStorageSetting, adapter) -> Dict[str, Any]:
        """Google Drive APIへの接続をテスト（内部メソッド）"""
        try:
            # 接続テスト（内部でトークンリフレッシュも試みる）
            is_connected = adapter.test_connection()
            
            if is_connected:
                # ユーザー情報を取得
                try:
                    user_data = adapter.get_user_info()
                    user_info = user_data.get('user', {})
                    storage_quota = user_data.get('storage_quota', {})
                    
                    # ストレージ容量を数値に変換
                    storage_limit_str = storage_quota.get('limit')
                    storage_used_str = storage_quota.get('usage')
                    
                    storage_limit = int(storage_limit_str) if storage_limit_str else None
                    storage_used = int(storage_used_str) if storage_used_str else None
                    
                    return {
                        'status': 'success',
                        'message': 'Google Driveへの接続に成功しました',
                        'user_email': user_info.get('emailAddress', '不明'),
                        'user_name': user_info.get('displayName', '不明'),
                        'storage_limit': storage_limit,
                        'storage_used': storage_used,
                    }
                except Exception as e:
                    logger.warning(f"Failed to get user info: {e}", exc_info=True)
                    return {
                        'status': 'success',
                        'message': 'Google Driveへの接続に成功しました（詳細情報の取得に失敗）',
                    }
            else:
                return {
                    'status': 'error',
                    'message': 'Google Driveへの接続に失敗しました。トークンの有効期限が切れている可能性があります。',
                }
        except Exception as e:
            logger.error(f"Google Drive connection test error: {e}", exc_info=True)
            error_message = str(e)
            # エラーメッセージを簡潔にする
            if 'invalid' in error_message.lower() or 'expired' in error_message.lower():
                error_message = 'トークンが無効または期限切れです。再度認証してください。'
            elif '401' in error_message:
                error_message = '認証に失敗しました。再度認証してください。'
            return {
                'status': 'error',
                'message': f'接続テスト中にエラーが発生しました: {error_message}',
            }

