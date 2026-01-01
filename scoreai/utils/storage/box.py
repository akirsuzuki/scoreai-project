"""
Box API連携
"""
import logging
from typing import Optional, Dict, BinaryIO, Any
from io import BytesIO
from django.conf import settings
from .base import StorageAdapter

logger = logging.getLogger(__name__)


class BoxAdapter(StorageAdapter):
    """Box APIアダプター"""
    
    def __init__(self, user, access_token: str, refresh_token: Optional[str] = None):
        super().__init__(user, access_token, refresh_token)
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Box APIクライアントを初期化"""
        try:
            from boxsdk import OAuth2, Client
        except ImportError:
            error_msg = (
                "boxsdkがインストールされていません。"
                "以下のコマンドを実行してインストールしてください: "
                "docker compose exec web pip install boxsdk && docker compose restart web"
            )
            logger.error(error_msg)
            raise ImportError(error_msg)
        
        try:
            oauth = OAuth2(
                client_id=getattr(settings, 'BOX_CLIENT_ID', None),
                client_secret=getattr(settings, 'BOX_CLIENT_SECRET', None),
                access_token=self.access_token,
                refresh_token=self.refresh_token,
            )
            
            self._client = Client(oauth)
            
        except Exception as e:
            logger.error(f"Box API client initialization error: {e}", exc_info=True)
            raise
    
    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Dict:
        """フォルダを作成"""
        try:
            if parent_folder_id:
                parent_folder = self._client.folder(folder_id=parent_folder_id)
                folder = parent_folder.create_subfolder(folder_name)
            else:
                # ルートフォルダに作成
                folder = self._client.folder('0').create_subfolder(folder_name)
            
            return {
                'id': folder.id,
                'name': folder.name,
                'webViewLink': folder.get_shared_link() or f"https://app.box.com/folder/{folder.id}",
            }
        except Exception as e:
            logger.error(f"Box folder creation error: {e}", exc_info=True)
            raise
    
    def get_or_create_folder(self, folder_path: str, root_folder_id: Optional[str] = None) -> Dict:
        """フォルダを取得または作成（パス指定）"""
        try:
            current_folder_id = root_folder_id or '0'
            folder_names = folder_path.split('/')
            
            for folder_name in folder_names:
                if not folder_name.strip():
                    continue
                
                # 既存のフォルダを検索
                current_folder = self._client.folder(folder_id=current_folder_id)
                items = current_folder.get_items()
                
                found_folder = None
                for item in items:
                    if item.type == 'folder' and item.name == folder_name:
                        found_folder = item
                        break
                
                if found_folder:
                    # 既存のフォルダを使用
                    current_folder_id = found_folder.id
                else:
                    # 新しいフォルダを作成
                    folder = current_folder.create_subfolder(folder_name)
                    current_folder_id = folder.id
            
            # 最終的なフォルダ情報を取得
            folder = self._client.folder(folder_id=current_folder_id).get()
            
            return {
                'id': folder.id,
                'name': folder.name,
                'webViewLink': folder.get_shared_link() or f"https://app.box.com/folder/{folder.id}",
            }
        except Exception as e:
            logger.error(f"Box get_or_create_folder error: {e}", exc_info=True)
            raise
    
    def upload_file(
        self,
        file_content: BinaryIO,
        filename: str,
        folder_id: str,
        mime_type: Optional[str] = None
    ) -> Dict:
        """ファイルをアップロード"""
        try:
            folder = self._client.folder(folder_id=folder_id)
            
            # ファイルをアップロード
            uploaded_file = folder.upload_stream(
                file_stream=file_content,
                file_name=filename,
                file_description=None,
                preflight_check=True,
            )
            
            # ファイル情報を取得
            file_info = uploaded_file.get()
            
            return {
                'id': file_info.id,
                'name': file_info.name,
                'size': file_info.size or 0,
                'mimeType': file_info.type,
                'webViewLink': file_info.get_shared_link() or f"https://app.box.com/file/{file_info.id}",
                'createdTime': file_info.created_at.isoformat() if file_info.created_at else None,
            }
        except Exception as e:
            logger.error(f"Box file upload error: {e}", exc_info=True)
            raise
    
    def download_file(self, file_id: str) -> bytes:
        """ファイルをダウンロード"""
        try:
            file = self._client.file(file_id=file_id)
            file_content = file.content()
            return file_content
        except Exception as e:
            logger.error(f"Box file download error: {e}", exc_info=True)
            raise
    
    def get_file_info(self, file_id: str) -> Dict:
        """ファイル情報を取得"""
        try:
            file = self._client.file(file_id=file_id).get()
            
            return {
                'id': file.id,
                'name': file.name,
                'size': file.size or 0,
                'mimeType': file.type,
                'webViewLink': file.get_shared_link() or f"https://app.box.com/file/{file.id}",
                'createdTime': file.created_at.isoformat() if file.created_at else None,
                'modifiedTime': file.modified_at.isoformat() if file.modified_at else None,
            }
        except Exception as e:
            logger.error(f"Box get_file_info error: {e}", exc_info=True)
            raise
    
    def refresh_access_token(self) -> bool:
        """アクセストークンをリフレッシュ"""
        try:
            import requests
            
            client_id = getattr(settings, 'BOX_CLIENT_ID', None)
            client_secret = getattr(settings, 'BOX_CLIENT_SECRET', None)
            
            if not client_id or not client_secret:
                logger.error("Box OAuth credentials not configured")
                return False
            
            token_url = 'https://api.box.com/oauth2/token'
            token_data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': client_id,
                'client_secret': client_secret,
            }
            
            response = requests.post(token_url, data=token_data)
            response.raise_for_status()
            token_response = response.json()
            
            self.access_token = token_response.get('access_token')
            if token_response.get('refresh_token'):
                self.refresh_token = token_response.get('refresh_token')
            
            # クライアントを再初期化
            self._initialize_client()
            
            return True
        except Exception as e:
            logger.error(f"Box token refresh error: {e}", exc_info=True)
            return False
    
    def test_connection(self) -> bool:
        """接続をテスト"""
        try:
            # 現在のユーザー情報を取得して接続をテスト
            user = self._client.user().get()
            return user is not None
        except Exception as e:
            # トークンが期限切れの可能性があるので、リフレッシュを試みる
            error_str = str(e).lower()
            if 'invalid' in error_str or 'expired' in error_str or '401' in error_str:
                logger.info("Access token may be expired, attempting refresh...")
                if self.refresh_access_token():
                    # リフレッシュ成功後、再試行
                    try:
                        user = self._client.user().get()
                        return user is not None
                    except Exception as retry_error:
                        logger.error(f"Box connection test error after refresh: {retry_error}", exc_info=True)
                        return False
                else:
                    logger.error(f"Failed to refresh access token: {e}", exc_info=True)
                    return False
            else:
                logger.error(f"Box connection test error: {e}", exc_info=True)
                return False
    
    def get_user_info(self) -> Dict[str, Any]:
        """ユーザー情報とストレージ情報を取得"""
        try:
            user = self._client.user().get()
            
            # ストレージ情報はBox APIでは直接取得できないため、ユーザー情報のみ返す
            return {
                'user': {
                    'id': user.id,
                    'name': user.name,
                    'login': user.login,
                },
                'storage_quota': {},  # Box APIでは直接取得できない
            }
        except Exception as e:
            logger.error(f"Box get_user_info error: {e}", exc_info=True)
            raise

