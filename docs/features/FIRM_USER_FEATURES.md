# Firmユーザー向け機能一覧

## 📋 目次
1. [実装済み機能](#実装済み機能)
2. [今後実装すべき機能](#今後実装すべき機能)
3. [優先度別実装計画](#優先度別実装計画)

---

## ✅ 実装済み機能

### 1. プラン・サブスクリプション管理

#### 1.1 プラン一覧・詳細表示
- **URL**: `/plans/<firm_id>/`
- **ビュー**: `PlanListView`, `PlanDetailView`
- **機能**:
  - 利用可能なプラン一覧の表示（Free, Starter, Professional, Enterprise）
  - 各プランの詳細情報表示（料金、機能制限、特徴）
  - 現在のプランとの比較表示
  - プラン変更ボタン

#### 1.2 サブスクリプション管理
- **URL**: `/plans/<firm_id>/subscription/`
- **ビュー**: `SubscriptionManageView`
- **機能**:
  - 現在のプラン情報表示
  - サブスクリプションステータス表示（試用期間中、有効、支払い遅延など）
  - 利用状況の表示（AI相談回数、OCR読み込み回数）
  - 管理しているCompany数の表示
  - プラン変更リンク

#### 1.3 Stripe連携
- **機能**:
  - Stripe Checkoutによる決済処理
  - Webhookによる自動サブスクリプション更新
  - プラン変更の自動反映
  - 請求書支払い成功時の処理
  - 支払い失敗時の処理

#### 1.4 プラン制限チェック
- **実装場所**: `scoreai/utils/plan_limits.py`
- **機能**:
  - Company数制限のチェック
  - 現在のCompany数と上限の表示
  - Company追加時の制限チェック
  - 無制限プランの判定

### 2. クライアント（Company）管理

#### 2.1 クライアント一覧
- **URL**: `/firm_clientslist/`
- **ビュー**: `ClientsList`
- **機能**:
  - Firmに属するCompany一覧の表示
  - プラン制限情報の表示
  - Company追加機能（プラン制限チェック付き）
  - アサインされているクライアント一覧の表示（選択中のFirmに属するもののみ）

#### 2.2 アサイン一覧
- **URL**: `/assigned-clients/`
- **ビュー**: `AssignedClientsListView`
- **機能**:
  - 自分がアサインされているクライアント一覧の表示（選択中のFirmに属するもののみ）
  - 各クライアントの選択機能

### 3. スタッフ管理

#### 3.1 Firmメンバー管理
- **URL**: `/firm/<firm_id>/members/`
- **ビュー**: `FirmMemberListView`, `FirmMemberInviteView`, `FirmMemberDeleteView`, `FirmInvitationCancelView`
- **機能**:
  - ✅ メンバー一覧の表示
  - ✅ メンバーの追加・削除
  - ✅ 権限の設定（オーナー、メンバー）
  - ✅ メンバーの招待機能（メール招待）
  - ✅ メンバーのアクティブ/非アクティブ管理
  - ✅ 招待中のメンバー一覧表示

### 4. 利用状況追跡

#### 4.1 月次利用状況の記録
- **モデル**: `FirmUsageTracking`, `CompanyUsageTracking`
- **機能**:
  - AI相談回数の記録（Company Userのみ）
  - OCR読み込み回数の記録（Company Userのみ）
  - API利用回数の記録（Firm/Companyレベル）
  - 月次リセット機能（管理コマンド `reset_monthly_usage`）

#### 4.2 利用状況の表示
- **表示場所**: サブスクリプション管理ページ
- **機能**:
  - 現在月の利用状況表示
  - プログレスバーによる視覚的な表示
  - 残り月数の表示
  - 制限に近づいた場合の警告表示

#### 4.3 利用状況の自動追跡
- **実装場所**: `scoreai/utils/usage_tracking.py`
- **機能**:
  - AI相談実行時の自動カウント（Company Userのみ）
  - OCR処理実行時の自動カウント（Company Userのみ）
  - API利用回数の自動カウント（Firm/Companyレベル）
  - 制限チェック機能

### 5. 権限管理

#### 5.1 Firmオーナー権限チェック
- **Mixin**: `FirmOwnerMixin` (`scoreai/mixins.py`)
- **機能**:
  - Firmオーナーのみがアクセス可能な機能の保護
  - プラン管理機能へのアクセス制御
  - サブスクリプション管理へのアクセス制御
  - スタッフ管理へのアクセス制御

#### 5.2 ユーザー属性の管理
- **モデル**: `UserFirm`
- **機能**:
  - Firmへのユーザー追加
  - オーナー権限の設定
  - アクティブ/非アクティブの管理
  - 選択中のFirmの管理

#### 5.3 Companyメンバー管理
- **URL**: `/company/<company_id>/members/`
- **ビュー**: `CompanyMemberListView`, `CompanyMemberInviteView`, `CompanyMemberDeleteView`
- **機能**:
  - Companyに所属するメンバー一覧の表示
  - メンバーの招待（メール招待）
  - メンバーの削除（非アクティブ化）
  - オーナー権限・マネージャー権限の設定
  - 招待中のメンバー一覧表示

### 6. データモデル

#### 6.1 Firm関連モデル
- **Firm**: Firmの基本情報
- **UserFirm**: ユーザーとFirmの関連
- **FirmCompany**: FirmとCompanyの関連
- **FirmPlan**: プランの定義
- **FirmSubscription**: サブスクリプション情報
- **FirmUsageTracking**: 利用状況の記録

---

## 🚀 今後実装すべき機能

### 優先度: 高

#### 1. ✅ Firmメンバー管理機能（実装済み）
- **URL**: `/firm/<firm_id>/members/`
- **ビュー**: `FirmMemberListView`, `FirmMemberInviteView`, `FirmMemberDeleteView`, `FirmInvitationCancelView`
- **機能**:
  - ✅ メンバー一覧の表示
  - ✅ メンバーの追加・削除
  - ✅ 権限の設定（オーナー、メンバー）
  - ✅ メンバーの招待機能（メール招待）
  - ✅ メンバーのアクティブ/非アクティブ管理
  - ✅ 招待中のメンバー一覧表示

#### 2. ✅ プランダウングレード時の処理（実装済み）
- **実装場所**: `scoreai/utils/plan_downgrade.py`, `scoreai/utils/plan_limits.py`
- **機能**:
  - ✅ グレース期間の設定（`FirmCompany.grace_period_end`）
  - ✅ 超過Companyの警告表示（通知機能と連携）
  - ✅ 自動的なCompany無効化（グレース期間後、Stripe Webhookで処理）
  - ✅ ダウングレード前の確認画面（Stripe Checkoutで処理）
  - ✅ グレース期間終了の通知

#### 3. ✅ 利用状況の詳細レポート（実装済み）
- **URL**: `/firm/<firm_id>/usage/report/`
- **ビュー**: `UsageReportView`, `CompanyUsageReportView`
- **機能**:
  - ✅ 月次利用状況のグラフ表示（Chart.js使用）
  - ✅ 過去数ヶ月の利用状況の比較（1-24ヶ月選択可能）
  - ✅ Company別の利用状況表示
  - ✅ Company別の詳細レポート（`/firm/<firm_id>/companies/<company_id>/usage/`）
  - ⏳ エクスポート機能（CSV/Excel）は未実装

#### 4. ✅ 請求履歴の表示（実装済み）
- **URL**: `/firm/<firm_id>/billing/history/`
- **ビュー**: `BillingHistoryView`, `BillingInvoiceDetailView`, `PaymentMethodUpdateView`
- **機能**:
  - ✅ 過去の請求書一覧（Stripe Invoice）
  - ✅ 請求書の詳細表示
  - ✅ 請求書のダウンロード（PDF、Stripeから直接）
  - ✅ 支払い方法の管理（Stripe Checkout経由）

### 優先度: 中

#### 5. ✅ Firm設定管理（部分実装）
- **URL**: `/firm/<firm_id>/settings/`
- **ビュー**: `FirmSettingsView`
- **機能**:
  - ✅ Firm名の変更
  - ✅ APIキー・APIプロバイダーの設定（Firm/Companyレベル）
  - ⏳ Firmの説明・プロフィール設定（未実装）
  - ⏳ 通知設定（未実装）
  - ⏳ データ保持期間の設定（未実装）

#### 6. ✅ 通知機能（実装済み）
- **URL**: `/firm/<firm_id>/notifications/`
- **ビュー**: `NotificationListView`, `NotificationDetailView`, `NotificationMarkReadView`, `NotificationMarkAllReadView`
- **モデル**: `FirmNotification`
- **機能**:
  - ✅ プラン制限に近づいた場合の通知
  - ✅ 支払い失敗時の通知
  - ✅ サブスクリプション更新の通知
  - ✅ メンバー招待の通知
  - ✅ プランダウングレード時の通知
  - ✅ グレース期間終了の通知
  - ✅ 未読通知数の表示（ヘッダーアイコン）

#### 7. ✅ Company別の利用状況表示（実装済み）
- **URL**: `/firm/<firm_id>/companies/<company_id>/usage/`
- **ビュー**: `CompanyUsageReportView`
- **機能**:
  - ✅ Company別のAI相談回数
  - ✅ Company別のOCR読み込み回数
  - ✅ Company別の利用状況グラフ（Chart.js使用）
  - ✅ 月次利用状況の一覧表示
  - ✅ 表示期間の選択（3/6/12/24ヶ月）

#### 8. ✅ プラン変更履歴（実装済み）
- **URL**: `/firm/<firm_id>/subscription/history/`
- **ビュー**: `SubscriptionHistoryView`
- **モデル**: `SubscriptionHistory`
- **機能**:
  - ✅ プラン変更の日時と内容
  - ✅ 変更前後のプラン比較
  - ✅ Stripeイベントとの連携（`customer.subscription.updated`）
  - ⏳ 変更理由の記録（未実装）

### 優先度: 低（将来実装）

#### 9. API連携機能
- **概要**: 外部システムとの連携
- **機能**:
  - APIキーの生成・管理
  - APIドキュメントの提供
  - レート制限の設定
  - API利用状況の監視
- **実装場所**: 新規アプリ `api` または `rest_framework` を使用

#### 10. レポート生成機能
- **概要**: カスタムレポートの生成
- **機能**:
  - 基本レポート（PDF/Excel）
  - 高度なレポート（カスタムテンプレート）
  - レポートのスケジュール配信
  - レポートの共有機能
- **URL例**: `/firm/<firm_id>/reports/`

#### 11. マーケティング支援機能
- **概要**: プランに含まれるマーケティング支援機能
- **機能**:
  - セミナー共催の管理
  - オフ会実施支援の管理
  - メルマガ配信支援
  - マーケティング資料の提供
- **URL例**: `/firm/<firm_id>/marketing/`

#### 12. 優先サポート機能
- **概要**: Enterpriseプラン向けの優先サポート
- **機能**:
  - 優先サポートチケットシステム
  - チャットサポート
  - 専任サポート担当者の割り当て
- **実装場所**: 新規アプリ `support` または既存システムと統合

#### 13. データエクスポート機能
- **概要**: Firmのデータを一括エクスポート
- **機能**:
  - Companyデータのエクスポート
  - 利用状況データのエクスポート
  - 請求履歴のエクスポート
  - 全データのバックアップ
- **URL例**: `/firm/<firm_id>/export/`

#### 14. 分析・ダッシュボード機能
- **概要**: Firmのパフォーマンス分析
- **機能**:
  - 利用状況のトレンド分析
  - Company別のパフォーマンス比較
  - コスト分析
  - 予測分析
- **URL例**: `/firm/<firm_id>/analytics/`

---

## 📊 優先度別実装計画

### Phase 1: 基盤機能の拡張（1-2ヶ月）
1. ✅ プラン・サブスクリプション管理（実装済み）
2. ✅ 利用状況追跡（実装済み）
3. ✅ Firmメンバー管理機能（実装済み）
4. ✅ プランダウングレード時の処理（実装済み：グレース期間、警告、自動無効化）

### Phase 2: 可視化・レポート機能（2-3ヶ月）
5. ✅ 利用状況の詳細レポート（実装済み）
6. ✅ 請求履歴の表示（実装済み）
7. ✅ Company別の利用状況表示（実装済み）
8. ✅ プラン変更履歴（実装済み）

### Phase 3: 設定・通知機能（1-2ヶ月）
9. ✅ Firm設定管理（部分実装：Firm名、APIキー設定）
10. ✅ 通知機能（実装済み）

### Phase 4: 高度な機能（3-6ヶ月）
11. API連携機能
12. レポート生成機能
13. マーケティング支援機能
14. 優先サポート機能
15. データエクスポート機能
16. 分析・ダッシュボード機能

---

## 🔗 関連ドキュメント

- [プラン管理テストチェックリスト](../development/PLAN_MANAGEMENT_TEST_CHECKLIST.md)
- [Company数制限実装計画](./COMPANY_LIMIT_IMPLEMENTATION_PLAN.md)
- [Stripe設定詳細ガイド](../setup/STRIPE_SETUP_DETAILED.md)

---

## 📝 備考

- 各機能の実装前に、詳細な仕様書を作成することを推奨
- ユーザーフィードバックを収集し、優先度を再評価する
- セキュリティとパフォーマンスを考慮した実装を行う


