"""
Google Cloud Vision APIを使用したOCR機能
"""
from google.cloud import vision
from django.conf import settings
import logging
from typing import Dict, List, Optional, Any
from io import BytesIO
from PIL import Image
import base64

logger = logging.getLogger(__name__)


def initialize_vision_client() -> Optional[vision.ImageAnnotatorClient]:
    """Vision APIクライアントを初期化"""
    try:
        import os
        import json
        
        # 方法1: サービスアカウントキーのパスが環境変数で設定されている場合
        if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            client = vision.ImageAnnotatorClient()
            return client
        
        # 方法2: サービスアカウントキーのJSONが環境変数で設定されている場合（Herokuなど）
        if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON'):
            creds_json = json.loads(os.environ['GOOGLE_APPLICATION_CREDENTIALS_JSON'])
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_info(creds_json)
            client = vision.ImageAnnotatorClient(credentials=credentials)
            return client
        
        # 方法3: settings.pyからサービスアカウントキーのパスを取得
        if hasattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS') and settings.GOOGLE_APPLICATION_CREDENTIALS:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.GOOGLE_APPLICATION_CREDENTIALS
            client = vision.ImageAnnotatorClient()
            return client
        
        # 方法4: デフォルト認証情報を使用（GCP環境で実行する場合）
        try:
            client = vision.ImageAnnotatorClient()
            return client
        except Exception:
            pass
        
        logger.error("Google Cloud Vision APIの認証情報が設定されていません。GOOGLE_APPLICATION_CREDENTIALSまたはGOOGLE_APPLICATION_CREDENTIALS_JSONを設定してください。")
        return None
    except Exception as e:
        logger.error(f"Vision API client initialization error: {e}", exc_info=True)
        return None


def extract_text_from_image(image_file) -> Optional[str]:
    """
    画像からテキストを抽出（OCR）
    
    Args:
        image_file: アップロードされた画像ファイル
        
    Returns:
        抽出されたテキスト、エラー時はNone
    """
    try:
        client = initialize_vision_client()
        if not client:
            return None
        
        # 画像を読み込む
        image_content = image_file.read()
        image_file.seek(0)  # ファイルポインタをリセット
        
        image = vision.Image(content=image_content)
        
        # OCRを実行
        response = client.text_detection(image=image)
        texts = response.text_annotations
        
        if texts:
            # 最初の要素は全テキストを含む
            return texts[0].description
        else:
            logger.warning("OCR結果が空です")
            return None
            
    except Exception as e:
        logger.error(f"OCR error: {e}", exc_info=True)
        return None


def extract_text_from_pdf(pdf_file) -> Optional[str]:
    """
    PDFからテキストを抽出（OCR）
    
    注意: Google Cloud Vision APIはPDFを直接サポートしていません。
    PDFを画像に変換してからOCRを実行する必要があります。
    
    Args:
        pdf_file: アップロードされたPDFファイル
        
    Returns:
        抽出されたテキスト、エラー時はNone
    """
    try:
        from pdf2image import convert_from_bytes
        
        # PDFファイルの内容を読み込む
        pdf_content = pdf_file.read()
        pdf_file.seek(0)  # ファイルポインタをリセット
        
        # PDFを画像に変換
        images = convert_from_bytes(pdf_content)
        
        # 各ページからテキストを抽出
        all_texts = []
        client = initialize_vision_client()
        
        if not client:
            return None
        
        for image_pil in images:
            # PIL Imageをbytesに変換
            img_byte_arr = BytesIO()
            image_pil.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # OCRを実行
            image = vision.Image(content=img_byte_arr)
            response = client.text_detection(image=image)
            texts = response.text_annotations
            
            if texts:
                all_texts.append(texts[0].description)
        
        return "\n\n".join(all_texts) if all_texts else None
        
    except ImportError:
        logger.error("pdf2imageライブラリがインストールされていません。pip install pdf2imageを実行してください。")
        return None
    except Exception as e:
        logger.error(f"PDF OCR error: {e}", exc_info=True)
        return None


def parse_financial_statement_from_text(text: str) -> Dict[str, Any]:
    """
    OCRで抽出したテキストから決算書データをパース
    
    注意: これは基本的な実装です。実際の決算書の形式に応じて
    より高度なパースロジックが必要になる場合があります。
    
    Args:
        text: OCRで抽出したテキスト
        
    Returns:
        パースされた決算書データの辞書
    """
    import re
    from decimal import Decimal, InvalidOperation
    
    parsed_data = {
        'year': None,
        'sales': None,
        'gross_profit': None,
        'operating_profit': None,
        'ordinary_profit': None,
        'net_profit': None,
        # その他の項目...
    }
    
    # 年度の抽出（例: "令和6年" や "2024年"）
    year_patterns = [
        r'令和(\d+)年',
        r'(\d{4})年',
        r'R(\d+)年',  # R6年形式
    ]
    
    for pattern in year_patterns:
        match = re.search(pattern, text)
        if match:
            if '令和' in pattern or 'R' in pattern:
                # 令和年を西暦に変換
                reiwa_year = int(match.group(1))
                parsed_data['year'] = 2018 + reiwa_year
            else:
                parsed_data['year'] = int(match.group(1))
            break
    
    # 数値の抽出パターン
    # 項目名と数値のマッピング
    patterns = {
        'sales': [
            r'売上高[合計]*[：:]*\s*([\d,]+)',
            r'売上[：:]*\s*([\d,]+)',
        ],
        'gross_profit': [
            r'売上総利益[：:]*\s*([\d,]+)',
            r'総利益[：:]*\s*([\d,]+)',
        ],
        'operating_profit': [
            r'営業利益[：:]*\s*([\d,]+)',
        ],
        'ordinary_profit': [
            r'経常利益[：:]*\s*([\d,]+)',
        ],
        'net_profit': [
            r'当期純利益[：:]*\s*([\d,]+)',
            r'純利益[：:]*\s*([\d,]+)',
        ],
    }
    
    # 各項目を抽出
    for key, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    # カンマを除去して数値に変換（千円単位に変換）
                    value_str = match.group(1).replace(',', '').replace('，', '')
                    value = int(Decimal(value_str) // 1000)
                    parsed_data[key] = value
                    break
                except (ValueError, InvalidOperation):
                    continue
    
    return parsed_data

