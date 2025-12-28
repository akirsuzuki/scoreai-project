# Stripe設定詳細ガイド

## 前提条件

- Stripeアカウントにログイン済み
- ローカル開発環境が動作している

## ステップ1: APIキーの取得

### 1-1. テストモードでAPIキーを取得

1. [Stripe Dashboard](https://dashboard.stripe.com/)にアクセス
2. 左メニューから「開発者」→「APIキー」をクリック
3. **APIキーページでテストモードのキーを確認**:
   - ページに「テストモードのキー」と「本番モードのキー」の2つのセクションが表示されます
   - 「テストモードのキー」セクションを確認してください
   - もし「本番モードのキー」しか表示されていない場合は、ページ上部に「テストモードのキーを表示」というリンクやボタンがあるかもしれません
4. **テストモードのキーをコピー**:
   - **公開可能キー（Publishable key）**: `pk_test_...` で始まる文字列
     - 「表示」または「Reveal test key」ボタンをクリックして表示
   - **シークレットキー（Secret key）**: `sk_test_...` で始まる文字列
     - 「表示」または「Reveal test key」ボタンをクリックして表示
     - **重要**: このキーは一度しか表示されない場合があります。必ずコピーしてください

**注意**: 
- 新規アカウントの場合は、デフォルトでテストモードのキーが表示されることが多いです
- APIキーが`pk_test_`または`sk_test_`で始まっていれば、それがテストモードのキーです
- `pk_live_`または`sk_live_`で始まるキーは本番モードのキーです（開発環境では使用しないでください）

### 1-2. local_settings.pyに設定

プロジェクトルートの`score/local_settings.py`ファイルを開き（存在しない場合は作成）、以下を追加：

```python
# Stripe設定（テストモード）
STRIPE_PUBLIC_KEY = 'pk_test_あなたの公開可能キー'
STRIPE_SECRET_KEY = 'sk_test_あなたのシークレットキー'
STRIPE_WEBHOOK_SECRET = ''  # 後で設定（ステップ3）
```

**注意**: `local_settings.py`は`.gitignore`に含まれているため、Gitにコミットされません。

## ステップ2: 価格（Price）の作成

各プランの価格をStripe Dashboardで作成します。

### 2-1. Starterプラン - 月額価格

1. Stripe Dashboardで「製品」→「価格」をクリック
2. 「価格を追加」ボタンをクリック
3. 以下の設定を入力：
   - **価格タイプ**: 「定期」を選択
   - **価格**: `9800`（円）
   - **請求頻度**: 「月ごと」を選択
   - **価格ID**: 自動生成されます（例: `price_xxxxx`）
4. 「価格を追加」をクリック
5. 作成された価格の**価格ID**をコピー（例: `price_1ABC...`）

### 2-2. Starterプラン - 年額価格

1. 同様に「価格を追加」をクリック
2. 以下の設定を入力：
   - **価格タイプ**: 「定期」を選択
   - **価格**: `98000`（円）
   - **請求頻度**: 「年ごと」を選択
3. 「価格を追加」をクリック
4. 作成された価格の**価格ID**をコピー

### 2-3. Professionalプラン - 月額・年額価格

同様の手順で以下を作成：
- **月額**: `29800`円
- **年額**: `298000`円

### 2-4. Enterpriseプラン - 月額・年額価格

同様の手順で以下を作成：
- **月額**: `79800`円
- **年額**: `798000`円

### 2-5. データベースに価格IDを設定

作成した価格IDをデータベースの`FirmPlan`モデルに設定します。

#### Django管理画面から設定する場合

1. ローカルサーバーを起動: `docker compose up`
2. 管理画面にアクセス: `http://localhost:8000/admin/`
3. 「Firm Plans」をクリック
4. 各プランを編集：
   - **Starterプラン**:
     - `stripe_price_id_monthly`: 月額価格IDを入力
     - `stripe_price_id_yearly`: 年額価格IDを入力
   - **Professionalプラン**: 同様に設定
   - **Enterpriseプラン**: 同様に設定

#### 管理コマンドで設定する場合

```bash
docker compose exec django python manage.py shell
```

```python
from scoreai.models import FirmPlan

# Starterプラン
starter = FirmPlan.objects.get(plan_type='starter')
starter.stripe_price_id_monthly = 'price_xxxxx'  # 月額価格ID
starter.stripe_price_id_yearly = 'price_yyyyy'  # 年額価格ID
starter.save()

# Professionalプラン
professional = FirmPlan.objects.get(plan_type='professional')
professional.stripe_price_id_monthly = 'price_xxxxx'
professional.stripe_price_id_yearly = 'price_yyyyy'
professional.save()

# Enterpriseプラン
enterprise = FirmPlan.objects.get(plan_type='enterprise')
enterprise.stripe_price_id_monthly = 'price_xxxxx'
enterprise.stripe_price_id_yearly = 'price_yyyyy'
enterprise.save()
```

## ステップ3: Webhookの設定

### 3-1. ローカル開発環境でのWebhook設定（Stripe CLIを使用）

ローカル開発環境では、Stripe CLIを使用してWebhookをローカルに転送します。

#### Stripe CLIのインストール

**macOS**:
```bash
brew install stripe/stripe-cli/stripe
```

**Linux/Windows**:
[Stripe CLI公式ページ](https://stripe.com/docs/stripe-cli)からインストール

#### Stripe CLIでログイン

```bash
stripe login
```

ブラウザが開くので、Stripeアカウントでログインして認証を完了します。

#### Webhookをローカルに転送

```bash
stripe listen --forward-to localhost:8000/stripe/webhook/
```

このコマンドを実行すると、**Webhook signing secret**が表示されます（例: `whsec_xxxxx`）。

このシークレットを`local_settings.py`に追加：

```python
STRIPE_WEBHOOK_SECRET = 'whsec_xxxxx'  # Stripe CLIから表示されたシークレット
```

**重要**: `stripe listen`コマンドは実行し続ける必要があります。別のターミナルで実行してください。

### 3-2. 本番環境でのWebhook設定

1. Stripe Dashboardで「開発者」→「Webhook」をクリック
2. 「エンドポイントを追加」をクリック
3. エンドポイントURLを入力:
   ```
   https://yourdomain.com/stripe/webhook/
   ```
   （例: `https://score-ai.net/stripe/webhook/`）
4. 「イベントを選択」をクリック
5. 以下のイベントを選択：
   - ✅ `customer.subscription.created`
   - ✅ `customer.subscription.updated`
   - ✅ `customer.subscription.deleted`
   - ✅ `invoice.payment_succeeded`
   - ✅ `invoice.payment_failed`
6. 「エンドポイントを追加」をクリック
7. 作成されたエンドポイントの「署名シークレットを表示」をクリック
8. 表示されたシークレット（`whsec_...`）をコピー
9. 本番環境の環境変数に設定:
   ```bash
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```

## ステップ4: 動作確認

### 4-1. 設定の確認

```bash
# Djangoシェルで確認
docker compose exec django python manage.py shell
```

```python
from django.conf import settings
print("STRIPE_PUBLIC_KEY:", settings.STRIPE_PUBLIC_KEY[:20] + "...")
print("STRIPE_SECRET_KEY:", settings.STRIPE_SECRET_KEY[:20] + "...")
print("STRIPE_WEBHOOK_SECRET:", settings.STRIPE_WEBHOOK_SECRET[:20] + "..." if settings.STRIPE_WEBHOOK_SECRET else "未設定")
```

### 4-2. プラン一覧の表示確認

1. ブラウザで `http://localhost:8000/plans/<firm_id>/` にアクセス
2. プラン一覧が表示されることを確認
3. 各プランの料金が正しく表示されることを確認

### 4-3. テスト決済の実行

1. Starter/Professional/Enterpriseプランの詳細ページにアクセス
2. 「このプランに登録」ボタンをクリック
3. Stripe Checkout画面が表示されることを確認
4. テストカード番号を入力:
   - **カード番号**: `4242 4242 4242 4242`
   - **有効期限**: 未来の日付（例: `12/34`）
   - **CVC**: 任意の3桁（例: `123`）
   - **郵便番号**: 任意（例: `12345`）
5. 「サブスクライブ」をクリック
6. サブスクリプションが作成されることを確認

### 4-4. Webhookの動作確認

1. `stripe listen`コマンドが実行されていることを確認
2. テスト決済を実行
3. ターミナルにWebhookイベントが表示されることを確認
4. サブスクリプション管理ページでステータスが「有効」になっていることを確認

## トラブルシューティング

### APIキーが正しく設定されていない

**エラー**: `Stripeの設定が完了していません`

**対処法**:
1. `local_settings.py`に正しく設定されているか確認
2. サーバーを再起動: `docker compose restart django`

### 価格IDが設定されていない

**エラー**: `Stripe Price IDが設定されていません`

**対処法**:
1. Stripe Dashboardで価格が作成されているか確認
2. データベースの`FirmPlan`に価格IDが設定されているか確認

### Webhookが動作しない

**対処法**:
1. `stripe listen`コマンドが実行されているか確認
2. `local_settings.py`の`STRIPE_WEBHOOK_SECRET`が正しく設定されているか確認
3. Djangoのログを確認: `docker compose logs django`

### テストカードでエラーが発生する

**エラー**: カードが拒否される

**対処法**:
- テストモードになっているか確認（APIキーが`pk_test_`または`sk_test_`で始まるか確認）
- カード番号が正しいか確認（`4242 4242 4242 4242`）

### テストモードが表示されない

**問題**: Stripe Dashboardでテストモードの表示が見つからない

**対処法**:
1. **APIキーページで確認**: 「開発者」→「APIキー」に移動
   - ページに「テストモードのキー」と「本番モードのキー」の2つのセクションが表示されます
   - 「テストモードのキー」セクションを探してください
2. **キーのプレフィックスで確認**: 表示されているキーが`pk_test_`または`sk_test_`で始まるか確認
   - `test`が含まれていればテストモードです
   - `live`が含まれていれば本番モードです
3. **テストモードのキーを表示する**:
   - APIキーページで「テストモードのキーを表示」や「Show test key」というリンクやボタンを探してください
   - または、ページ上部にタブや切り替えボタンがあるかもしれません
4. **新規アカウントの場合**: 新規アカウントはデフォルトでテストモードのキーが表示されることが多いです
5. **それでも見つからない場合**: 
   - Stripe Dashboardの左メニューで「開発者」→「APIキー」を開いた状態で、ページを下にスクロールして「テストモードのキー」セクションを探してください
   - または、Stripeサポートに問い合わせるか、Stripe Dashboardのヘルプを確認してください

## 参考リンク

- [Stripe Dashboard](https://dashboard.stripe.com/)
- [Stripe CLI ドキュメント](https://stripe.com/docs/stripe-cli)
- [Stripe テストカード](https://stripe.com/docs/testing)
- [Stripe Webhook ドキュメント](https://stripe.com/docs/webhooks)

