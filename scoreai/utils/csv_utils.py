"""
CSV処理用のユーティリティ関数
"""
import csv
import chardet
import logging
from typing import Optional, Tuple, List, Dict, Any
from io import StringIO, BytesIO

logger = logging.getLogger(__name__)


def detect_encoding(file_content: bytes) -> str:
    """
    CSVファイルのエンコーディングを自動検出
    
    Args:
        file_content: ファイルのバイト列
        
    Returns:
        検出されたエンコーディング（デフォルト: shift-jis）
    """
    try:
        # chardetを使用してエンコーディングを検出
        detected = chardet.detect(file_content)
        encoding = detected.get('encoding', 'shift-jis')
        confidence = detected.get('confidence', 0)
        
        # 信頼度が低い場合は、一般的な日本語エンコーディングを試す
        if confidence < 0.7:
            # よく使われる日本語エンコーディングを順に試す
            for enc in ['shift-jis', 'utf-8', 'euc-jp', 'cp932']:
                try:
                    file_content.decode(enc)
                    logger.info(f"Encoding detected (fallback): {enc}")
                    return enc
                except UnicodeDecodeError:
                    continue
        
        logger.info(f"Encoding detected: {encoding} (confidence: {confidence:.2f})")
        return encoding.lower()
    except Exception as e:
        logger.warning(f"Encoding detection failed: {e}, using shift-jis as fallback")
        return 'shift-jis'


def read_csv_with_auto_encoding(csv_file) -> Tuple[List[List[str]], str]:
    """
    エンコーディングを自動検出してCSVを読み込む
    
    Args:
        csv_file: アップロードされたCSVファイル
        
    Returns:
        (CSVデータのリスト, 使用されたエンコーディング)
    """
    # ファイルの内容を読み込む
    file_content = csv_file.read()
    csv_file.seek(0)  # ファイルポインタをリセット
    
    # エンコーディングを検出
    encoding = detect_encoding(file_content)
    
    # エンコーディングを試行
    encodings_to_try = [encoding, 'shift-jis', 'utf-8', 'euc-jp', 'cp932']
    
    for enc in encodings_to_try:
        try:
            decoded_content = file_content.decode(enc)
            csv_reader = csv.reader(StringIO(decoded_content))
            data = list(csv_reader)
            logger.info(f"CSV read successfully with encoding: {enc}")
            return data, enc
        except (UnicodeDecodeError, UnicodeError) as e:
            logger.warning(f"Failed to decode with {enc}: {e}")
            continue
        except Exception as e:
            logger.error(f"Error reading CSV with {enc}: {e}")
            continue
    
    # すべてのエンコーディングで失敗した場合
    raise ValueError("CSVファイルのエンコーディングを検出できませんでした。")


def validate_csv_structure(
    csv_data: List[List[str]],
    expected_columns: Optional[List[str]] = None,
    min_rows: int = 1
) -> Tuple[bool, Optional[str]]:
    """
    CSVデータの構造を検証
    
    Args:
        csv_data: CSVデータのリスト
        expected_columns: 期待される列名のリスト（オプション）
        min_rows: 最小行数
        
    Returns:
        (検証結果, エラーメッセージ)
    """
    if not csv_data:
        return False, "CSVファイルが空です。"
    
    if len(csv_data) < min_rows:
        return False, f"CSVファイルの行数が不足しています（最低{min_rows}行必要）。"
    
    if expected_columns:
        header = csv_data[0]
        missing_columns = set(expected_columns) - set(header)
        if missing_columns:
            return False, f"必須の列が不足しています: {', '.join(missing_columns)}"
    
    return True, None


def preview_csv_data(
    csv_data: List[List[str]],
    max_rows: int = 10
) -> Dict[str, Any]:
    """
    CSVデータのプレビューを生成
    
    Args:
        csv_data: CSVデータのリスト
        max_rows: プレビューに表示する最大行数
        
    Returns:
        プレビューデータの辞書
    """
    preview_rows = csv_data[:max_rows + 1]  # ヘッダー + データ行
    total_rows = len(csv_data)
    
    return {
        'header': csv_data[0] if csv_data else [],
        'preview_rows': preview_rows[1:] if len(preview_rows) > 1 else [],
        'total_rows': total_rows,
        'preview_count': min(max_rows, total_rows - 1) if total_rows > 1 else 0,
        'has_more': total_rows > max_rows + 1
    }

