# Google Drive連携セットアップガイド

## 概要

SCORE AIでGoogle Driveと連携するための包括的なセットアップガイドです。

## 目次

1. [前提条件](#前提条件)
2. [Google Cloud Consoleでの設定](#google-cloud-consoleでの設定)
3. [OAuth認証設定](#oauth認証設定)
4. [Google Drive APIの有効化](#google-drive-apiの有効化)
5. [環境変数の設定](#環境変数の設定)
6. [テスト手順](#テスト手順)
7. [トラブルシューティング](#トラブルシューティング)

## 前提条件

- Googleアカウントを持っていること
- Google Cloud Consoleへのアクセス権限があること（管理者のみ）
- Docker環境が起動していること（ローカルテストの場合）

## Google Cloud Consoleでの設定

### 1. プロジェクトの作成または選択

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成（または既存のプロジェクトを選択）
3. プロジェクト名を入力して作成

### 2. OAuth同意画面の設定

1. 左メニューから「**APIとサービス**」→「**OAuth同意画面**」を選択
2. **ユーザータイプ**を選択：
   - **テスト環境**: 「外部」を選択（後で公開可能）
   - **本番環境**: 「内部」を選択（Google Workspaceの場合）
3. **アプリ情報**を入力：
   - **アプリ名**: `SCORE AI`
   - **ユーザーサポートメール**: あなたのメールアドレス
   - **デベロッパーの連絡先情報**: あなたのメールアドレス
4. 「**スコープ**」で「保存して次へ」をクリック
5. 「**テストユーザー**」で：
   - **重要**: 使用するGoogleアカウント（例: `akirsuzuki@gmail.com`）を必ず追加
   - 「**+ ユーザーを追加**」ボタンをクリック
   - メールアドレスを入力して「追加」をクリック
   - **テストユーザーに追加されていないアカウントでは認証できません**
6. 「**概要**」で設定を確認して「ダッシュボードに戻る」

**重要**: 外部ユーザータイプの場合、テストユーザーに追加されていないアカウントでは「エラー 403: access_denied」が発生します。

### 3. OAuth 2.0 クライアントIDの作成

1. 左メニューから「**APIとサービス**」→「**認証情報**」を選択
2. 「**認証情報を作成**」→「**OAuth 2.0 クライアントID**」を選択
3. **アプリケーションの種類**を「**ウェブアプリケーション**」に選択
4. **名前**を入力（例: `SCORE AI Web Client`）
5. 「**承認済みのリダイレクト URI**」に以下を追加：
   ```
   http://localhost:8000/storage/google-drive/callback/
   ```
   （本番環境の場合は、実際のドメインに置き換えてください）
   **重要**: 末尾のスラッシュ（`/`）を含めること
6. 「**作成**」をクリック
7. **クライアントID**と**クライアントシークレット**をコピー（後で使用します）

## Google Drive APIの有効化

**重要**: Google Drive APIを使用するには、APIを有効化する必要があります。

### 方法1: 直接リンクから有効化（推奨）

以下のリンクから直接有効化ページにアクセスできます：

**https://console.developers.google.com/apis/api/drive.googleapis.com/overview?project=YOUR_PROJECT_ID**

1. 上記のリンクをクリック（`YOUR_PROJECT_ID`を実際のプロジェクトIDに置き換え）
2. 「**有効にする**」ボタンをクリック
3. 有効化が完了するまで待つ（通常は数秒）

### 方法2: Google Cloud Consoleから有効化

1. 左メニューから「**APIとサービス**」→「**ライブラリ**」を選択
2. 検索ボックスに「**Google Drive API**」と入力
3. 「**Google Drive API**」を選択
4. 「**有効にする**」ボタンをクリック
5. APIが有効化されるまで数分待つ（通常は数秒で完了）

**注意**: APIを有効化した直後は、反映まで数分かかる場合があります。エラーが発生する場合は、数分待ってから再度お試しください。

## 環境変数の設定

### ローカル開発環境（local_settings.py）

`score/local_settings.py`に以下の設定を追加：

```python
# Google Drive OAuth2設定
GOOGLE_DRIVE_CLIENT_ID = 'あなたのクライアントID'
GOOGLE_DRIVE_CLIENT_SECRET = 'あなたのクライアントシークレット'
GOOGLE_DRIVE_REDIRECT_URI = 'http://localhost:8000/storage/google-drive/callback/'
```

### 本番環境

環境変数として設定：

```bash
export GOOGLE_DRIVE_CLIENT_ID='あなたのクライアントID'
export GOOGLE_DRIVE_CLIENT_SECRET='あなたのクライアントシークレット'
export GOOGLE_DRIVE_REDIRECT_URI='https://yourdomain.com/storage/google-drive/callback/'
```

## 設定の構造について

### 2種類の設定

1. **OAuth2クライアントID/シークレット（アプリケーション全体）**
   - 管理者が`local_settings.py`で設定
   - アプリケーション全体で1つの設定
   - すべてのユーザーがこの設定を使用してGoogle認証を行う

2. **各ユーザーのアクセストークン（ユーザーごと）**
   - 各ユーザーが自分のGoogleアカウントで認証
   - 認証後、各ユーザーのアクセストークン/リフレッシュトークンが`CloudStorageSetting`モデルに保存される
   - ユーザーごとに異なるGoogle Driveアカウントと連携可能

### 動作の流れ

1. **管理者**: Google Cloud ConsoleでOAuth2クライアントID/シークレットを作成し、`local_settings.py`に設定
2. **各ユーザー**: `/storage/setting/`にアクセスして「Google Driveと連携」をクリック
3. **各ユーザー**: 自分のGoogleアカウントでログインして認証
4. **システム**: 各ユーザーのアクセストークンを`CloudStorageSetting`に保存
5. **各ユーザー**: 自分のGoogle Driveアカウントのファイルにアクセス可能

## テスト手順

### ステップ1: サーバーの起動

```bash
docker compose up -d
docker compose exec django python manage.py runserver 0.0.0.0:8000
```

### ステップ2: ブラウザでのテスト

1. ブラウザで `http://localhost:8000` にアクセス
2. ログインする
3. `/storage/setting/` にアクセス
4. 「**Google Driveと連携**」ボタンをクリック
5. Googleアカウントでログイン
6. 権限を確認して「**許可**」をクリック
7. 設定画面で「**連携済み**」と表示されることを確認

### ステップ3: フォルダ構造の初期化

```bash
# システム規定のフォルダ構造をデータベースに初期化
docker compose exec django python manage.py init_document_folders

# フォルダ構造をGoogle Driveに作成
docker compose exec django python manage.py init_storage_folders
```

## トラブルシューティング

### エラー 403: access_denied

**原因**: OAuth同意画面が「テスト中」の状態で、使用しているGoogleアカウントが「テストユーザー」に追加されていない

**解決方法**:
1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. プロジェクトを選択
3. 左メニューから「**APIとサービス**」→「**OAuth同意画面**」を選択
4. 「**テストユーザー**」タブをクリック
5. 「**+ ユーザーを追加**」ボタンをクリック
6. 使用しているGoogleアカウントのメールアドレスを入力
7. 「**追加**」をクリック
8. 再度認証を試みる

### Google Drive API has not been used

**原因**: Google Drive APIが有効化されていない

**解決方法**:
1. [Google Drive API有効化ページ](https://console.developers.google.com/apis/api/drive.googleapis.com/overview)にアクセス
2. 「**有効にする**」ボタンをクリック
3. 数分待ってから再度試す

### 接続テストが失敗する

**原因**: トークンが期限切れ、または設定が正しくない

**解決方法**:
1. `/storage/setting/`で「接続を再テスト」ボタンをクリック
2. エラーが続く場合は、連携を解除して再度認証する

## 参考リンク

- [Google Drive API ドキュメント](https://developers.google.com/drive/api)
- [OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Google Cloud Console](https://console.cloud.google.com/)

