"""
クラウドストレージ連携のベースクラス
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, BinaryIO
from django.contrib.auth import get_user_model

User = get_user_model()


class StorageAdapter(ABC):
    """ストレージアダプターのベースクラス"""
    
    def __init__(self, user: User, access_token: str, refresh_token: Optional[str] = None):
        """
        ストレージアダプターを初期化
        
        Args:
            user: ユーザーオブジェクト
            access_token: アクセストークン
            refresh_token: リフレッシュトークン（オプション）
        """
        self.user = user
        self.access_token = access_token
        self.refresh_token = refresh_token
    
    @abstractmethod
    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Dict:
        """
        フォルダを作成
        
        Args:
            folder_name: フォルダ名
            parent_folder_id: 親フォルダID（オプション）
        
        Returns:
            作成されたフォルダの情報（id, name等を含む辞書）
        """
        pass
    
    @abstractmethod
    def get_or_create_folder(self, folder_path: str, root_folder_id: Optional[str] = None) -> Dict:
        """
        フォルダを取得または作成（パス指定）
        
        Args:
            folder_path: フォルダパス（例: "試算表/貸借対照表"）
            root_folder_id: ルートフォルダID（オプション）
        
        Returns:
            フォルダ情報（id, name等を含む辞書）
        """
        pass
    
    @abstractmethod
    def upload_file(
        self,
        file_content: BinaryIO,
        filename: str,
        folder_id: str,
        mime_type: Optional[str] = None
    ) -> Dict:
        """
        ファイルをアップロード
        
        Args:
            file_content: ファイル内容（バイナリ）
            filename: ファイル名
            folder_id: アップロード先フォルダID
            mime_type: MIMEタイプ（オプション）
        
        Returns:
            アップロードされたファイルの情報（id, name, webViewLink等を含む辞書）
        """
        pass
    
    @abstractmethod
    def download_file(self, file_id: str) -> bytes:
        """
        ファイルをダウンロード
        
        Args:
            file_id: ファイルID
        
        Returns:
            ファイル内容（バイト）
        """
        pass
    
    @abstractmethod
    def get_file_info(self, file_id: str) -> Dict:
        """
        ファイル情報を取得
        
        Args:
            file_id: ファイルID
        
        Returns:
            ファイル情報（id, name, size, mimeType等を含む辞書）
        """
        pass
    
    @abstractmethod
    def refresh_access_token(self) -> bool:
        """
        アクセストークンをリフレッシュ
        
        Returns:
            成功した場合True
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        接続をテスト
        
        Returns:
            接続が成功した場合True
        """
        pass

