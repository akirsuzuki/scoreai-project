# プロンプトテンプレート変数使用例

## 利用可能な変数

| 変数名 | 説明 | データ型 |
|--------|------|----------|
| `{user_message}` | ユーザーの質問 | 文字列 |
| `{company_name}` | 会社名 | 文字列 |
| `{industry}` | 業種 | 文字列 |
| `{size}` | 規模（小規模、中規模、大規模） | 文字列 |
| `{fiscal_summary}` | 決算書データ | JSON文字列 |
| `{debt_info}` | 借入情報 | JSON文字列 |
| `{monthly_data}` | 月次推移データ | JSON文字列 |

## 使用例

### 例1: 基本的な財務相談テンプレート

```
【会社情報】
会社名: {company_name}
業種: {industry}
規模: {size}

【決算書データ】
{fiscal_summary}

【借入情報】
{debt_info}

【月次推移データ】
{monthly_data}

【ユーザーの質問】
{user_message}

上記の情報を基に、以下の点を考慮して回答してください：
1. 財務状況の分析
2. 具体的な改善提案
3. 優先順位の高いアクション
4. リスク要因の指摘

回答は日本語で、専門的すぎない言葉で説明してください。
```

### 例2: シンプルなテンプレート（財務データのみ）

```
{company_name}の財務データを分析してください。

【決算書データ】
{fiscal_summary}

【質問】
{user_message}

上記のデータを基に、具体的なアドバイスを提供してください。
```

### 例3: 補助金・助成金相談用テンプレート

```
【会社情報】
会社名: {company_name}
業種: {industry}
規模: {size}

【財務データ】
{fiscal_summary}

【ユーザーの質問】
{user_message}

上記の情報を基に、以下の点を考慮して回答してください：
1. 該当する可能性のある補助金・助成金制度
2. 申請のタイミングと期限
3. 必要な書類と手続き
4. 申請のポイントと注意事項

回答は日本語で、専門的すぎない言葉で説明してください。
```

### 例4: 税務相談用テンプレート

```
【会社情報】
会社名: {company_name}
業種: {industry}
規模: {size}

【決算書データ】
{fiscal_summary}

【ユーザーの質問】
{user_message}

上記の情報を基に、以下の点を考慮して回答してください：
1. 税務上の注意点
2. 節税の可能性
3. 必要な手続き
4. 期限とタイミング

回答は日本語で、専門的すぎない言葉で説明してください。
```

### 例5: 借入情報に焦点を当てたテンプレート

```
【会社情報】
会社名: {company_name}
業種: {industry}

【借入情報】
{debt_info}

【決算書データ】
{fiscal_summary}

【ユーザーの質問】
{user_message}

借入情報と財務データを分析し、以下の点について回答してください：
1. 借入金の適正性
2. 返済計画の見直しポイント
3. 資金繰りの改善提案

回答は日本語で、専門的すぎない言葉で説明してください。
```

### 例6: 月次推移に焦点を当てたテンプレート

```
【会社情報】
会社名: {company_name}
業種: {industry}

【月次推移データ（直近12ヶ月）】
{monthly_data}

【決算書データ】
{fiscal_summary}

【ユーザーの質問】
{user_message}

月次推移データを分析し、以下の点について回答してください：
1. 売上・利益のトレンド分析
2. 季節性の有無
3. 改善のポイント

回答は日本語で、専門的すぎない言葉で説明してください。
```

## 変数の実際の値の例

### {fiscal_summary} の例
```json
{
  "year": 2024,
  "sales": 100000,
  "gross_profit": 30000,
  "operating_profit": 10000,
  "ordinary_profit": 8000,
  "net_profit": 5000,
  "total_assets": 50000,
  "total_liabilities": 30000,
  "total_net_assets": 20000,
  "capital_stock": 10000,
  "retained_earnings": 10000
}
```

### {debt_info} の例
```json
[
  {
    "financial_institution": "○○銀行",
    "principal": 10000,
    "interest_rate": 1.5,
    "monthly_repayment": 100,
    "remaining_months": 120,
    "is_securedby_management": true,
    "is_collateraled": false
  },
  {
    "financial_institution": "△△信用金庫",
    "principal": 5000,
    "interest_rate": 2.0,
    "monthly_repayment": 50,
    "remaining_months": 100,
    "is_securedby_management": false,
    "is_collateraled": true
  }
]
```

### {monthly_data} の例
```json
[
  {
    "year": 2024,
    "period": 1,
    "sales": 8000,
    "gross_profit": 2400,
    "operating_profit": 800,
    "ordinary_profit": 700
  },
  {
    "year": 2024,
    "period": 2,
    "sales": 8500,
    "gross_profit": 2550,
    "operating_profit": 850,
    "ordinary_profit": 750
  }
]
```

## テンプレート作成のヒント

1. **変数は必ず中括弧で囲む**: `{user_message}` のように `{}` で囲む必要があります
2. **変数名は正確に**: 大文字小文字も区別されます
3. **JSONデータの扱い**: `{fiscal_summary}`, `{debt_info}`, `{monthly_data}` は既にJSON形式の文字列として展開されます
4. **必須変数**: `{user_message}` は常に利用可能です
5. **条件付き変数**: `{fiscal_summary}`, `{debt_info}`, `{monthly_data}` はデータが存在する場合のみ利用可能です

## よくある質問

### Q: 変数が空の場合はどうなりますか？
A: 変数が存在しない場合、空文字列として展開されます。テンプレート内で条件分岐はできませんが、AIが適切に判断してくれるはずです。

### Q: JSONデータを整形したい場合は？
A: JSONデータは既に整形された形式（インデント付き）で展開されます。AIが読みやすい形式になっています。

### Q: 変数の順序は重要ですか？
A: 順序は自由です。読みやすさを重視して配置してください。

