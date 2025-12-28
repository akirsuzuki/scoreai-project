"""
Google Drive API連携
"""
import logging
from typing import Optional, Dict, BinaryIO, Any
from io import BytesIO
from django.conf import settings
from .base import StorageAdapter

logger = logging.getLogger(__name__)


class GoogleDriveAdapter(StorageAdapter):
    """Google Drive APIアダプター"""
    
    def __init__(self, user, access_token: str, refresh_token: Optional[str] = None):
        super().__init__(user, access_token, refresh_token)
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Google Drive APIクライアントを初期化"""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
            
            credentials = Credentials(
                token=self.access_token,
                refresh_token=self.refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=getattr(settings, 'GOOGLE_DRIVE_CLIENT_ID', None),
                client_secret=getattr(settings, 'GOOGLE_DRIVE_CLIENT_SECRET', None),
            )
            
            self._client = build('drive', 'v3', credentials=credentials)
            self._MediaIoBaseUpload = MediaIoBaseUpload
            self._MediaIoBaseDownload = MediaIoBaseDownload
            
        except ImportError:
            logger.error("google-api-python-clientがインストールされていません")
            raise
        except Exception as e:
            logger.error(f"Google Drive API client initialization error: {e}", exc_info=True)
            raise
    
    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Dict:
        """フォルダを作成"""
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            folder = self._client.files().create(
                body=file_metadata,
                fields='id, name, webViewLink'
            ).execute()
            
            return {
                'id': folder.get('id'),
                'name': folder.get('name'),
                'webViewLink': folder.get('webViewLink'),
            }
        except Exception as e:
            logger.error(f"Google Drive folder creation error: {e}", exc_info=True)
            raise
    
    def get_or_create_folder(self, folder_path: str, root_folder_id: Optional[str] = None) -> Dict:
        """フォルダを取得または作成（パス指定）"""
        try:
            current_folder_id = root_folder_id or 'root'
            folder_names = folder_path.split('/')
            
            for folder_name in folder_names:
                if not folder_name.strip():
                    continue
                
                # 既存のフォルダを検索
                query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
                if current_folder_id != 'root':
                    query += f" and '{current_folder_id}' in parents"
                else:
                    query += " and 'root' in parents"
                
                results = self._client.files().list(
                    q=query,
                    fields='files(id, name)'
                ).execute()
                
                folders = results.get('files', [])
                
                if folders:
                    # 既存のフォルダを使用
                    current_folder_id = folders[0]['id']
                else:
                    # 新しいフォルダを作成
                    folder = self.create_folder(folder_name, current_folder_id)
                    current_folder_id = folder['id']
            
            # 最終的なフォルダ情報を取得
            folder_info = self._client.files().get(
                fileId=current_folder_id,
                fields='id, name, webViewLink'
            ).execute()
            
            return {
                'id': folder_info.get('id'),
                'name': folder_info.get('name'),
                'webViewLink': folder_info.get('webViewLink'),
            }
        except Exception as e:
            logger.error(f"Google Drive get_or_create_folder error: {e}", exc_info=True)
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
            # MIMEタイプの自動判定
            if not mime_type:
                import mimetypes
                mime_type, _ = mimetypes.guess_type(filename)
                if not mime_type:
                    mime_type = 'application/octet-stream'
            
            # ファイルメタデータ
            file_metadata = {
                'name': filename,
                'parents': [folder_id],
            }
            
            # メディアアップロード
            media = self._MediaIoBaseUpload(
                file_content,
                mimetype=mime_type,
                resumable=True
            )
            
            file = self._client.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, size, mimeType, webViewLink, createdTime'
            ).execute()
            
            return {
                'id': file.get('id'),
                'name': file.get('name'),
                'size': int(file.get('size', 0)),
                'mimeType': file.get('mimeType'),
                'webViewLink': file.get('webViewLink'),
                'createdTime': file.get('createdTime'),
            }
        except Exception as e:
            logger.error(f"Google Drive file upload error: {e}", exc_info=True)
            raise
    
    def download_file(self, file_id: str) -> bytes:
        """ファイルをダウンロード"""
        try:
            request = self._client.files().get_media(fileId=file_id)
            file_content = BytesIO()
            downloader = self._MediaIoBaseDownload(file_content, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            return file_content.getvalue()
        except Exception as e:
            logger.error(f"Google Drive file download error: {e}", exc_info=True)
            raise
    
    def get_file_info(self, file_id: str) -> Dict:
        """ファイル情報を取得"""
        try:
            file = self._client.files().get(
                fileId=file_id,
                fields='id, name, size, mimeType, webViewLink, createdTime, modifiedTime'
            ).execute()
            
            return {
                'id': file.get('id'),
                'name': file.get('name'),
                'size': int(file.get('size', 0)),
                'mimeType': file.get('mimeType'),
                'webViewLink': file.get('webViewLink'),
                'createdTime': file.get('createdTime'),
                'modifiedTime': file.get('modifiedTime'),
            }
        except Exception as e:
            logger.error(f"Google Drive get_file_info error: {e}", exc_info=True)
            raise
    
    def refresh_access_token(self) -> bool:
        """アクセストークンをリフレッシュ"""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            
            credentials = Credentials(
                token=self.access_token,
                refresh_token=self.refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=getattr(settings, 'GOOGLE_DRIVE_CLIENT_ID', None),
                client_secret=getattr(settings, 'GOOGLE_DRIVE_CLIENT_SECRET', None),
            )
            
            credentials.refresh(Request())
            
            self.access_token = credentials.token
            if credentials.refresh_token:
                self.refresh_token = credentials.refresh_token
            
            return True
        except Exception as e:
            logger.error(f"Google Drive token refresh error: {e}", exc_info=True)
            return False
    
    def test_connection(self) -> bool:
        """接続をテスト"""
        try:
            # ユーザー情報を取得して接続をテスト
            about = self._client.about().get(fields='user').execute()
            return about.get('user') is not None
        except Exception as e:
            # トークンが期限切れの可能性があるので、リフレッシュを試みる
            error_str = str(e).lower()
            if 'invalid' in error_str or 'expired' in error_str or '401' in error_str:
                logger.info("Access token may be expired, attempting refresh...")
                if self.refresh_access_token():
                    # リフレッシュ成功後、クライアントを再初期化して再試行
                    self._initialize_client()
                    try:
                        about = self._client.about().get(fields='user').execute()
                        return about.get('user') is not None
                    except Exception as retry_error:
                        logger.error(f"Google Drive connection test error after refresh: {retry_error}", exc_info=True)
                        return False
                else:
                    logger.error(f"Failed to refresh access token: {e}", exc_info=True)
                    return False
            else:
                logger.error(f"Google Drive connection test error: {e}", exc_info=True)
                return False
    
    def get_user_info(self) -> Dict[str, Any]:
        """ユーザー情報とストレージ情報を取得"""
        try:
            about = self._client.about().get(fields='user,storageQuota').execute()
            return {
                'user': about.get('user', {}),
                'storage_quota': about.get('storageQuota', {}),
            }
        except Exception as e:
            logger.error(f"Google Drive get_user_info error: {e}", exc_info=True)
            raise

