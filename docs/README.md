# SCORE AI ドキュメント

## ディレクトリ構成

```
docs/
├── setup/          # セットアップ関連
├── features/       # 機能仕様
├── development/    # 開発関連
└── archive/        # アーカイブ（実装完了済みの設計ドキュメント）
```

## セットアップ関連 (`setup/`)

### [Docker環境セットアップガイド](./setup/DOCKER_SETUP.md)
Docker環境でのローカル開発のセットアップ手順

### [Google API設定ガイド](./setup/GOOGLE_API_SETUP.md)
Google Gemini API、Vision API、Drive APIの設定方法

### [Google Drive連携セットアップガイド](./setup/GOOGLE_DRIVE_SETUP.md)
Google Driveとの連携設定とOAuth認証の手順

### [初期データ投入ガイド](./setup/INITIAL_DATA.md)
AI相談機能、フォルダ構造、Google Driveフォルダの初期化方法

## 機能仕様 (`features/`)

### [Firmユーザー向け機能一覧](./features/FIRM_USER_FEATURES.md)
Firmユーザー向けの実装済み機能と今後の実装予定機能

### [Company制限実装計画](./features/COMPANY_LIMIT_IMPLEMENTATION_PLAN.md)
プランダウングレード時のCompany制限管理の実装計画

### [OCR機能仕様](./features/OCR_FEATURE_SPEC.md)
決算書OCR読み込み機能の詳細仕様

### [プロンプトテンプレート使用例](./features/PROMPT_TEMPLATE_EXAMPLES.md)
AI相談機能のプロンプトテンプレート変数の使用例

## 開発関連 (`development/`)

### [改善実施状況](./development/IMPROVEMENTS.md)
コードレビューで指摘された改善項目の実施状況

### [テストガイド](./development/TESTING_GUIDE.md)
機能テストの手順とチェックリスト

### [クイックテストチェックリスト](./development/QUICK_TEST_CHECKLIST.md)
主要機能の簡易テストチェックリスト

### [コーディング規約](./development/CODING_STANDARDS.md)
プロジェクトのコーディング規約とベストプラクティス

### [ベストプラクティス分析](./development/BEST_PRACTICES_ANALYSIS.md)
Python/Djangoベストプラクティス準拠度の分析レポート

## アーカイブ (`archive/`)

実装完了済みの設計ドキュメントを保存しています。

- `MENU_REDESIGN_PROPOSAL.md`: メニュー再設計提案（実装完了）
- `DESIGN_MOCKUP.md`: デザインモックアップ（実装完了）
- `AI_CONSULTATION_IMPLEMENTATION_PLAN.md`: AI相談実装計画（実装完了）
- `IMPLEMENTATION_STATUS.md`: AI相談機能実装状況（実装完了）
- `IMPROVEMENT_STATUS.md`: 改善状況（古い情報）

## 主要ドキュメントへのリンク

### 新規開発者向け
1. [Docker環境セットアップガイド](./setup/DOCKER_SETUP.md)
2. [Google API設定ガイド](./setup/GOOGLE_API_SETUP.md)
3. [初期データ投入ガイド](./setup/INITIAL_DATA.md)
4. [コーディング規約](./development/CODING_STANDARDS.md)

### 機能開発者向け
1. [OCR機能仕様](./features/OCR_FEATURE_SPEC.md)
2. [プロンプトテンプレート使用例](./features/PROMPT_TEMPLATE_EXAMPLES.md)
3. [テストガイド](./development/TESTING_GUIDE.md)
4. [実装予定機能一覧](./FUTURE_FEATURES.md)

### コードレビュー・改善向け
1. [改善実施状況](./development/IMPROVEMENTS.md)
2. [ベストプラクティス分析](./development/BEST_PRACTICES_ANALYSIS.md)
3. [コード整合性レビューレポート](./CODE_REVIEW_REPORT.md)
4. [実装状況サマリー](./IMPLEMENTATION_STATUS.md)

