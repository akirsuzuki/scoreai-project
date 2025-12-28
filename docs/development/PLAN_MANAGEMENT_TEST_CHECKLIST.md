# プラン管理機能 動作確認チェックリスト

## 前提条件

### 1. テスト用データの準備

#### FirmとUserFirmの作成
管理コマンドを使用して、テスト用のFirmとUserFirmを作成してください：

```bash
# デフォルト（最初のユーザーを使用）
docker compose exec django python manage.py create_test_firm

# 特定のユーザーを指定
docker compose exec django python manage.py create_test_firm --email your-email@example.com
```

コマンド実行後、Firm IDが表示されます。このIDをメモしておいてください。

#### プランの確認
プランが正しく作成されているか確認：

```bash
docker compose exec django python manage.py shell -c "from scoreai.models import FirmPlan; [print(f'{p.name} ({p.plan_type})') for p in FirmPlan.objects.all()]"
```

4つのプラン（Free, Starter, Professional, Enterprise）が表示されればOKです。

## 動作確認項目

### 1. プラン一覧表示

#### 確認URL
```
http://localhost:8000/plans/<firm_id>/
```

#### 確認項目
- [ ] 4つのプラン（Free, Starter, Professional, Enterprise）が表示される
- [ ] 各プランの料金が正しく表示される
- [ ] 各プランの機能制限が正しく表示される
- [ ] 現在のサブスクリプションがある場合、そのプランが強調表示される
- [ ] サイドバーに「プラン・サブスクリプション」リンクが表示される（Firmオーナーのみ）

### 2. プラン詳細表示

#### 確認URL
```
http://localhost:8000/plans/<firm_id>/<plan_id>/
```

#### 確認項目
- [ ] プランの詳細情報が正しく表示される
- [ ] 料金情報が正しく表示される
- [ ] 機能制限が正しく表示される
- [ ] 利用可能な機能が正しく表示される
- [ ] 「このプランに登録」ボタンが表示される（無料プランの場合は「無料で登録」）

### 3. 無料プラン（Free）の登録

#### 確認手順
1. Freeプランの詳細ページにアクセス
2. 「無料で登録」ボタンをクリック
3. サブスクリプション管理ページにリダイレクトされることを確認

#### 確認項目
- [ ] Freeプランに登録できる
- [ ] サブスクリプション管理ページにリダイレクトされる
- [ ] ステータスが「試用期間中」になっている
- [ ] 試用期間終了日が3ヶ月後になっている

### 4. サブスクリプション管理ページ

#### 確認URL
```
http://localhost:8000/plans/<firm_id>/subscription/
```

#### 確認項目
- [ ] 現在のプラン情報が表示される
- [ ] ステータスが正しく表示される
- [ ] 開始日、試用期間終了日（該当する場合）が表示される
- [ ] 利用状況（AI相談回数、OCR回数）が表示される
- [ ] 管理しているCompany数が表示される
- [ ] プログレスバーが正しく表示される（利用状況に応じて）

### 5. 有料プランの登録（Stripe未設定時）

#### 確認手順
1. Starter/Professional/Enterpriseプランの詳細ページにアクセス
2. 「このプランに登録」ボタンをクリック

#### 確認項目
- [ ] Stripe APIキーが設定されていない場合、エラーメッセージが表示される
- [ ] Stripe Price IDが設定されていない場合、エラーメッセージが表示される

### 6. 権限チェック

#### 確認項目
- [ ] Firmオーナーでないユーザーがアクセスした場合、エラーメッセージが表示される
- [ ] ログインしていないユーザーがアクセスした場合、ログインページにリダイレクトされる
- [ ] Firmオーナーのみサイドバーに「プラン・サブスクリプション」リンクが表示される

## エラー確認

### よくあるエラーと対処法

#### 1. `ModuleNotFoundError: No module named 'stripe'`
**対処法**: Dockerコンテナ内で`pip install stripe`を実行、またはDockerイメージを再ビルド

#### 2. `Firm matching query does not exist`
**対処法**: テスト用のFirmとUserFirmを作成してください（上記の前提条件を参照）

#### 3. `このFirmのオーナー権限がありません`
**対処法**: UserFirmで`is_owner=True`が設定されていることを確認してください

#### 4. テンプレートエラー
**対処法**: テンプレートファイルが正しく作成されているか確認してください

## 実装済み機能

以下の機能が実装されています：

1. **Stripe Webhook処理**: 支払い状況の自動更新
   - URL: `/stripe/webhook/`
   - 処理イベント:
     - `customer.subscription.created`: サブスクリプション作成時
     - `customer.subscription.updated`: サブスクリプション更新時
     - `customer.subscription.deleted`: サブスクリプション削除時
     - `invoice.payment_succeeded`: 支払い成功時
     - `invoice.payment_failed`: 支払い失敗時

2. **利用状況の自動追跡**: AI相談・OCR使用時のカウント
   - AI相談使用時に自動的にカウント
   - OCR使用時に自動的にカウント
   - 利用制限に達した場合はエラーメッセージを表示

3. **月次リセット機能**: 毎月1日に利用回数をリセット
   - 管理コマンド: `python manage.py reset_monthly_usage`
   - スケジュール設定: cronジョブで毎月1日の0時0分に実行

## 月次リセットのスケジュール設定

### cronジョブの設定

本番環境では、cronジョブを使用して毎月1日の0時0分に月次リセットを実行します。

#### Docker環境の場合

`docker-compose.yml`にcronサービスを追加するか、ホストマシンのcronを使用します。

#### ホストマシンのcronを使用する場合

```bash
# crontabを編集
crontab -e

# 以下の行を追加（毎月1日の0時0分に実行）
0 0 1 * * cd /path/to/scoreai-project && docker compose exec -T django python manage.py reset_monthly_usage
```

#### テスト実行

```bash
# DRY RUNモードで実行（実際にはリセットしない）
docker compose exec django python manage.py reset_monthly_usage --dry-run

# 強制リセット（既にリセット済みでもリセット）
docker compose exec django python manage.py reset_monthly_usage --force

# 通常実行
docker compose exec django python manage.py reset_monthly_usage
```

