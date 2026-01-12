# 本番環境パフォーマンス問題の分析

## 現状の問題点

### 🔴 高優先度（即座に影響がある）

#### 1. N+1クエリ問題（ループ内でのクエリ実行）

**問題箇所1: `FiscalSummary_MonthListView.get_context_data()`**
```python
# scoreai/views.py:1426-1437
for year in years_to_compare:
    fiscal_summary_year = FiscalSummary_Year.objects.filter(
        company=self.this_company,
        year=year,
        is_budget=False,
        is_draft=False
    ).order_by('-version').first()  # ❌ select_relatedが不足
    
    if fiscal_summary_year:
        monthly_data_list = FiscalSummary_Month.objects.filter(
            fiscal_summary_year=fiscal_summary_year,
            is_budget=False
        ).order_by('period')  # ❌ select_relatedが不足
```

**影響**: 年度ごとに2回のクエリが実行され、3年度比較で6回のクエリが発生

**問題箇所2: `IndexView.get_context_data()`**
```python
# scoreai/views/index_views.py:85-92
for year in latest_years_with_draft:
    monthly_data = FiscalSummary_Month.objects.filter(
        fiscal_summary_year__company=self.this_company,
        fiscal_summary_year__year=year,
        fiscal_summary_year__is_budget=False,
        is_budget=False
    ).select_related('fiscal_summary_year', 'fiscal_summary_year__company').order_by('period')
    # ✅ select_relatedは使用されているが、ループ内でクエリ実行
```

**影響**: 年度数分のクエリが実行される（最大3回）

#### 2. 重い計算処理の毎回実行（キャッシュなし）

**問題箇所: `Debt.balances_monthly`プロパティ**
```python
# scoreai/models.py:969-1034
@property
def balances_monthly(self):
    """今後12ヶ月間の各月の残高を計算"""
    # ❌ 毎回計算されている（キャッシュなし）
    # ❌ ループ内でbalance_after_months()を12回呼び出し
```

**影響**: 
- 借入が10件ある場合、120回の計算が実行される
- ダッシュボード表示時に全借入の残高計算が毎回実行される

**問題箇所: `Debt.balance_after_months()`**
```python
# scoreai/models.py:balance_after_months()
# 複雑な計算処理が毎回実行される
# キャッシュされていない
```

#### 3. データベースインデックスの不足

**確認が必要なモデル:**
- `FiscalSummary_Year`: `company`, `year`, `is_budget`, `is_draft`の複合インデックス
- `FiscalSummary_Month`: `fiscal_summary_year`, `period`, `is_budget`の複合インデックス
- `Debt`: `company`, `is_nodisplay`, `is_rescheduled`の複合インデックス
- `UserCompany`: `user`, `company`, `active`の複合インデックス

**影響**: クエリ速度が遅い、特に大量データがある場合

#### 4. キャッシュの未活用

**現状**: 
- `LocMemCache`が設定されているが、実際の使用箇所がほとんどない
- 本番環境で`REDIS_URL`が設定されていない可能性

**影響**: 
- 同じデータを何度もデータベースから取得
- 計算結果が再利用されない

### 🟡 中優先度（パフォーマンスに影響がある）

#### 5. 不要なデータの取得

**問題箇所: `IndexView.get_context_data()`**
```python
# scoreai/views/index_views.py:87-92
monthly_data = FiscalSummary_Month.objects.filter(...)
# ❌ 全フィールドを取得している（only/deferを使用していない）
```

**影響**: メモリ使用量が増加、ネットワーク転送量が増加

#### 6. ループ内での辞書変換処理

**問題箇所: `IndexView.get_context_data()`**
```python
# scoreai/views/index_views.py:96-107
for month in monthly_data:
    monthly_data_dict[month.period] = {
        'id': month.id,
        'sales': float(month.sales) if month.sales is not None else 0.0,
        # ... 各フィールドを個別に変換
    }
```

**影響**: ループ内での型変換処理が重い

#### 7. 静的ファイルの配信方法

**現状**: 
- `WhiteNoise`を使用しているが、CDNを使用していない
- 静的ファイルがHerokuから配信されている

**影響**: 
- 静的ファイルの読み込みが遅い
- サーバーリソースを消費

### 🟢 低優先度（長期的な改善）

#### 8. データベース接続プールの最適化

**現状**: `conn_max_age=600`が設定されているが、接続プールの詳細設定がない

#### 9. クエリプロファイリングツールの未導入

**現状**: 本番環境でのクエリパフォーマンス監視ツールがない

---

## 具体的な改善策

### 即座に実施すべき（1週間以内）

1. **`FiscalSummary_MonthListView`の修正**
   ```python
   # select_relatedを追加
   fiscal_summary_year = FiscalSummary_Year.objects.filter(
       company=self.this_company,
       year=year,
       is_budget=False,
       is_draft=False
   ).select_related('company').order_by('-version').first()
   
   monthly_data_list = FiscalSummary_Month.objects.filter(
       fiscal_summary_year=fiscal_summary_year,
       is_budget=False
   ).select_related('fiscal_summary_year', 'fiscal_summary_year__company').order_by('period')
   ```

2. **`Debt.balances_monthly`のキャッシュ実装**
   ```python
   @property
   def balances_monthly(self):
       from django.core.cache import cache
       cache_key = f'debt_balances_monthly_{self.id}'
       cached = cache.get(cache_key)
       if cached is not None:
           return cached
       # 計算処理
       balances = [...]  # 既存の計算ロジック
       cache.set(cache_key, balances, 3600)  # 1時間キャッシュ
       return balances
   ```

3. **データベースインデックスの追加**
   - マイグレーションを作成してインデックスを追加

### 1-2週間以内に実施

4. **キャッシュの実装**
   - 月次サマリーデータのキャッシュ
   - 借入リストのキャッシュ

5. **クエリの最適化（only/deferの使用）**
   - 必要なフィールドのみ取得

6. **Redisキャッシュの本番環境での有効化**
   - HerokuでRedisアドオンを追加
   - 環境変数の設定確認

---

## 期待される効果

### 即座の改善（1週間以内）
- **ページ読み込み時間**: 30-40%短縮
- **データベースクエリ数**: 40-50%削減
- **サーバー負荷**: 30-40%削減

### 中期改善（1-2週間以内）
- **ページ読み込み時間**: 50-60%短縮
- **データベースクエリ数**: 60-70%削減
- **サーバー負荷**: 50-60%削減

---

## 監視すべき指標

1. **ページ読み込み時間**: 各ページの平均読み込み時間
2. **データベースクエリ数**: 1リクエストあたりのクエリ数
3. **データベースクエリ時間**: 1リクエストあたりのクエリ実行時間
4. **メモリ使用量**: サーバーのメモリ使用率
5. **CPU使用率**: サーバーのCPU使用率

---

## 参考資料

- [Django Performance Best Practices](https://docs.djangoproject.com/en/stable/topics/performance/)
- [Django Caching Framework](https://docs.djangoproject.com/en/stable/topics/cache/)
- [Database Indexing Best Practices](https://www.postgresql.org/docs/current/indexes.html)
