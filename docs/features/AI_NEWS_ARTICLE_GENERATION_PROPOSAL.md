# AIニュース記事自動生成機能 素案

## 概要

ターゲット別（経営者向け、税理士・会計士向け、社労士向け、一般向け）に最適化されたニュース記事を自動生成する機能。

## 機能要件

### 1. ターゲット別記事生成

#### ターゲット分類
- **経営者向け**: 経営戦略、財務改善、資金調達、事業拡大など
- **税理士・会計士向け**: 税務改正、会計基準変更、実務のポイント、クライアント支援事例など
- **社労士向け**: 労働法改正、社会保険制度変更、人事労務の実務、助成金情報など
- **一般向け**: ビジネス全般、経済ニュース、業界動向など

### 2. 記事生成の流れ

```
1. ターゲット選択
   ↓
2. トピック/テーマ選択（または自由入力）
   ↓
3. 会社データの活用（オプション）
   - 財務データ
   - 業界情報
   - ローカルベンチマーク
   ↓
4. AI生成実行
   ↓
5. 記事プレビュー・編集
   ↓
6. 保存（下書き/公開）
```

## データモデル設計

### 1. NewsArticleTarget（記事ターゲット）

```python
class NewsArticleTarget(models.Model):
    """記事ターゲット（経営者、税理士・会計士、社労士、一般）"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    name = models.CharField(max_length=50, unique=True, verbose_name="ターゲット名")
    description = models.TextField(verbose_name="説明")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    order = models.IntegerField(default=0, verbose_name="表示順序")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = '記事ターゲット'
        verbose_name_plural = '記事ターゲット'
```

### 2. NewsArticleTopic（記事トピック）

```python
class NewsArticleTopic(models.Model):
    """記事トピック（税務改正、資金調達、人事労務など）"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    target = models.ForeignKey(NewsArticleTarget, on_delete=models.CASCADE, verbose_name="ターゲット")
    name = models.CharField(max_length=100, verbose_name="トピック名")
    description = models.TextField(verbose_name="説明")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    order = models.IntegerField(default=0, verbose_name="表示順序")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['target', 'order', 'name']
        verbose_name = '記事トピック'
        verbose_name_plural = '記事トピック'
```

### 3. NewsArticleScript（記事生成スクリプト）

```python
class NewsArticleScript(models.Model):
    """記事生成用のAIスクリプト（システム用）"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    target = models.ForeignKey(NewsArticleTarget, on_delete=models.CASCADE, verbose_name="ターゲット")
    topic = models.ForeignKey(NewsArticleTopic, on_delete=models.CASCADE, null=True, blank=True, verbose_name="トピック")
    name = models.CharField(max_length=100, verbose_name="スクリプト名")
    system_instruction = models.TextField(verbose_name="システム指示")
    prompt_template = models.TextField(verbose_name="プロンプトテンプレート")
    is_default = models.BooleanField(default=False, verbose_name="デフォルト")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="作成者")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '記事生成スクリプト（システム）'
        verbose_name_plural = '記事生成スクリプト（システム）'
        unique_together = [['target', 'topic', 'is_default']]
```

### 4. UserNewsArticleScript（ユーザー独自スクリプト）

```python
class UserNewsArticleScript(models.Model):
    """ユーザー独自の記事生成スクリプト"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ユーザー")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name="会社")
    target = models.ForeignKey(NewsArticleTarget, on_delete=models.CASCADE, verbose_name="ターゲット")
    topic = models.ForeignKey(NewsArticleTopic, on_delete=models.CASCADE, null=True, blank=True, verbose_name="トピック")
    name = models.CharField(max_length=100, verbose_name="スクリプト名")
    system_instruction = models.TextField(verbose_name="システム指示")
    prompt_template = models.TextField(verbose_name="プロンプトテンプレート")
    is_default = models.BooleanField(default=False, verbose_name="デフォルト")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '記事生成スクリプト（ユーザー）'
        verbose_name_plural = '記事生成スクリプト（ユーザー）'
        unique_together = [['user', 'company', 'target', 'topic', 'is_default']]
```

### 5. NewsArticleGeneration（記事生成履歴）

```python
class NewsArticleGeneration(models.Model):
    """記事生成履歴"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ユーザー")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, verbose_name="会社")
    target = models.ForeignKey(NewsArticleTarget, on_delete=models.CASCADE, verbose_name="ターゲット")
    topic = models.ForeignKey(NewsArticleTopic, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="トピック")
    custom_topic = models.CharField(max_length=200, blank=True, verbose_name="カスタムトピック")
    generated_title = models.CharField(max_length=255, verbose_name="生成されたタイトル")
    generated_content = models.TextField(verbose_name="生成された本文")
    script_used = models.ForeignKey(NewsArticleScript, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="使用スクリプト")
    user_script_used = models.ForeignKey(UserNewsArticleScript, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="使用ユーザースクリプト")
    data_snapshot = models.JSONField(default=dict, verbose_name="データスナップショット")
    blog = models.OneToOneField(Blog, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="保存されたブログ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    
    class Meta:
        verbose_name = '記事生成履歴'
        verbose_name_plural = '記事生成履歴'
        ordering = ['-created_at']
```

## UI/UX設計

### 1. 記事生成画面

```
┌─────────────────────────────────────────┐
│  AIニュース記事生成                      │
├─────────────────────────────────────────┤
│                                         │
│  ターゲット選択:                        │
│  ○ 経営者向け                           │
│  ○ 税理士・会計士向け                   │
│  ○ 社労士向け                           │
│  ○ 一般向け                             │
│                                         │
│  トピック選択:                          │
│  [ドロップダウン] 税務改正 / 資金調達...│
│  または [カスタムトピック入力]           │
│                                         │
│  会社データを活用:                      │
│  ☑ 財務データを参照                     │
│  ☑ 業界情報を参照                       │
│  ☑ ローカルベンチマークを参照           │
│                                         │
│  [記事を生成]                           │
│                                         │
└─────────────────────────────────────────┘
```

### 2. 記事プレビュー・編集画面

```
┌─────────────────────────────────────────┐
│  生成された記事                          │
├─────────────────────────────────────────┤
│                                         │
│  タイトル: [編集可能]                   │
│  本文: [編集可能（Markdown対応）]       │
│                                         │
│  [プレビュー] [保存] [公開]             │
│                                         │
└─────────────────────────────────────────┘
```

## プロンプト設計例

### 経営者向け記事の例

```
システム指示:
あなたは経営コンサルタントです。中小企業の経営者向けに、実践的で分かりやすい記事を作成してください。

プロンプトテンプレート:
【ターゲット】経営者向け
【トピック】{topic}
【会社情報】（オプション）
- 業界: {industry_classification}
- 企業規模: {company_size}
- 財務状況: {fiscal_summary}

【記事要件】
- 文字数: 1,500-2,000文字
- 構成: 導入→本論→まとめ
- トーン: 実践的、具体的、前向き
- 読者の行動を促す内容を含める

上記の要件に基づいて、{topic}に関する記事を作成してください。
```

### 税理士・会計士向け記事の例

```
システム指示:
あなたは税理士・会計士向けの専門情報を提供するライターです。実務に役立つ情報を、専門的でありながら分かりやすく伝えてください。

プロンプトテンプレート:
【ターゲット】税理士・会計士向け
【トピック】{topic}
【最新情報】（オプション）
- 税務改正情報
- 会計基準変更
- 実務のポイント

【記事要件】
- 文字数: 2,000-3,000文字
- 構成: 概要→詳細解説→実務への影響→まとめ
- トーン: 専門的、正確、実務的
- クライアントへの説明に使える内容

上記の要件に基づいて、{topic}に関する記事を作成してください。
```

## 実装の優先順位

### Phase 1: 基本機能
1. データモデル作成
2. ターゲット・トピック管理（Admin）
3. 基本的な記事生成機能
4. 記事プレビュー・編集機能
5. Blogモデルへの保存機能

### Phase 2: 高度な機能
1. 会社データの活用（財務データ、業界情報）
2. ユーザー独自スクリプト機能
3. 記事テンプレート機能
4. バッチ生成機能（定期生成）

### Phase 3: 拡張機能
1. 記事のSEO最適化
2. 画像生成機能（記事用のアイキャッチ画像）
3. SNS投稿連携
4. 記事のパフォーマンス分析

## 技術的な実装

### 1. ビュー構成

- `NewsArticleGenerateView`: 記事生成画面
- `NewsArticlePreviewView`: 記事プレビュー・編集画面
- `NewsArticleSaveView`: 記事保存API
- `NewsArticleScriptManageView`: スクリプト管理画面

### 2. ユーティリティ

- `news_article_data.py`: 会社データ収集
- `news_article_prompt.py`: プロンプト構築
- `news_article_generator.py`: AI生成処理

### 3. 既存機能との連携

- `Blog`モデルへの保存
- `AIConsultationType`と同様のスクリプト管理
- `SelectedCompanyMixin`の活用
- プラン制限の適用（Professional/Enterpriseのみ）

## プラン制限

- **Starter**: 月5記事まで
- **Professional**: 月20記事まで
- **Enterprise**: 無制限

## セキュリティ・品質管理

1. **コンテンツフィルタリング**: 不適切な内容の検出
2. **事実確認**: 重要な情報の正確性チェック
3. **著作権**: 生成された記事の権利関係
4. **下書き管理**: 公開前の確認機能

## 今後の拡張可能性

1. **多言語対応**: 英語記事の生成
2. **音声記事**: 音声読み上げ機能
3. **動画記事**: 動画コンテンツの生成
4. **パーソナライズ**: 読者の興味に基づく記事推薦

