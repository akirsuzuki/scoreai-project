# Google API設定の違い

## 2つのAPIの違い

このアプリケーションでは、**2つの異なるGoogle API**を使用しています：

### 1. Google Gemini API（AIチャット機能）
- **用途**: AI相談機能（財務相談、補助金相談など）
- **認証方法**: **APIキー（文字列）**
- **設定場所**: `GEMINI_API_KEY`
- **取得方法**: [Google AI Studio](https://makersuite.google.com/app/apikey)から取得
- **現在の設定**: ✅ 設定済み（`local_settings.py`に記載）

### 2. Google Cloud Vision API（OCR機能）
- **用途**: 決算書OCR読み込み機能
- **認証方法**: **サービスアカウントキー（JSONファイル）** または **APIキー**
- **設定場所**: `GOOGLE_APPLICATION_CREDENTIALS`（ファイルパス）または `GOOGLE_APPLICATION_CREDENTIALS_JSON`（JSON文字列）
- **取得方法**: [Google Cloud Console](https://console.cloud.google.com/)から取得
- **現在の設定**: ❌ 未設定

## 設定の違いまとめ

| 項目 | Gemini API | Vision API |
|------|-----------|------------|
| 認証方法 | APIキー（文字列） | サービスアカウントキー（JSONファイル） |
| 設定変数 | `GEMINI_API_KEY` | `GOOGLE_APPLICATION_CREDENTIALS` |
| 取得場所 | Google AI Studio | Google Cloud Console |
| 設定済み | ✅ はい | ❌ いいえ |

## Google Cloud Vision APIの設定方法

### ステップ1: Google Cloud Consoleでプロジェクトを作成

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. プロジェクトを作成（または既存のプロジェクトを選択）

### ステップ2: Cloud Vision APIを有効化

1. 「APIとサービス」→「ライブラリ」を開く
2. 「Cloud Vision API」を検索
3. 「有効にする」をクリック

### ステップ3: サービスアカウントキーを作成

1. 「IAMと管理」→「サービスアカウント」を開く
2. 「サービスアカウントを作成」をクリック
3. サービスアカウント名を入力（例: `scoreai-vision-api`）
4. 「作成して続行」をクリック
5. 「ロール」で「Cloud Vision API User」を選択
6. 「完了」をクリック
7. 作成したサービスアカウントをクリック
8. 「キー」タブ→「キーを追加」→「新しいキーを作成」
9. 「JSON」を選択して「作成」
10. JSONファイルがダウンロードされます

### ステップ4: 認証情報を設定

#### 方法A: ファイルパスで設定（推奨・ローカル開発）

1. ダウンロードしたJSONファイルをプロジェクトの安全な場所に保存
   - 例: `/Users/akirasuzuki/Desktop/work/score/scoreai-project/credentials/vision-api-key.json`
   - **注意**: `.gitignore`に追加してGitにコミットしないようにする

2. `local_settings.py`に追加：

```python
# Google Cloud Vision API（サービスアカウントキーのパス）
GOOGLE_APPLICATION_CREDENTIALS = '/Users/akirasuzuki/Desktop/work/score/scoreai-project/credentials/vision-api-key.json'
```

#### 方法B: 環境変数で設定

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/vision-api-key.json"
```

#### 方法C: Docker環境の場合

Dockerコンテナ内で使用する場合：

1. JSONファイルをプロジェクトディレクトリに配置（`.gitignore`に追加）
2. `docker-compose.yml`でボリュームマウント：

```yaml
services:
  django:
    volumes:
      - ./credentials:/app/credentials:ro  # 読み取り専用でマウント
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/vision-api-key.json
```

## 現在の設定状況

### ✅ 設定済み
- `GEMINI_API_KEY`: AI相談機能で使用中

### ❌ 未設定
- `GOOGLE_APPLICATION_CREDENTIALS`: OCR機能で必要（未設定のためOCR機能は動作しません）

## OCR機能を使用する場合

OCR機能（決算書読み込み）を使用する場合は、上記の手順でGoogle Cloud Vision APIの認証情報を設定してください。

設定しない場合、OCR機能は以下のエラーを表示します：
```
OCR機能が利用できません。必要なライブラリがインストールされているか確認してください。
```

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

## まとめ

- **GEMINI_API_KEY**: AI相談機能用（✅ 設定済み）
- **GOOGLE_APPLICATION_CREDENTIALS**: OCR機能用（❌ 未設定、必要に応じて設定）

OCR機能を使用しない場合は、設定は不要です。使用する場合は、上記の手順で設定してください。

