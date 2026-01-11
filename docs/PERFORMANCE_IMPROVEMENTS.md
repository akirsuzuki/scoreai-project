# パフォーマンス改善提案書

## 現状分析

本番環境のパフォーマンス問題を分析した結果、以下の問題点が特定されました：

### 1. N+1クエリ問題
- `FiscalSummary_Year`や`FiscalSummary_Month`の取得時に`select_related`が不足
- ループ内での関連オブジェクトアクセス

### 2. キャッシュの未活用
- キャッシュ設定はあるが、実際の使用箇所が少ない
- 頻繁にアクセスされるデータ（業界ベンチマーク、AI相談スクリプト等）がキャッシュされていない

### 3. データベースインデックスの不足
- 頻繁に検索されるフィールドにインデックスが設定されていない
- 複合インデックスの不足

### 4. 重い計算処理の最適化不足
- `Debt.balances_monthly`などのプロパティが毎回計算されている
- 計算結果がキャッシュされていない

### 5. クエリの最適化不足
- 不要なデータの取得
- ループ内でのクエリ実行

---

## 改善策（優先度順）

### 🔴 高優先度（即座に実施）

#### 1. データベースインデックスの追加

**対象モデルとインデックス:**

```python
# scoreai/models.py

class FiscalSummary_Year(models.Model):
    # ... 既存のフィールド ...
    
    class Meta:
        indexes = [
            models.Index(fields=['company', 'year', 'is_budget', 'is_draft']),
            models.Index(fields=['company', 'is_budget', 'is_draft', '-year']),
            models.Index(fields=['year', 'is_budget']),
        ]

class FiscalSummary_Month(models.Model):
    # ... 既存のフィールド ...
    
    class Meta:
        indexes = [
            models.Index(fields=['fiscal_summary_year', 'period', 'is_budget']),
            models.Index(fields=['fiscal_summary_year', 'period']),
        ]

class Debt(models.Model):
    # ... 既存のフィールド ...
    
    class Meta:
        indexes = [
            models.Index(fields=['company', 'is_nodisplay', 'is_rescheduled']),
            models.Index(fields=['company', 'financial_institution']),
            models.Index(fields=['company', 'start_date']),
            models.Index(fields=['company', 'debt_type']),
        ]

class AIConsultationHistory(models.Model):
    # ... 既存のフィールド ...
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'company', '-created_at']),
            models.Index(fields=['company', 'consultation_type', '-created_at']),
        ]
```

**効果**: クエリ速度が2-10倍向上する可能性

**実装手順**:
1. 上記のインデックスをモデルに追加
2. `python manage.py makemigrations`
3. `python manage.py migrate`
4. 本番環境でマイグレーション実行

---

#### 2. select_related/prefetch_relatedの追加

**問題箇所の修正:**

```python
# scoreai/views.py - FiscalSummary_MonthListView

# 修正前
fiscal_summary_year = FiscalSummary_Year.objects.filter(
    company=self.this_company,
    year=year,
    is_budget=False,
    is_draft=False
).order_by('-version').first()

# 修正後
fiscal_summary_year = FiscalSummary_Year.objects.filter(
    company=self.this_company,
    year=year,
    is_budget=False,
    is_draft=False
).select_related('company').order_by('-version').first()

# 修正前
monthly_data_list = FiscalSummary_Month.objects.filter(
    fiscal_summary_year=fiscal_summary_year,
    is_budget=False
).order_by('period')

# 修正後
monthly_data_list = FiscalSummary_Month.objects.filter(
    fiscal_summary_year=fiscal_summary_year,
    is_budget=False
).select_related('fiscal_summary_year', 'fiscal_summary_year__company').order_by('period')
```

**効果**: N+1クエリを削減し、ページ読み込み時間を30-50%短縮

---

#### 3. キャッシュの実装

**頻繁にアクセスされるデータのキャッシュ:**

```python
# scoreai/views/utils.py または新しい scoreai/utils/cache_utils.py

from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key

def get_cached_monthly_summaries(company, num_years=5):
    """月次サマリーをキャッシュから取得"""
    cache_key = f'monthly_summaries_{company.id}_{num_years}'
    cached_data = cache.get(cache_key)
    
    if cached_data is None:
        # キャッシュがない場合は計算
        cached_data = get_monthly_summaries(company, num_years)
        # 5分間キャッシュ
        cache.set(cache_key, cached_data, 300)
    
    return cached_data

def invalidate_monthly_summaries_cache(company_id):
    """月次サマリーのキャッシュを無効化"""
    cache_key_pattern = f'monthly_summaries_{company_id}_*'
    # キャッシュキーのパターン削除（実装が必要）
    cache.delete_many([f'monthly_summaries_{company_id}_{i}' for i in range(1, 10)])
```

**キャッシュ無効化のタイミング:**
- `FiscalSummary_Month`の作成・更新・削除時
- `FiscalSummary_Year`の作成・更新・削除時

```python
# scoreai/models.py - FiscalSummary_Month

def save(self, *args, **kwargs):
    super().save(*args, **kwargs)
    # キャッシュを無効化
    from django.core.cache import cache
    cache_key_pattern = f'monthly_summaries_{self.fiscal_summary_year.company.id}_*'
    cache.delete_many([f'monthly_summaries_{self.fiscal_summary_year.company.id}_{i}' for i in range(1, 10)])
```

**効果**: ダッシュボードの読み込み時間を50-70%短縮

---

### 🟡 中優先度（1-2週間以内に実施）

#### 4. Debt.balances_monthlyのキャッシュ

**問題**: 毎回12ヶ月分の残高を計算している

**解決策**: 計算結果をキャッシュ

```python
# scoreai/models.py - Debt

from django.core.cache import cache

@property
def balances_monthly(self):
    """今後12ヶ月間の各月の残高を計算（キャッシュ付き）"""
    cache_key = f'debt_balances_monthly_{self.id}'
    cached_balances = cache.get(cache_key)
    
    if cached_balances is not None:
        return cached_balances
    
    # 計算処理（既存のコード）
    # ... 計算ロジック ...
    
    # 結果をキャッシュ（1時間）
    cache.set(cache_key, balances, 3600)
    return balances
```

**キャッシュ無効化:**
- `Debt`の更新時
- 関連する`Debt`の更新時（同じ会社の他の借入が更新された場合）

---

#### 5. クエリの最適化（不要なデータの取得を削減）

**問題箇所の特定と修正:**

```python
# scoreai/views/index_views.py - IndexView

# 修正前: 全データを取得してからフィルタリング
monthly_data = FiscalSummary_Month.objects.filter(...).order_by('period')

# 修正後: 必要なデータのみ取得
monthly_data = FiscalSummary_Month.objects.filter(
    fiscal_summary_year__company=self.this_company,
    fiscal_summary_year__year=year,
    fiscal_summary_year__is_budget=False,
    is_budget=False
).select_related(
    'fiscal_summary_year',
    'fiscal_summary_year__company'
).only(
    'id', 'period', 'sales', 'gross_profit', 
    'operating_profit', 'ordinary_profit',
    'gross_profit_rate', 'operating_profit_rate', 'ordinary_profit_rate'
).order_by('period')
```

**効果**: メモリ使用量とクエリ時間を削減

---

#### 6. ページネーションの最適化

**大量データのページネーション:**

```python
# scoreai/views.py - リストビュー

class SomeListView(ListView):
    paginate_by = 25  # 適切なページサイズ
    paginate_orphans = 5
    
    def get_queryset(self):
        return Model.objects.filter(...).select_related(...).only(...)
```

---

### 🟢 低優先度（長期で実施）

#### 7. Redisキャッシュの本番環境での有効化

**現状**: 設定はあるが、環境変数`REDIS_URL`が設定されていない可能性

**実装手順**:
1. HerokuでRedisアドオンを追加: `heroku addons:create heroku-redis:mini`
2. 環境変数`REDIS_URL`が自動設定されることを確認
3. `django-redis`パッケージがインストールされていることを確認
4. キャッシュの動作確認

---

#### 8. 静的ファイルのCDN配信

**現状**: 静的ファイルがHerokuから配信されている

**改善策**:
- AWS S3 + CloudFront
- Cloudflare
- Herokuの静的ファイル配信最適化

---

#### 9. データベース接続プールの最適化

**現状**: `conn_max_age=600`が設定されている

**改善策**:
```python
# score/settings.py

DATABASES['default'] = dj_database_url.config(
    conn_max_age=600,
    ssl_require=True,
    # 接続プールの設定を追加
    OPTIONS={
        'connect_timeout': 10,
        'options': '-c statement_timeout=30000'
    }
)
```

---

#### 10. クエリプロファイリングツールの導入

**ツールの導入:**
- `django-debug-toolbar`（開発環境）
- `django-silk`（本番環境でのプロファイリング）
- `django-extensions`の`runserver_plus`（開発環境）

**使用方法:**
```python
# settings.py（開発環境のみ）

if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

---

## 実装優先順位

### フェーズ1（即座に実施 - 1週間以内）
1. ✅ データベースインデックスの追加
2. ✅ select_related/prefetch_relatedの追加
3. ✅ 基本的なキャッシュの実装

### フェーズ2（1-2週間以内）
4. ✅ Debt.balances_monthlyのキャッシュ
5. ✅ クエリの最適化（only/deferの使用）
6. ✅ ページネーションの最適化

### フェーズ3（長期）
7. ✅ Redisキャッシュの本番環境での有効化
8. ✅ 静的ファイルのCDN配信
9. ✅ データベース接続プールの最適化
10. ✅ クエリプロファイリングツールの導入

---

## 期待される効果

### フェーズ1完了後
- **ページ読み込み時間**: 30-50%短縮
- **データベースクエリ数**: 50-70%削減
- **サーバー負荷**: 40-60%削減

### フェーズ2完了後
- **ページ読み込み時間**: 50-70%短縮
- **データベースクエリ数**: 70-90%削減
- **サーバー負荷**: 60-80%削減

### フェーズ3完了後
- **ページ読み込み時間**: 70-90%短縮
- **スケーラビリティ**: 大幅に向上
- **ユーザー体験**: 著しく改善

---

## 監視と測定

### パフォーマンス指標の監視
1. **ページ読み込み時間**: 各ページの平均読み込み時間
2. **データベースクエリ数**: 1リクエストあたりのクエリ数
3. **データベースクエリ時間**: 1リクエストあたりのクエリ実行時間
4. **キャッシュヒット率**: キャッシュの有効性

### ツール
- Heroku Metrics Dashboard
- New Relic（オプション）
- Sentry（エラー追跡）

---

## 注意事項

1. **キャッシュ無効化**: データ更新時に必ずキャッシュを無効化すること
2. **インデックスの追加**: マイグレーション時に本番環境のダウンタイムを最小限に
3. **段階的な実装**: 一度にすべてを変更せず、段階的に実装・テストすること
4. **バックアップ**: 本番環境での変更前に必ずバックアップを取得すること

---

## 参考資料

- [Django Performance Best Practices](https://docs.djangoproject.com/en/stable/topics/performance/)
- [Django Caching Framework](https://docs.djangoproject.com/en/stable/topics/cache/)
- [Database Indexing Best Practices](https://www.postgresql.org/docs/current/indexes.html)

