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


def parse_loan_contract_from_text(text: str) -> Dict[str, Any]:
    """
    OCRで抽出したテキストから金銭消費貸借契約書データをパース
    
    注意: これは基本的な実装です。実際の契約書の形式に応じて
    より高度なパースロジックが必要になる場合があります。
    
    Args:
        text: OCRで抽出したテキスト
        
    Returns:
        パースされた契約書データの辞書
    """
    import re
    from decimal import Decimal, InvalidOperation
    from datetime import datetime
    
    parsed_data = {
        'financial_institution_name': None,
        'principal': None,  # 借入元本（円）
        'issue_date': None,  # 実行日
        'start_date': None,  # 返済開始日
        'interest_rate': None,  # 利息（%）
        'monthly_repayment': None,  # 月返済額（円）
        'is_securedby_management': None,  # 経営者保証
        'is_collateraled': None,  # 担保
    }
    
    # 金融機関名の抽出
    # 一般的な金融機関名のパターン
    financial_institution_patterns = [
        r'(三菱UFJ銀行|三井住友銀行|みずほ銀行|りそな銀行|横浜銀行|静岡銀行|千葉銀行|きらぼし銀行)',
        r'(地方銀行|信用金庫|信用組合|労働金庫)',
        r'(株式会社\s*[^\s]+銀行)',
        r'([^\s]+銀行)',
        r'([^\s]+信用金庫)',
        r'([^\s]+信用組合)',
    ]
    
    for pattern in financial_institution_patterns:
        match = re.search(pattern, text)
        if match:
            parsed_data['financial_institution_name'] = match.group(1).strip()
            break
    
    # 借入元本の抽出（「金」「円」などの単位を含む）
    principal_patterns = [
        r'借入[金元本]*[：:]*\s*([\d,]+)\s*[千万億]*円',
        r'元本[：:]*\s*([\d,]+)\s*[千万億]*円',
        r'金額[：:]*\s*([\d,]+)\s*[千万億]*円',
        r'([\d,]+)\s*[千万億]*円[^\d]*借入',
        r'([\d,]+)\s*[千万億]*円[^\d]*元本',
    ]
    
    for pattern in principal_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                value_str = match.group(1).replace(',', '').replace('，', '')
                # 千万億の単位を処理
                multiplier = 1
                if '千万' in text[match.start():match.end()+20]:
                    multiplier = 10000000
                elif '万' in text[match.start():match.end()+20]:
                    multiplier = 10000
                elif '億' in text[match.start():match.end()+20]:
                    multiplier = 100000000
                elif '千' in text[match.start():match.end()+20]:
                    multiplier = 1000
                
                value = int(Decimal(value_str) * multiplier)
                parsed_data['principal'] = value
                break
            except (ValueError, InvalidOperation):
                continue
    
    # 実行日の抽出
    date_patterns = [
        r'実行日[：:]*\s*(\d{4})[年/\-](\d{1,2})[月/\-](\d{1,2})日?',
        r'契約日[：:]*\s*(\d{4})[年/\-](\d{1,2})[月/\-](\d{1,2})日?',
        r'(\d{4})[年/\-](\d{1,2})[月/\-](\d{1,2})日?[^\d]*実行',
        r'令和(\d+)年(\d{1,2})月(\d{1,2})日[^\d]*実行',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                if '令和' in pattern:
                    reiwa_year = int(match.group(1))
                    year = 2018 + reiwa_year
                    month = int(match.group(2))
                    day = int(match.group(3))
                else:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                parsed_data['issue_date'] = datetime(year, month, day).date()
                break
            except (ValueError, IndexError):
                continue
    
    # 返済開始日の抽出
    start_date_patterns = [
        r'返済開始日[：:]*\s*(\d{4})[年/\-](\d{1,2})[月/\-](\d{1,2})日?',
        r'(\d{4})[年/\-](\d{1,2})[月/\-](\d{1,2})日?[^\d]*返済開始',
        r'令和(\d+)年(\d{1,2})月(\d{1,2})日[^\d]*返済開始',
    ]
    
    for pattern in start_date_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                if '令和' in pattern:
                    reiwa_year = int(match.group(1))
                    year = 2018 + reiwa_year
                    month = int(match.group(2))
                    day = int(match.group(3))
                else:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                parsed_data['start_date'] = datetime(year, month, day).date()
                break
            except (ValueError, IndexError):
                continue
    
    # 利息（年利）の抽出
    interest_patterns = [
        r'利息[：:]*\s*([\d.]+)\s*%',
        r'年利[：:]*\s*([\d.]+)\s*%',
        r'利率[：:]*\s*([\d.]+)\s*%',
        r'([\d.]+)\s*%[^\d]*年利',
        r'([\d.]+)\s*%[^\d]*利息',
    ]
    
    for pattern in interest_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                value = Decimal(match.group(1))
                parsed_data['interest_rate'] = float(value)
                break
            except (ValueError, InvalidOperation):
                continue
    
    # 月返済額の抽出
    monthly_repayment_patterns = [
        r'月返済[額]*[：:]*\s*([\d,]+)\s*[千万億]*円',
        r'返済額[：:]*\s*([\d,]+)\s*[千万億]*円',
        r'([\d,]+)\s*[千万億]*円[^\d]*月返済',
        r'([\d,]+)\s*[千万億]*円[^\d]*返済額',
    ]
    
    for pattern in monthly_repayment_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                value_str = match.group(1).replace(',', '').replace('，', '')
                # 千万億の単位を処理
                multiplier = 1
                if '千万' in text[match.start():match.end()+20]:
                    multiplier = 10000000
                elif '万' in text[match.start():match.end()+20]:
                    multiplier = 10000
                elif '億' in text[match.start():match.end()+20]:
                    multiplier = 100000000
                elif '千' in text[match.start():match.end()+20]:
                    multiplier = 1000
                
                value = int(Decimal(value_str) * multiplier)
                parsed_data['monthly_repayment'] = value
                break
            except (ValueError, InvalidOperation):
                continue
    
    # 経営者保証の有無
    if re.search(r'経営者保証|代表者保証|個人保証', text):
        parsed_data['is_securedby_management'] = True
    elif re.search(r'経営者保証なし|代表者保証なし|個人保証なし', text):
        parsed_data['is_securedby_management'] = False
    
    # 担保の有無
    if re.search(r'担保[あり有]|抵当権|質権', text):
        parsed_data['is_collateraled'] = True
    elif re.search(r'担保なし|無担保', text):
        parsed_data['is_collateraled'] = False
    
    return parsed_data

