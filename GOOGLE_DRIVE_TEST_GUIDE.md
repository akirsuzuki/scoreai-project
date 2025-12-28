# Google Drive連携テストガイド（localhost）

## 前提条件

- Docker環境が起動していること
- Googleアカウントを持っていること
- Google Cloud Consoleへのアクセス権限があること

## テスト手順

### ステップ1: Google Cloud Consoleでの設定

#### 1-1. プロジェクトの作成または選択

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. プロジェクトを選択（または新規作成）
3. プロジェクト名を確認

#### 1-2. OAuth同意画面の設定

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

#### 1-3. OAuth 2.0 クライアントIDの作成

1. 左メニューから「**APIとサービス**」→「**認証情報**」を選択
2. 「**認証情報を作成**」→「**OAuth 2.0 クライアントID**」を選択
3. **アプリケーションの種類**を「**ウェブアプリケーション**」に選択
4. **名前**を入力（例: `SCORE AI Web Client (localhost)`）
5. 「**承認済みのリダイレクト URI**」に以下を追加：
   ```
   http://localhost:8000/storage/google-drive/callback/
   ```
   **重要**: 末尾のスラッシュ（`/`）を含めること
6. 「**作成**」をクリック
7. **クライアントID**と**クライアントシークレット**をコピー
   - この画面を閉じると、シークレットは再表示できません
   - 必ずコピーして保存してください

#### 1-4. Google Drive APIの有効化

1. 左メニューから「**APIとサービス**」→「**ライブラリ**」を選択
2. 「**Google Drive API**」を検索
3. 「**Google Drive API**」を選択して「**有効にする**」をクリック

### ステップ2: アプリケーション側の設定

#### 2-1. local_settings.pyの更新

`score/local_settings.py`に以下を追加または更新：

```python
# Google Drive OAuth2設定
GOOGLE_DRIVE_CLIENT_ID = 'あなたのクライアントID'
GOOGLE_DRIVE_CLIENT_SECRET = 'あなたのクライアントシークレット'
GOOGLE_DRIVE_REDIRECT_URI = 'http://localhost:8000/storage/google-drive/callback/'
```

**例**:
```python
GOOGLE_DRIVE_CLIENT_ID = '123456789-abcdefghijklmnop.apps.googleusercontent.com'
GOOGLE_DRIVE_CLIENT_SECRET = 'GOCSPX-abcdefghijklmnopqrstuvwxyz'
GOOGLE_DRIVE_REDIRECT_URI = 'http://localhost:8000/storage/google-drive/callback/'
```

#### 2-2. 設定の確認

- クライアントIDとシークレットが正しく設定されているか確認
- リダイレクトURIが`http://localhost:8000/storage/google-drive/callback/`になっているか確認

### ステップ3: サーバーの起動

```bash
# Dockerコンテナを起動（まだ起動していない場合）
docker compose up -d

# サーバーを起動
docker compose exec django python manage.py runserver 0.0.0.0:8000
```

または、既に起動している場合は、サーバーを再起動：

```bash
# サーバーを再起動（設定変更を反映）
docker compose restart django
```

### ステップ4: ブラウザでのテスト

#### 4-1. アプリケーションにログイン

1. ブラウザで `http://localhost:8000` にアクセス
2. ログインする

#### 4-2. ストレージ設定画面にアクセス

1. ブラウザで `http://localhost:8000/storage/setting/` にアクセス
2. 「**Google Driveと連携**」ボタンが表示されることを確認

#### 4-3. OAuth認証を開始

1. 「**Google Driveと連携**」ボタンをクリック
2. 認証説明画面が表示されることを確認
3. 「**Googleアカウントで認証**」ボタンをクリック

#### 4-4. Google側での認証

1. Googleのログイン画面が表示される
2. **テストユーザーに追加したGoogleアカウント**でログイン
   - 外部ユーザータイプの場合、テストユーザーに追加されていないアカウントでは認証できません
3. 「**SCORE AIがあなたのGoogle Driveにアクセスすることを許可しますか？**」という画面が表示される
4. 権限を確認して「**許可**」をクリック

#### 4-5. 認証完了の確認

1. 自動的に設定画面に戻る
2. 「**連携済み**」と表示されることを確認
3. 「**SCORE AIがあなたのGoogle Driveにアクセス可能な状態です**」というメッセージが表示されることを確認

### ステップ5: 接続テスト

#### 5-1. 接続状態の確認

設定画面で以下を確認：
- 「**連携済み**」と表示されている
- ストレージタイプが「**Google Drive**」と表示されている
- 連携日時が表示されている

#### 5-2. エラーの確認

もしエラーが発生した場合：

1. **ブラウザのコンソール**を確認（F12キー）
2. **Dockerログ**を確認：
   ```bash
   docker compose logs django | tail -50
   ```
3. **エラーメッセージ**を確認

## よくあるエラーと対処法

### エラー: "redirect_uri_mismatch"

**原因**: Google Cloud Consoleで設定したリダイレクトURIと、アプリケーションで使用しているURIが一致していない

**対処法**:
1. Google Cloud Consoleの「認証情報」→「OAuth 2.0 クライアントID」を確認
2. 「承認済みのリダイレクト URI」に以下が正確に追加されているか確認：
   ```
   http://localhost:8000/storage/google-drive/callback/
   ```
3. `local_settings.py`の`GOOGLE_DRIVE_REDIRECT_URI`が以下になっているか確認：
   ```python
   GOOGLE_DRIVE_REDIRECT_URI = 'http://localhost:8000/storage/google-drive/callback/'
   ```

### エラー: "access_denied"

**原因**: テストユーザーに追加されていない、またはOAuth同意画面が公開されていない

**対処法**:
1. Google Cloud Consoleの「OAuth同意画面」を確認
2. 「テストユーザー」に、使用しているGoogleアカウントを追加
3. 外部ユーザータイプの場合、OAuth同意画面を公開する必要があります（本番環境のみ）

### エラー: "invalid_client"

**原因**: クライアントIDまたはクライアントシークレットが正しく設定されていない

**対処法**:
1. `local_settings.py`の設定を確認
2. クライアントIDとシークレットが正しくコピーされているか確認
3. 余分なスペースや改行が入っていないか確認

### エラー: "Google Drive OAuth設定が完了していません"

**原因**: `GOOGLE_DRIVE_CLIENT_ID`が設定されていない

**対処法**:
1. `local_settings.py`に`GOOGLE_DRIVE_CLIENT_ID`が設定されているか確認
2. サーバーを再起動して設定を反映

## テストチェックリスト

- [ ] Google Cloud Consoleでプロジェクトを作成/選択
- [ ] OAuth同意画面を設定
- [ ] OAuth 2.0 クライアントIDを作成
- [ ] リダイレクトURIを`http://localhost:8000/storage/google-drive/callback/`に設定
- [ ] Google Drive APIを有効化
- [ ] `local_settings.py`にクライアントIDとシークレットを設定
- [ ] サーバーを起動
- [ ] `/storage/setting/`にアクセス
- [ ] 「Google Driveと連携」ボタンをクリック
- [ ] Googleアカウントでログイン
- [ ] 権限を許可
- [ ] 設定画面で「連携済み」と表示されることを確認

## 次のステップ

連携が成功したら、以下の機能をテストできます：

1. **ファイルアップロード機能**（今後実装予定）
2. **フォルダ自動作成機能**（今後実装予定）
3. **OCR機能との統合**（今後実装予定）

## トラブルシューティング

### ログの確認

```bash
# Djangoログを確認
docker compose logs django | tail -100

# リアルタイムでログを確認
docker compose logs -f django
```

### 設定の再確認

```bash
# local_settings.pyの内容を確認（機密情報は表示されないように注意）
docker compose exec django python -c "from django.conf import settings; print('CLIENT_ID:', 'SET' if hasattr(settings, 'GOOGLE_DRIVE_CLIENT_ID') and settings.GOOGLE_DRIVE_CLIENT_ID else 'NOT SET')"
```

## 参考リンク

- [Google Drive API ドキュメント](https://developers.google.com/drive/api)
- [OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Google Cloud Console](https://console.cloud.google.com/)

