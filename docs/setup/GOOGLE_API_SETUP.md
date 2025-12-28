# Google API設定ガイド

## 概要

このアプリケーションでは、以下のGoogle APIを使用します：
1. **Google Gemini API**: AI相談機能
2. **Google Cloud Vision API**: OCR機能（決算書の読み込み）
3. **Google Drive API**: クラウドストレージ連携

## 2つのAPIの違い

### 1. Google Gemini API（AI相談機能）
- **用途**: AI相談機能（財務相談、補助金・助成金相談など）
- **認証方法**: **APIキー（文字列）**
- **設定場所**: `GEMINI_API_KEY`
- **取得方法**: [Google AI Studio](https://makersuite.google.com/app/apikey)から取得

### 2. Google Cloud Vision API（OCR機能）
- **用途**: 決算書OCR読み込み機能
- **認証方法**: **サービスアカウントキー（JSONファイル）** または **APIキー**
- **設定場所**: `GOOGLE_APPLICATION_CREDENTIALS`（ファイルパス）または `GOOGLE_APPLICATION_CREDENTIALS_JSON`（JSON文字列）
- **取得方法**: [Google Cloud Console](https://console.cloud.google.com/)から取得

### 3. Google Drive API（クラウドストレージ連携）
- **用途**: Google Driveとの連携
- **認証方法**: **OAuth 2.0**
- **設定場所**: `GOOGLE_DRIVE_CLIENT_ID`, `GOOGLE_DRIVE_CLIENT_SECRET`
- **詳細**: [Google Drive連携セットアップガイド](./GOOGLE_DRIVE_SETUP.md)を参照

## 設定の違いまとめ

| 項目 | Gemini API | Vision API | Drive API |
|------|-----------|------------|-----------|
| 認証方法 | APIキー（文字列） | サービスアカウントキー（JSONファイル） | OAuth 2.0 |
| 設定変数 | `GEMINI_API_KEY` | `GOOGLE_APPLICATION_CREDENTIALS` | `GOOGLE_DRIVE_CLIENT_ID`等 |
| 取得場所 | Google AI Studio | Google Cloud Console | Google Cloud Console |
| 用途 | AI相談 | OCR | ストレージ連携 |

## Google Gemini API キーの取得

1. [Google AI Studio](https://makersuite.google.com/app/apikey)にアクセス
2. Googleアカウントでログイン
3. 「Create API Key」をクリック
4. APIキーをコピー

## Google Cloud Vision API キーの取得

### 方法A: サービスアカウントキーを使用（推奨・本番環境）

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. プロジェクトを作成または選択
3. 「APIとサービス」→「ライブラリ」から「Cloud Vision API」を有効化
4. 「IAMと管理」→「サービスアカウント」でサービスアカウントを作成
5. サービスアカウントに「Cloud Vision API User」ロールを付与
6. サービスアカウントのキーをJSON形式でダウンロード
7. ダウンロードしたJSONファイルを安全な場所に保存

### 方法B: APIキーを使用（開発環境のみ）

1. 「APIとサービス」→「認証情報」からAPIキーを作成
2. APIキーをコピー

## 環境変数の設定

### ローカル開発環境（local_settings.py）

```python
# Google Gemini API
GEMINI_API_KEY = 'your-gemini-api-key-here'

# Google Cloud Vision API（サービスアカウントキーの場合）
GOOGLE_APPLICATION_CREDENTIALS = '/path/to/service-account-key.json'

# または、APIキーの場合（開発環境のみ）
GOOGLE_CLOUD_VISION_API_KEY = 'your-vision-api-key-here'
GOOGLE_CLOUD_PROJECT_ID = 'your-project-id'
```

### 本番環境（Herokuなど）

環境変数として設定：

```bash
# Gemini API
heroku config:set GEMINI_API_KEY=your-gemini-api-key

# Vision API（サービスアカウントキーの場合）
# サービスアカウントキーのJSONファイルの内容を環境変数として設定
heroku config:set GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type": "service_account", ...}'

# または、APIキーの場合（開発環境のみ）
heroku config:set GOOGLE_CLOUD_VISION_API_KEY=your-vision-api-key
heroku config:set GOOGLE_CLOUD_PROJECT_ID=your-project-id
```

## 注意事項

1. **セキュリティ**: APIキーは絶対にGitにコミットしないでください
2. **サービスアカウントキー**: 本番環境では必ずサービスアカウントキーを使用してください
3. **APIキーの制限**: APIキーには適切な制限（IPアドレス、リファラーなど）を設定してください
4. **コスト**: Google Cloud Vision APIは使用量に応じて課金されます。無料枠もありますが、制限を確認してください

## トラブルシューティング

### Gemini API エラー

- APIキーが正しく設定されているか確認
- APIキーに適切な権限があるか確認
- インターネット接続を確認

### Vision API エラー

- サービスアカウントキーのパスが正しいか確認
- サービスアカウントに適切なロールが付与されているか確認
- Cloud Vision APIが有効化されているか確認

## 設定確認方法

### Gemini APIの確認

```bash
docker compose exec django python manage.py shell
```

```python
from scoreai.utils.gemini import initialize_gemini
try:
    initialize_gemini()
    print("✓ Gemini API設定OK")
except Exception as e:
    print(f"✗ Gemini API設定エラー: {e}")
```

### Vision APIの確認

```bash
docker compose exec django python manage.py shell
```

```python
from scoreai.utils.ocr import initialize_vision_client
client = initialize_vision_client()
if client:
    print("✓ Vision API設定OK")
else:
    print("✗ Vision API設定エラー: 認証情報が設定されていません")
```

