# Google Drive API有効化ガイド

## エラー内容

以下のエラーが発生した場合、Google Drive APIが有効化されていません：

```
Google Drive API has not been used in project 261936238440 before or it is disabled.
Enable it by visiting https://console.developers.google.com/apis/api/drive.googleapis.com/overview?project=261936238440
```

## 解決方法

### ステップ1: Google Cloud Consoleにアクセス

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. プロジェクト `261936238440` を選択（または該当するプロジェクトを選択）

### ステップ2: Google Drive APIを有効化

1. 左メニューから「**APIとサービス**」→「**ライブラリ**」を選択
2. 検索ボックスに「**Google Drive API**」と入力
3. 「**Google Drive API**」を選択
4. 「**有効にする**」ボタンをクリック
5. APIが有効化されるまで数分待つ（通常は数秒で完了）

### ステップ3: 直接リンクから有効化（推奨）

以下のリンクから直接有効化ページにアクセスできます：

**https://console.developers.google.com/apis/api/drive.googleapis.com/overview?project=261936238440**

1. 上記のリンクをクリック
2. 「**有効にする**」ボタンをクリック
3. 有効化が完了するまで待つ

### ステップ4: 反映を確認

APIを有効化した後、反映まで数分かかる場合があります。以下のコマンドで再度試してください：

```bash
docker compose exec django python manage.py init_storage_folders
```

## 注意事項

- APIを有効化した直後は、反映まで数分かかる場合があります
- エラーが続く場合は、5-10分待ってから再度お試しください
- プロジェクトIDが異なる場合は、エラーメッセージ内のURLを使用してください

## 確認方法

Google Drive APIが有効化されているか確認するには：

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 左メニューから「**APIとサービス**」→「**有効なAPI**」を選択
3. 「**Google Drive API**」がリストに表示されていることを確認

## トラブルシューティング

### エラーが続く場合

1. **APIの有効化を確認**
   - 「有効なAPI」ページで「Google Drive API」が表示されているか確認

2. **プロジェクトの確認**
   - OAuth 2.0 クライアントIDが作成されたプロジェクトと同じプロジェクトでAPIを有効化しているか確認

3. **権限の確認**
   - Google Cloud Consoleにログインしているアカウントに、プロジェクトの編集権限があるか確認

4. **時間を置く**
   - APIを有効化した直後は、反映まで数分かかる場合があります。5-10分待ってから再度お試しください

