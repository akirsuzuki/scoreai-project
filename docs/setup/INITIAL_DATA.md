# 初期データ投入ガイド

## 概要

SCORE AIの各種機能を利用するために必要な初期データの投入方法を説明します。

## 目次

1. [AI相談機能の初期データ](#ai相談機能の初期データ)
2. [フォルダ構造の初期データ](#フォルダ構造の初期データ)
3. [Google Driveフォルダ構造の作成](#google-driveフォルダ構造の作成)

## AI相談機能の初期データ

### 方法1: Django管理コマンドを使用（推奨）

最も簡単で確実な方法です。

```bash
docker compose exec django python manage.py init_ai_consultation_data
```

このコマンドで以下が作成されます：
- 相談タイプ（財務相談、補助金・助成金相談、税務相談、法律相談）
- 各相談タイプのデフォルトスクリプト

### 実行例

```bash
$ docker compose exec django python manage.py init_ai_consultation_data
============================================================
AI相談機能の初期データ投入を開始します...
============================================================
✓ 相談タイプを作成しました: 財務相談
✓ 相談タイプを作成しました: 補助金・助成金相談
✓ 相談タイプを作成しました: 税務相談
✓ 相談タイプを作成しました: 法律相談
✓ 財務相談のデフォルトスクリプトを作成しました
✓ 補助金・助成金相談のデフォルトスクリプトを作成しました
✓ 税務相談のデフォルトスクリプトを作成しました
✓ 法律相談のデフォルトスクリプトを作成しました
============================================================
初期データ投入が完了しました！
============================================================
```

### データの確認

```bash
docker compose exec django python manage.py shell
```

```python
>>> from scoreai.models import AIConsultationType, AIConsultationScript
>>> AIConsultationType.objects.all()
<QuerySet [<AIConsultationType: 財務相談>, <AIConsultationType: 補助金・助成金相談>, ...]>
>>> AIConsultationScript.objects.all()
<QuerySet [<AIConsultationScript: 財務相談 - デフォルト>, ...]>
```

## フォルダ構造の初期データ

### システム規定のフォルダ構造をデータベースに初期化

```bash
docker compose exec django python manage.py init_document_folders
```

このコマンドで以下が作成されます：
- 決算書
- 試算表（貸借対照表、損益計算書、月次推移損益計算書、部門別損益計算書）
- 金銭消費貸借契約書
- 契約書（リース契約書、商品売買契約、賃貸借契約）

### 実行例

```bash
$ docker compose exec django python manage.py init_document_folders
✓ 決算書 を作成しました
✓ 試算表 を作成しました
✓ 貸借対照表 を作成しました
✓ 損益計算書 を作成しました
✓ 月次推移損益計算書 を作成しました
✓ 部門別損益計算書 を作成しました
✓ 金銭消費貸借契約書 を作成しました
✓ 契約書 を作成しました
✓ リース契約書 を作成しました
✓ 商品売買契約 を作成しました
✓ 賃貸借契約 を作成しました

初期化が完了しました。（作成: 11, 更新: 0）
```

## Google Driveフォルダ構造の作成

### 前提条件

- Google Driveと連携済みであること
- Google Drive APIが有効化されていること
- システム規定のフォルダ構造がデータベースに初期化されていること

### フォルダ構造の作成

```bash
docker compose exec django python manage.py init_storage_folders
```

このコマンドで以下が実行されます：
1. 各ユーザーのGoogle Driveに「S-CoreAI」フォルダを作成（存在しない場合）
2. 「S-CoreAI」フォルダの下にシステム規定のフォルダ構造を作成

### 特定のユーザーのみ初期化

```bash
docker compose exec django python manage.py init_storage_folders --user-id 1
```

### 作成されるフォルダ構造

```
Google Drive ルート/
└── S-CoreAI/
    ├── 決算書/
    ├── 試算表/
    │   ├── 貸借対照表/
    │   ├── 損益計算書/
    │   ├── 月次推移損益計算書/
    │   └── 部門別損益計算書/
    ├── 金銭消費貸借契約書/
    └── 契約書/
        ├── リース契約書/
        ├── 商品売買契約/
        └── 賃貸借契約/
```

## トラブルシューティング

### エラー: "スーパーユーザーが見つかりません"

スーパーユーザーを作成してください：

```bash
docker compose exec django python manage.py createsuperuser
```

### エラー: "Google Drive API has not been used"

Google Drive APIが有効化されていません。以下の手順で有効化してください：

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. プロジェクトを選択
3. 「APIとサービス」→「ライブラリ」から「Google Drive API」を検索
4. 「有効にする」をクリック

詳細は [Google Drive連携セットアップガイド](./GOOGLE_DRIVE_SETUP.md) を参照してください。

### 既存データがある場合

すべてのコマンドは`get_or_create`を使用しているため、既存のデータは上書きされません。
既存データを削除したい場合は、Django管理画面またはシェルから削除してください。

## 次のステップ

1. サーバーを再起動
```bash
docker compose restart django
```

2. 各機能をテスト
- AI相談センター: `http://localhost:8000/ai-consultation/`
- ストレージ設定: `http://localhost:8000/storage/setting/`
- OCR読み込み: `http://localhost:8000/import_fiscal_summary_ocr/`

