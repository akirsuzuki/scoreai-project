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


def preprocess_image(image_file) -> BytesIO:
    """
    画像の前処理（回転、コントラスト調整、ノイズ除去）
    
    Args:
        image_file: アップロードされた画像ファイル
        
    Returns:
        処理済み画像のBytesIO
    """
    try:
        from PIL import ImageEnhance, ImageFilter
        
        # 画像を読み込む
        img = Image.open(image_file)
        image_file.seek(0)  # ファイルポインタをリセット
        
        # 1. 自動回転（EXIF情報から）
        try:
            if hasattr(img, '_getexif') and img._getexif():
                exif = img._getexif()
                orientation = exif.get(274)  # Orientation tag
                if orientation == 3:
                    img = img.rotate(180, expand=True)
                elif orientation == 6:
                    img = img.rotate(270, expand=True)
                elif orientation == 8:
                    img = img.rotate(90, expand=True)
        except Exception:
            pass  # EXIF情報がない場合はスキップ
        
        # 2. グレースケール変換（カラー画像の場合、OCR精度向上のため）
        if img.mode not in ('L', '1'):  # グレースケールまたはモノクロでない場合
            img = img.convert('L')
        
        # 3. コントラスト調整（OCR精度向上のため）
        try:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.3)  # コントラストを1.3倍
        except Exception:
            pass
        
        # 4. シャープネス調整
        try:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.1)  # シャープネスを1.1倍
        except Exception:
            pass
        
        # 5. 解像度の確認（警告のみ、変更はしない）
        if img.size[0] < 1000 or img.size[1] < 1000:
            logger.warning(f"Low resolution image detected: {img.size}. OCR accuracy may be reduced.")
        
        # BytesIOに変換
        output = BytesIO()
        img.save(output, format='PNG', dpi=(300, 300))
        output.seek(0)
        return output
        
    except Exception as e:
        logger.warning(f"Image preprocessing error: {e}. Using original image.")
        # エラー時は元の画像を返す
        image_file.seek(0)
        return image_file


def extract_text_from_image(image_file, use_document_detection=True, preprocess=True) -> Optional[str]:
    """
    画像からテキストを抽出（OCR）
    
    Args:
        image_file: アップロードされた画像ファイル
        use_document_detection: Document Text Detection APIを使用するか（表形式に適している）
        preprocess: 画像の前処理を実行するか
    
    Returns:
        抽出されたテキスト、エラー時はNone
    """
    try:
        client = initialize_vision_client()
        if not client:
            return None
        
        # 画像の前処理（オプション）
        if preprocess:
            processed_image = preprocess_image(image_file)
            image_content = processed_image.read()
            processed_image.seek(0)
        else:
            image_content = image_file.read()
            image_file.seek(0)  # ファイルポインタをリセット
        
        image = vision.Image(content=image_content)
        
        # OCRを実行（Document Text Detection APIを使用）
        if use_document_detection:
            # Document Text Detection API（表形式の文書に最適）
            response = client.document_text_detection(
                image=image,
                image_context={
                    'language_hints': ['ja']  # 日本語を優先
                }
            )
            
            # Document Text Detection APIの結果からテキストを抽出
            if response.full_text_annotation:
                return response.full_text_annotation.text
            else:
                logger.warning("Document Text Detection APIの結果が空です")
                # フォールバック: text_detectionを試す
                response = client.text_detection(image=image)
                texts = response.text_annotations
                if texts:
                    return texts[0].description
        else:
            # 従来のtext_detection API
            response = client.text_detection(image=image)
            texts = response.text_annotations
            
            if texts:
                # 最初の要素は全テキストを含む
                return texts[0].description
        
        logger.warning("OCR結果が空です")
        return None
            
    except Exception as e:
        logger.error(f"OCR error: {e}", exc_info=True)
        return None


def extract_text_from_pdf(pdf_file, use_document_detection=True, preprocess=True) -> Optional[str]:
    """
    PDFからテキストを抽出（OCR）
    
    注意: Google Cloud Vision APIはPDFを直接サポートしていません。
    PDFを画像に変換してからOCRを実行する必要があります。
    
    Args:
        pdf_file: アップロードされたPDFファイル
        use_document_detection: Document Text Detection APIを使用するか
        preprocess: 画像の前処理を実行するか
    
    Returns:
        抽出されたテキスト、エラー時はNone
    """
    try:
        from pdf2image import convert_from_bytes
        
        # PDFファイルの内容を読み込む
        pdf_content = pdf_file.read()
        pdf_file.seek(0)  # ファイルポインタをリセット
        
        # PDFを画像に変換（DPIを高めに設定して精度向上）
        images = convert_from_bytes(pdf_content, dpi=300)
        
        # 各ページからテキストを抽出
        all_texts = []
        client = initialize_vision_client()
        
        if not client:
            return None
        
        for page_num, image_pil in enumerate(images, 1):
            logger.info(f"Processing PDF page {page_num}/{len(images)}")
            
            # PIL Imageをbytesに変換
            img_byte_arr = BytesIO()
            image_pil.save(img_byte_arr, format='PNG', dpi=(300, 300))
            img_byte_arr.seek(0)
            
            # 画像の前処理（オプション）
            if preprocess:
                processed_image = preprocess_image(img_byte_arr)
                img_content = processed_image.read()
            else:
                img_content = img_byte_arr.getvalue()
            
            # OCRを実行
            image = vision.Image(content=img_content)
            
            if use_document_detection:
                # Document Text Detection APIを使用
                response = client.document_text_detection(
                    image=image,
                    image_context={
                        'language_hints': ['ja']  # 日本語を優先
                    }
                )
                
                if response.full_text_annotation:
                    all_texts.append(response.full_text_annotation.text)
                else:
                    # フォールバック: text_detectionを試す
                    response = client.text_detection(image=image)
                    texts = response.text_annotations
                    if texts:
                        all_texts.append(texts[0].description)
            else:
                # 従来のtext_detection API
                response = client.text_detection(image=image)
                texts = response.text_annotations
                
                if texts:
                    all_texts.append(texts[0].description)
        
        return "\n\n--- ページ区切り ---\n\n".join(all_texts) if all_texts else None
        
    except ImportError:
        logger.error("pdf2imageライブラリがインストールされていません。pip install pdf2imageを実行してください。")
        return None
    except Exception as e:
        logger.error(f"PDF OCR error: {e}", exc_info=True)
        return None


def parse_financial_statement_from_text(text: str, use_ai: bool = False) -> Dict[str, Any]:
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


def parse_financial_statement_with_ai(text: str) -> Dict[str, Any]:
    """
    Gemini APIを使用して決算書データをパース（高精度）
    
    Args:
        text: OCRで抽出したテキスト
        
    Returns:
        パースされた決算書データの辞書
    """
    try:
        from ..utils.gemini import get_gemini_response_with_tokens
        import json
        import re
        
        # テキストが長すぎる場合は最初の8000文字のみ使用
        text_to_analyze = text[:8000] if len(text) > 8000 else text
        
        prompt = f"""
以下の決算書のOCRテキストから、決算書データを抽出してください。
JSON形式で返答してください。数値は千円単位で返してください。

OCRテキスト:
{text_to_analyze}

抽出する項目（存在する場合のみ）:
- year: 年度（西暦、整数、例: 2024）
- sales: 売上高（千円、整数）
- gross_profit: 売上総利益（千円、整数）
- operating_profit: 営業利益（千円、整数）
- ordinary_profit: 経常利益（千円、整数）
- net_profit: 当期純利益（千円、整数）
- total_assets: 総資産（千円、整数）
- total_liabilities: 総負債（千円、整数）
- total_net_assets: 純資産合計（千円、整数）
- capital_stock: 資本金（千円、整数）
- retained_earnings: 利益剰余金（千円、整数）

JSON形式で返答してください。存在しない項目はnullを返してください。
例: {{"year": 2024, "sales": 1000000, "operating_profit": 50000, ...}}
"""
        
        system_instruction = """あなたは財務データ抽出の専門家です。
OCRテキストから正確に数値を抽出し、JSON形式で返答してください。
数値の単位（円、千円、万円など）を正しく変換してください。
数値にカンマが含まれている場合は除去してください。"""
        
        response_text, _, _, _ = get_gemini_response_with_tokens(
            prompt=prompt,
            system_instruction=system_instruction,
            model='gemini-1.5-flash'  # 軽量で高速
        )
        
        if not response_text:
            logger.warning("AIパースが失敗しました。正規表現パースにフォールバックします。")
            return parse_financial_statement_from_text(text, use_ai=False)
        
        # JSONをパース
        # JSON部分を抽出（```json ... ``` または { ... }）
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
        if json_match:
            try:
                parsed_data = json.loads(json_match.group(0))
                logger.info(f"AIパース成功: {len(parsed_data)}項目を抽出")
                return parsed_data
            except json.JSONDecodeError as e:
                logger.warning(f"JSONパースエラー: {e}. 正規表現パースにフォールバックします。")
                return parse_financial_statement_from_text(text, use_ai=False)
        else:
            logger.warning("AIレスポンスからJSONが見つかりませんでした。正規表現パースにフォールバックします。")
            return parse_financial_statement_from_text(text, use_ai=False)
            
    except Exception as e:
        logger.error(f"AIパースエラー: {e}", exc_info=True)
        # エラー時は正規表現パースにフォールバック
        return parse_financial_statement_from_text(text, use_ai=False)


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

