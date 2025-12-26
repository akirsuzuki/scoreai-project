# クイックテストチェックリスト

## 事前準備

### 1. 環境変数の設定確認

`score/local_settings.py`に以下が設定されているか確認:

```python
# Google Gemini API（オプション - チャット機能をテストする場合）
GEMINI_API_KEY = 'your-gemini-api-key'

# Google Cloud Vision API（オプション - OCR機能をテストする場合）
GOOGLE_APPLICATION_CREDENTIALS = '/path/to/service-account-key.json'
```

### 2. Docker環境の起動

```bash
# コンテナをビルド（初回または変更後）
docker compose build

# コンテナを起動
docker compose up -d

# サーバーを起動
docker compose exec django python manage.py runserver 0.0.0.0:8000
```

### 3. 必要なライブラリのインストール確認

```bash
docker compose exec django pip install chardet google-generativeai google-cloud-vision pdf2image Pillow
```

## テスト項目

### ✅ CSV取り込み機能（必須テスト）

#### テスト1: エンコーディング自動検出
- [ ] マネーフォワードからShift-JIS形式のCSVをエクスポート
- [ ] `/import_fiscal_summary_month_MF/` にアクセス
- [ ] CSVファイルをアップロード
- [ ] エンコーディングが自動検出されることを確認（成功メッセージに表示）
- [ ] データが正常にインポートされることを確認

#### テスト2: プレビュー機能
- [ ] `/import_fiscal_summary_month_MF/` にアクセス
- [ ] CSVファイルを選択
- [ ] 「プレビュー」ボタンをクリック
- [ ] 以下が表示されることを確認:
  - [ ] 検出されたエンコーディング
  - [ ] 総行数
  - [ ] 最初の10行のデータ（テーブル形式）
- [ ] データが保存されていないことを確認（月次PL一覧で確認）

#### テスト3: エラーハンドリング
- [ ] 空のCSVファイルをアップロード → 「CSVファイルが空です」エラー
- [ ] 不正な構造のCSVをアップロード → 適切なエラーメッセージ
- [ ] 数値以外の値が含まれるCSVをアップロード → 行番号と列番号を含むエラーメッセージ

### ✅ Google Gemini API機能（オプション - APIキーが必要）

#### テスト4: AIチャット機能
- [ ] ダッシュボード（`/`）にアクセス
- [ ] チャットフォームに質問を入力（例: "債務の返済計画について教えてください"）
- [ ] 「送信」ボタンをクリック
- [ ] Gemini APIからの応答が表示されることを確認

#### テスト5: APIキー未設定時のエラー
- [ ] `GEMINI_API_KEY`をコメントアウトまたは削除
- [ ] チャット機能を使用
- [ ] 適切なエラーメッセージが表示されることを確認

### ✅ OCR機能（オプション - Vision APIキーが必要）

#### テスト6: 画像からのOCR
- [ ] `/import_fiscal_summary_ocr/` にアクセス
- [ ] 決算書のPNGまたはJPEG画像をアップロード
- [ ] OCR処理が実行されることを確認
- [ ] 抽出されたテキストからデータがパースされることを確認
- [ ] 年度別財務サマリー一覧でデータが表示されることを確認

#### テスト7: PDFからのOCR
- [ ] `/import_fiscal_summary_ocr/` にアクセス
- [ ] 決算書のPDFファイルをアップロード
- [ ] PDFが画像に変換され、OCRが実行されることを確認
- [ ] 複数ページがある場合、すべてのページが処理されることを確認

## トラブルシューティング

### 問題1: `ModuleNotFoundError: No module named 'chardet'`

**解決方法:**
```bash
docker compose exec django pip install chardet
```

### 問題2: `ImportError: cannot import name 'read_csv_with_auto_encoding'`

**解決方法:**
- `scoreai/utils/csv_utils.py`が存在するか確認
- `scoreai/utils/__init__.py`が存在するか確認
- サーバーを再起動: `docker compose restart django`

### 問題3: Gemini APIエラー

**解決方法:**
- `GEMINI_API_KEY`が正しく設定されているか確認
- APIキーが有効か確認（[Google AI Studio](https://makersuite.google.com/app/apikey)）

### 問題4: Vision APIエラー

**解決方法:**
- `GOOGLE_APPLICATION_CREDENTIALS`が正しく設定されているか確認
- サービスアカウントキーのパスが正しいか確認
- Cloud Vision APIが有効化されているか確認

## テスト結果の記録

テスト完了後、以下を記録してください:

```
テスト日時: ___________
テスト実施者: ___________

✅ 成功したテスト:
- [テスト項目名]

❌ 失敗したテスト:
- [テスト項目名] - [エラー内容]

📝 備考:
[その他のコメント]
```

