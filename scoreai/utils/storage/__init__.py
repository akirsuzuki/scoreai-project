"""
クラウドストレージ連携モジュール
"""
from .base import StorageAdapter
from .google_drive import GoogleDriveAdapter
from .box import BoxAdapter

__all__ = [
    'StorageAdapter',
    'GoogleDriveAdapter',
    'BoxAdapter',
]

