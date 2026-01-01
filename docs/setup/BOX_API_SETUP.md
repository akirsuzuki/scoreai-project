# Box API設定手順

## 概要

SCORE AIアプリケーションでBox連携を使用するために、Box Developer Consoleでアプリを作成し、OAuth2認証情報を取得する手順を説明します。

---

## 前提条件

- Boxアカウント（個人アカウントまたはビジネスアカウント）
- Box Developer Consoleへのアクセス権限

---

## 手順

### 1. Box Developer Consoleでアプリを作成

1. **Box Developer Consoleにアクセス**
   - ブラウザで [https://developer.box.com/](https://developer.box.com/) にアクセス
   - Boxアカウントでログイン

2. **新しいアプリを作成**
   - 右上の「My Apps」をクリック
   - 「Create New App」ボタンをクリック

3. **アプリタイプを選択**
   - 「Custom App」を選択
   - 「Next」をクリック

4. **認証方法を選択**
   - 認証方法の選択画面で、以下の2つのオプションが表示されます：
     - **OAuth 2.0 with JWT (Server Authentication)**: サーバー間認証用（このアプリでは使用しません）
     - **OAuth 2.0 with User Authentication (Standard)**: ユーザー認証用（**こちらを選択**）
   
   - ⚠️ **重要**: **「OAuth 2.0 with User Authentication (Standard)」を選択してください**
   - このアプリケーションでは、ユーザーが自分のBoxアカウントにアクセスする必要があるため、ユーザー認証方式を使用します
   - 「Next」をクリック

5. **アプリ名を入力**
   - アプリ名を入力（例: "SCORE AI Storage Integration"）
   - 「Create App」をクリック

---

### 2. OAuth2設定を構成

1. **アプリ設定画面に移動**
   - 作成したアプリをクリックして詳細画面を開く
   - 左側のメニューから「Configuration」（構成設定）を選択

2. **「アプリの構成設定に関する情報を追加します」画面での設定**

   「Configuration」画面では、以下のセクションを設定します：

   #### 2-1. OAuth 2.0 Credentials（OAuth 2.0認証情報）
   
   **Redirect URIを設定**
   - 「OAuth 2.0 Credentials」セクションを開く
   - 「Redirect URI」フィールドに以下を入力：
     ```
     http://localhost:8000/storage/box/callback/
     ```
     （開発環境の場合）
   
   - 本番環境の場合は、実際のドメインを設定：
     ```
     https://your-domain.com/storage/box/callback/
     ```
   
   - 「Add」ボタンをクリックして追加
   - ⚠️ **重要**: 複数の環境（開発・本番）を使用する場合は、両方のURIを追加してください
   - 「Save Changes」をクリックして保存

   #### 2-2. Application Scopes（アプリケーションスコープ）
   
   **必要なスコープを有効化**
   - 「OAuth 2.0 Credentials」セクション内の「Application Scopes」を確認
   - 以下のスコープを有効化してください：
     - ✅ **Read and write all files and folders stored in Box**
       - ファイルとフォルダの読み書きに必要
       - このスコープは必須です
   
   - 以下のスコープは**不要**です（無効のままでOK）：
     - ❌ Manage users（ユーザー管理）
     - ❌ Manage enterprise properties（エンタープライズ設定管理）
   
   - スコープを選択後、「Save Changes」をクリック

   #### 2-3. その他の設定（通常はデフォルトのままでOK）
   
   - **App Access Level**: デフォルトのままで問題ありません
   - **Advanced Features**: 通常は有効にする必要はありません

---

### 3. Client IDとClient Secretを取得

1. **認証情報を確認**
   - 「OAuth 2.0 Credentials」セクションで以下を確認：
     - **Client ID**: アプリのクライアントID
     - **Client Secret**: 「Reveal」ボタンをクリックして表示（初回のみ表示可能）

2. **認証情報をコピー**
   - Client IDとClient Secretを安全な場所にコピー
   - ⚠️ **重要**: Client Secretは一度しか表示されないため、必ずコピーしてください

---

### 4. 環境変数を設定

#### 開発環境（Docker Compose）

1. **`.env`ファイルまたは`local_settings.py`に追加**
   ```python
   # Box API設定
   BOX_CLIENT_ID = 'your_box_client_id_here'
   BOX_CLIENT_SECRET = 'your_box_client_secret_here'
   BOX_REDIRECT_URI = 'http://localhost:8000/storage/box/callback/'
   ```

2. **Dockerコンテナを再起動**
   ```bash
   docker compose restart web
   ```

#### 本番環境（Heroku）

1. **Heroku環境変数を設定**
   ```bash
   heroku config:set BOX_CLIENT_ID=your_box_client_id_here
   heroku config:set BOX_CLIENT_SECRET=your_box_client_secret_here
   heroku config:set BOX_REDIRECT_URI=https://your-domain.com/storage/box/callback/
   ```

2. **設定を確認**
   ```bash
   heroku config
   ```

---

### 5. Django設定ファイルの更新

`score/settings.py`または`score/local_settings.py`に以下を追加：

```python
# Box API設定
BOX_CLIENT_ID = os.environ.get('BOX_CLIENT_ID', '')
BOX_CLIENT_SECRET = os.environ.get('BOX_CLIENT_SECRET', '')
BOX_REDIRECT_URI = os.environ.get('BOX_REDIRECT_URI', 'http://localhost:8000/storage/box/callback/')
```

---

### 6. boxsdkパッケージのインストール

⚠️ **重要**: `requirements.txt`に`boxsdk`を追加した後、Dockerコンテナを再ビルドする必要があります。

#### 方法1: Dockerコンテナを再ビルド（推奨）

```bash
# コンテナを停止
docker compose down

# コンテナを再ビルド（requirements.txtから自動インストール）
docker compose build web

# コンテナを起動
docker compose up -d
```

#### 方法2: 実行中のコンテナに直接インストール

```bash
# コンテナ内でboxsdkをインストール
docker compose exec web pip install boxsdk

# コンテナを再起動
docker compose restart web
```

#### インストール確認

```bash
docker compose exec web pip list | grep boxsdk
```

`boxsdk`が表示されればインストール完了です。

---

### 7. 動作確認

1. **アプリケーションを起動**
   ```bash
   docker compose up -d
   ```

2. **Box連携をテスト**
   - ブラウザで `http://localhost:8000/storage/setting/` にアクセス
   - 「Boxと連携」ボタンをクリック
   - Boxの認証画面が表示されることを確認
   - 認証を完了すると、Boxアカウントに「S-CoreAI」フォルダが作成されることを確認

---

## トラブルシューティング

### エラー: "Invalid redirect_uri"

**原因**: Redirect URIがBox Developer Consoleで設定したものと一致していない

**解決方法**:
1. Box Developer Consoleで設定したRedirect URIを確認
2. 環境変数`BOX_REDIRECT_URI`が正しく設定されているか確認
3. 末尾のスラッシュ（`/`）が一致しているか確認

---

### エラー: "Invalid client_id or client_secret"

**原因**: Client IDまたはClient Secretが正しく設定されていない

**解決方法**:
1. Box Developer ConsoleでClient IDとClient Secretを再確認
2. 環境変数が正しく設定されているか確認
3. Dockerコンテナを再起動

---

### エラー: "Access denied"

**原因**: 必要なスコープが設定されていない

**解決方法**:
1. Box Developer Consoleで「Application Scopes」を確認
2. 「Read and write all files and folders stored in Box」が有効になっているか確認
3. スコープを更新後、再度認証を試行

---

### エラー: "Token refresh failed"

**原因**: リフレッシュトークンが無効または期限切れ

**解決方法**:
1. クラウドストレージ設定画面で「連携を解除」
2. 再度「Boxと連携」を実行して新しいトークンを取得

---

## セキュリティに関する注意事項

1. **Client Secretの管理**
   - Client Secretは機密情報です。Gitリポジトリにコミットしないでください
   - `.env`ファイルは`.gitignore`に追加してください
   - 本番環境では環境変数として管理してください

2. **Redirect URIの設定**
   - 本番環境では、HTTPSを使用してください
   - 許可されたRedirect URIのみを使用してください

3. **スコープの最小化**
   - 必要最小限のスコープのみを有効にしてください
   - 不要なスコープは無効にしてください

---

## 参考リンク

- [Box Developer Documentation](https://developer.box.com/)
- [Box OAuth 2.0 Documentation](https://developer.box.com/guides/authentication/oauth2/)
- [Box Python SDK Documentation](https://github.com/box/box-python-sdk)

---

## 更新履歴

- 2026-01-01: 初版作成

