"""
クラウドストレージ連携モジュール
"""
from .base import StorageAdapter
from .google_drive import GoogleDriveAdapter

__all__ = [
    'StorageAdapter',
    'GoogleDriveAdapter',
]

