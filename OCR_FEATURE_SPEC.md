# 決算書OCR読み込み機能の仕様

## 機能概要

決算書のPDFや画像ファイルをアップロードすると、Google Cloud Vision APIを使用してOCR（光学文字認識）でテキストを抽出し、自動的に決算書データをパースしてインポートする機能です。

## 実装状況

✅ **実装済み**

- ビュー: `ImportFiscalSummaryFromOcrView` (`scoreai/views/ocr_views.py`)
- ユーティリティ: OCR処理関数 (`scoreai/utils/ocr.py`)
- フォーム: `OcrUploadForm` (`scoreai/forms.py`)
- テンプレート: `import_fiscal_summary_ocr.html`
- URL: `/import_fiscal_summary_ocr/`

## 対応ファイル形式

- **PDF**: 決算書のPDFファイル
- **画像**: PNG、JPEG、GIF、BMP形式

## 処理フロー

1. **ファイルアップロード**
   - ユーザーがPDFまたは画像ファイルをアップロード
   - ファイルタイプは自動検出（手動指定も可能）

2. **OCR処理**
   - Google Cloud Vision APIを使用してテキストを抽出
   - PDFの場合は、`pdf2image`で画像に変換してからOCR処理

3. **データパース**
   - 抽出されたテキストから正規表現で決算書データを抽出
   - 以下の項目を抽出：
     - 年度（令和年、西暦年に対応）
     - 売上高
     - 売上総利益
     - 営業利益
     - 経常利益
     - 当期純利益

4. **データ保存**
   - `FiscalSummary_Year`モデルに保存
   - 既存データがある場合は、上書きフラグで制御

## 抽出されるデータ項目

現在の実装では、以下の項目が抽出されます：

| 項目 | 抽出パターン | 備考 |
|------|------------|------|
| 年度 | 令和X年、R X年、YYYY年 | 令和年は西暦に自動変換 |
| 売上高 | "売上高"、"売上" | カンマ区切り数値に対応 |
| 売上総利益 | "売上総利益"、"総利益" | カンマ区切り数値に対応 |
| 営業利益 | "営業利益" | カンマ区切り数値に対応 |
| 経常利益 | "経常利益" | カンマ区切り数値に対応 |
| 当期純利益 | "当期純利益"、"純利益" | カンマ区切り数値に対応 |

**注意**: 数値は千円単位に変換されます（例: 1,000,000円 → 1000千円）

## 必要な設定

### 1. Google Cloud Vision APIの認証情報

以下のいずれかの方法で認証情報を設定する必要があります：

#### 方法1: 環境変数（推奨）
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

#### 方法2: settings.py
```python
GOOGLE_APPLICATION_CREDENTIALS = '/path/to/service-account-key.json'
```

#### 方法3: 環境変数（JSON文字列）
```bash
export GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type": "service_account", ...}'
```

### 2. 必要なPythonライブラリ

```bash
pip install google-cloud-vision pdf2image Pillow
```

### 3. システム要件

- `poppler-utils`（PDFを画像に変換するため）
  - Dockerfileに既に追加済み

## 制限事項と注意点

### 1. OCR精度

- **画像の品質が重要**: 高解像度で鮮明な画像ほど精度が向上します
- **レイアウト依存**: 決算書のレイアウトによっては、正しくパースできない場合があります
- **手動修正が必要な場合**: OCR結果は自動的にパースされますが、必要に応じて手動で修正してください

### 2. パースロジック

現在の実装は**基本的な正規表現パターンマッチング**を使用しています：

- 決算書の形式が標準的でない場合、正しく抽出できない可能性があります
- より高度なパースが必要な場合は、AI（Gemini APIなど）を使用した改善が可能です

### 3. 抽出項目の制限

現在は以下の項目のみ抽出されます：
- 年度
- 売上高
- 売上総利益
- 営業利益
- 経常利益
- 当期純利益

その他の項目（資産、負債、資本など）は抽出されません。

### 4. エラーハンドリング

- OCR処理に失敗した場合、エラーメッセージが表示されます
- テキスト抽出に失敗した場合、画像の品質を確認するよう促されます
- 年度が自動検出できない場合、手動入力が求められます

## 動作確認方法

### 1. 認証情報の確認

```bash
docker compose exec django python manage.py shell
```

```python
from scoreai.utils.ocr import initialize_vision_client
client = initialize_vision_client()
if client:
    print("✓ Vision APIクライアントの初期化に成功しました")
else:
    print("✗ Vision APIクライアントの初期化に失敗しました")
```

### 2. テスト実行

1. 決算書のPDFまたは画像ファイルを準備
2. `/import_fiscal_summary_ocr/`にアクセス
3. ファイルをアップロード
4. OCR処理を実行
5. 結果を確認

## 改善提案

### 1. AIを使用したパース改善

現在の正規表現ベースのパースを、Gemini APIを使用したより高度なパースに改善できます：

```python
def parse_financial_statement_with_ai(text: str) -> Dict[str, Any]:
    """Gemini APIを使用して決算書データをパース"""
    prompt = f"""
以下の決算書のOCRテキストから、決算書データを抽出してください。
JSON形式で返答してください。

{text}

抽出する項目:
- year: 年度（西暦）
- sales: 売上高（千円）
- gross_profit: 売上総利益（千円）
- operating_profit: 営業利益（千円）
- ordinary_profit: 経常利益（千円）
- net_profit: 当期純利益（千円）
"""
    # Gemini APIを呼び出してパース
    ...
```

### 2. 抽出項目の拡張

- 貸借対照表の項目（資産、負債、資本など）
- より詳細な損益計算書の項目
- 注記情報

### 3. プレビュー機能

OCR処理後、抽出されたデータを確認してから保存できるプレビュー機能

### 4. バッチ処理

複数の決算書を一度にアップロードして処理する機能

## トラブルシューティング

### エラー: "OCR機能が利用できません"

**原因**: 必要なライブラリがインストールされていない、または認証情報が設定されていない

**解決方法**:
1. ライブラリのインストール確認
   ```bash
   docker compose exec django pip list | grep -E "google-cloud-vision|pdf2image|Pillow"
   ```
2. 認証情報の設定確認
   ```bash
   docker compose exec django python manage.py shell
   >>> from scoreai.utils.ocr import initialize_vision_client
   >>> client = initialize_vision_client()
   ```

### エラー: "テキストの抽出に失敗しました"

**原因**: 画像の品質が低い、またはOCR処理に失敗

**解決方法**:
- より高解像度の画像を使用
- 画像の向きを確認（横向きの場合は回転）
- ファイル形式を確認

### エラー: "年度を自動検出できませんでした"

**原因**: OCRテキストから年度情報を抽出できない

**解決方法**:
- 手動で年度を入力
- 決算書の年度表記を確認

## 関連ファイル

- `scoreai/views/ocr_views.py` - OCRビュー
- `scoreai/utils/ocr.py` - OCR処理ユーティリティ
- `scoreai/forms.py` - OCRフォーム（`OcrUploadForm`）
- `templates/scoreai/import_fiscal_summary_ocr.html` - OCRアップロード画面
- `GOOGLE_API_SETUP.md` - Google API設定ガイド

