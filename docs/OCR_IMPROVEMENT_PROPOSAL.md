# OCR精度向上の改善提案

## 現状の問題点

1. **基本的なOCR APIの使用**
   - `text_detection`を使用（一般的なテキスト抽出向け）
   - 表形式の決算書には`document_text_detection`が適している

2. **正規表現ベースのパース**
   - 決算書のレイアウトに依存
   - 複雑な形式に対応できない

3. **抽出項目が限定的**
   - PL項目のみ（売上高、営業利益など）
   - BS項目（資産、負債、資本）が抽出されない

4. **画像の前処理なし**
   - 回転、コントラスト調整、ノイズ除去などがない

## 改善提案

### 1. Document Text Detection APIの使用（優先度：高）

**現状**: `text_detection`を使用
**改善**: `document_text_detection`を使用

**メリット**:
- 表形式の文書に最適化されている
- レイアウト情報（段落、テーブル、ブロック）を保持
- より正確なテキスト抽出

**実装例**:
```python
# 現状
response = client.text_detection(image=image)

# 改善後
response = client.document_text_detection(image=image)
# または
response = client.document_text_detection(
    image=image,
    image_context={
        'language_hints': ['ja']  # 日本語を優先
    }
)
```

### 2. AIを使用したパース改善（優先度：高）

**現状**: 正規表現ベースのパース
**改善**: Gemini APIを使用した構造化パース

**メリット**:
- レイアウトに依存しない
- より柔軟な抽出が可能
- エラー処理が容易

**実装例**:
```python
def parse_financial_statement_with_ai(text: str, ocr_metadata: Dict = None) -> Dict[str, Any]:
    """Gemini APIを使用して決算書データをパース"""
    from ..utils.gemini import get_gemini_response_with_tokens
    
    prompt = f"""
以下の決算書のOCRテキストから、決算書データを抽出してください。
JSON形式で返答してください。数値は千円単位で返してください。

OCRテキスト:
{text}

抽出する項目（存在する場合のみ）:
- year: 年度（西暦、整数）
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
"""
    
    system_instruction = """あなたは財務データ抽出の専門家です。
OCRテキストから正確に数値を抽出し、JSON形式で返答してください。
数値の単位（円、千円、万円など）を正しく変換してください。"""
    
    response = get_gemini_response_with_tokens(
        prompt=prompt,
        system_instruction=system_instruction,
        model='gemini-1.5-flash'  # 軽量で高速
    )
    
    if not response:
        return {}
    
    # JSONをパース
    import json
    try:
        # レスポンスからJSONを抽出
        text = response['text']
        # JSON部分を抽出（```json ... ``` または { ... }）
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            parsed_data = json.loads(json_match.group(0))
            return parsed_data
    except Exception as e:
        logger.error(f"Failed to parse AI response: {e}")
        return {}
    
    return {}
```

### 3. 画像の前処理（優先度：中）

**改善**: 画像の品質向上処理を追加

**実装例**:
```python
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np

def preprocess_image(image_file) -> BytesIO:
    """画像の前処理（回転、コントラスト調整、ノイズ除去）"""
    try:
        # 画像を読み込む
        img = Image.open(image_file)
        
        # 1. 自動回転（EXIF情報から）
        if hasattr(img, '_getexif'):
            exif = img._getexif()
            if exif:
                orientation = exif.get(274)  # Orientation tag
                if orientation == 3:
                    img = img.rotate(180, expand=True)
                elif orientation == 6:
                    img = img.rotate(270, expand=True)
                elif orientation == 8:
                    img = img.rotate(90, expand=True)
        
        # 2. グレースケール変換（カラー画像の場合）
        if img.mode != 'L':
            img = img.convert('L')
        
        # 3. コントラスト調整
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)  # コントラストを1.5倍
        
        # 4. シャープネス調整
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.2)  # シャープネスを1.2倍
        
        # 5. ノイズ除去（軽度）
        img = img.filter(ImageFilter.MedianFilter(size=3))
        
        # 6. 解像度の確認と調整（必要に応じて）
        # 最低解像度を確保（300 DPI推奨）
        if img.size[0] < 2000 or img.size[1] < 2000:
            # 解像度が低い場合は警告をログに記録
            logger.warning(f"Low resolution image: {img.size}")
        
        # BytesIOに変換
        output = BytesIO()
        img.save(output, format='PNG', dpi=(300, 300))
        output.seek(0)
        return output
        
    except Exception as e:
        logger.error(f"Image preprocessing error: {e}", exc_info=True)
        # エラー時は元の画像を返す
        image_file.seek(0)
        return image_file
```

### 4. 抽出項目の拡張（優先度：中）

**現状**: PL項目のみ
**改善**: BS項目も抽出

**追加項目**:
- 資産の部（流動資産、固定資産など）
- 負債の部（流動負債、固定負債など）
- 純資産の部（資本金、利益剰余金など）

### 5. エラーハンドリングの改善（優先度：中）

**改善**: より詳細なエラーメッセージとリトライ機能

**実装例**:
```python
def extract_text_with_retry(image_file, max_retries=3) -> Optional[str]:
    """リトライ機能付きOCR"""
    for attempt in range(max_retries):
        try:
            result = extract_text_from_image(image_file)
            if result:
                return result
            # リトライ前に画像を前処理
            if attempt < max_retries - 1:
                image_file.seek(0)
                image_file = preprocess_image(image_file)
        except Exception as e:
            logger.warning(f"OCR attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise
    return None
```

### 6. プレビュー機能の改善（優先度：低）

**改善**: OCR結果の可視化と編集機能

- 抽出されたテキストのハイライト表示
- 抽出された数値の確認と修正
- 抽出できなかった項目の手動入力

## 実装優先順位

1. **Document Text Detection APIの使用**（即座に効果あり）
2. **AIを使用したパース改善**（精度向上に大きく寄与）
3. **画像の前処理**（画像品質が低い場合に有効）
4. **抽出項目の拡張**（ユーザー価値向上）
5. **エラーハンドリングの改善**（ユーザー体験向上）
6. **プレビュー機能の改善**（ユーザー体験向上）

## 実装コスト

- **Document Text Detection API**: 低（API呼び出しを変更するだけ）
- **AIパース**: 中（Gemini APIの統合が必要、コスト増加）
- **画像前処理**: 低（PILを使用、既にインストール済み）
- **抽出項目拡張**: 中（AIパースと組み合わせると容易）
- **エラーハンドリング**: 低（既存コードの改善）
- **プレビュー機能**: 高（UI実装が必要）

## 推奨実装順序

1. **Phase 1**: Document Text Detection APIの使用 + 画像前処理
2. **Phase 2**: AIパースの実装（オプションとして提供）
3. **Phase 3**: 抽出項目の拡張
4. **Phase 4**: エラーハンドリングとプレビュー機能の改善

