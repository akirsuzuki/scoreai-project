"""
年次財務諸表のAI診断レポート生成ユーティリティ
"""
import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from django.db.models import Q

from ..models import (
    FiscalSummary_Year,
    IndustryBenchmark,
    IndustryIndicator,
    Company,
)

logger = logging.getLogger(__name__)


def collect_fiscal_data_for_diagnosis(
    company: Company,
    target_year: int
) -> Dict[str, Any]:
    """
    診断に必要な財務データを収集
    
    Args:
        company: 会社
        target_year: 対象年度
        
    Returns:
        診断に必要なデータの辞書
    """
    # 対象年度、前期、前々期のデータを取得
    fiscal_data = {}
    
    for year_offset in [0, -1, -2]:
        year = target_year + year_offset
        fiscal = FiscalSummary_Year.objects.filter(
            company=company,
            year=year,
            is_draft=False,
            is_budget=False
        ).first()
        
        if fiscal:
            fiscal_data[f'year_{year}'] = {
                'year': fiscal.year,
                # PL情報
                'sales': fiscal.sales,
                'gross_profit': fiscal.gross_profit,
                'operating_profit': fiscal.operating_profit,
                'ordinary_profit': fiscal.ordinary_profit,
                'net_profit': fiscal.net_profit,
                # BS情報
                'cash_and_deposits': fiscal.cash_and_deposits,
                'accounts_receivable': fiscal.accounts_receivable,
                'inventory': fiscal.inventory,
                'total_current_assets': fiscal.total_current_assets,
                'total_tangible_fixed_assets': fiscal.total_tangible_fixed_assets,
                'total_intangible_assets': fiscal.total_intangible_assets,
                'total_fixed_assets': fiscal.total_fixed_assets,
                'total_assets': fiscal.total_assets,
                'accounts_payable': fiscal.accounts_payable,
                'short_term_borrowings': fiscal.short_term_loans_payable,
                'total_current_liabilities': fiscal.total_current_liabilities,
                'long_term_borrowings': fiscal.long_term_loans_payable,
                'total_long_term_liabilities': fiscal.total_long_term_liabilities,
                'total_liabilities': fiscal.total_liabilities,
                'capital_stock': fiscal.capital_stock,
                'capital_surplus': fiscal.capital_surplus,
                'retained_earnings': fiscal.retained_earnings,
                'total_net_assets': fiscal.total_net_assets,
                # 指標
                'sales_growth_rate': float(fiscal.sales_growth_rate) if fiscal.sales_growth_rate else None,
                'operating_profit_margin': float(fiscal.operating_profit_margin) if fiscal.operating_profit_margin else None,
                'labor_productivity': float(fiscal.labor_productivity) if fiscal.labor_productivity else None,
                'EBITDA_interest_bearing_debt_ratio': float(fiscal.EBITDA_interest_bearing_debt_ratio) if fiscal.EBITDA_interest_bearing_debt_ratio else None,
                'operating_working_capital_turnover_period': float(fiscal.operating_working_capital_turnover_period) if fiscal.operating_working_capital_turnover_period else None,
                'equity_ratio': float(fiscal.equity_ratio) if fiscal.equity_ratio else None,
                # スコア
                'score_sales_growth_rate': fiscal.score_sales_growth_rate,
                'score_operating_profit_margin': fiscal.score_operating_profit_margin,
                'score_labor_productivity': fiscal.score_labor_productivity,
                'score_EBITDA_interest_bearing_debt_ratio': fiscal.score_EBITDA_interest_bearing_debt_ratio,
                'score_operating_working_capital_turnover_period': fiscal.score_operating_working_capital_turnover_period,
                'score_equity_ratio': fiscal.score_equity_ratio,
                # 税務情報
                'income_taxes': fiscal.income_taxes,
                # 決算留意事項
                'financial_statement_notes': fiscal.financial_statement_notes,
                # 貸借対照表の詳細
                'total_current_assets': fiscal.total_current_assets,
                'total_fixed_assets': fiscal.total_fixed_assets,
                'total_current_liabilities': fiscal.total_current_liabilities,
                'total_long_term_liabilities': fiscal.total_long_term_liabilities,
            }
    
    # ベンチマークデータを取得
    benchmark_data = {}
    if company.industry_classification and company.industry_subclassification:
        indicators = IndustryIndicator.objects.all()
        for indicator in indicators:
            benchmark = IndustryBenchmark.objects.filter(
                year=target_year,
                industry_classification=company.industry_classification,
                industry_subclassification=company.industry_subclassification,
                company_size=company.company_size,
                indicator=indicator
            ).first()
            
            # 見つからない場合は前年を試す
            if not benchmark and target_year > 2000:
                benchmark = IndustryBenchmark.objects.filter(
                    year=target_year - 1,
                    industry_classification=company.industry_classification,
                    industry_subclassification=company.industry_subclassification,
                    company_size=company.company_size,
                    indicator=indicator
                ).first()
            
            if benchmark:
                benchmark_data[indicator.name] = {
                    'median': float(benchmark.median),
                    'standard_deviation': float(benchmark.standard_deviation),
                    'range_i': float(benchmark.range_i),
                    'range_ii': float(benchmark.range_ii),
                    'range_iii': float(benchmark.range_iii),
                    'range_iv': float(benchmark.range_iv),
                }
    
    return {
        'company': {
            'name': company.name,
            'industry_classification': company.industry_classification.name if company.industry_classification else None,
            'industry_subclassification': company.industry_subclassification.name if company.industry_subclassification else None,
            'company_size': company.get_company_size_display(),
            'fiscal_month': company.fiscal_month,
        },
        'fiscal_data': fiscal_data,
        'benchmark_data': benchmark_data,
        'target_year': target_year,
    }


def build_ai_diagnosis_prompt(
    fiscal_data: Dict[str, Any],
    missing_info: Optional[List[str]] = None
) -> str:
    """
    AI診断用のプロンプトを構築
    
    Args:
        fiscal_data: 収集した財務データ
        missing_info: 不足している情報のリスト
        
    Returns:
        プロンプト文字列
    """
    prompt_parts = []
    
    # 基本情報
    prompt_parts.append("## 会社情報")
    prompt_parts.append(f"会社名: {fiscal_data['company']['name']}")
    prompt_parts.append(f"業界分類: {fiscal_data['company']['industry_classification'] or '未設定'}")
    prompt_parts.append(f"業界小分類: {fiscal_data['company']['industry_subclassification'] or '未設定'}")
    prompt_parts.append(f"企業規模: {fiscal_data['company']['company_size'] or '未設定'}")
    prompt_parts.append(f"決算月: {fiscal_data['company']['fiscal_month']}月")
    prompt_parts.append("")
    prompt_parts.append("**重要**: 上記の会社情報（業界分類、業界小分類、企業規模）を基に、業界特性を考慮した分析を行ってください。")
    prompt_parts.append("同じ業界・規模の企業と比較し、業界平均との差異を明確に示してください。")
    prompt_parts.append("")
    
    # 財務データ（3期分）
    prompt_parts.append("## 財務データ（3期分）")
    for key, data in fiscal_data['fiscal_data'].items():
        year = data['year']
        prompt_parts.append(f"\n### {year}年度")
        
        # 損益計算書情報
        prompt_parts.append("\n#### 損益計算書")
        prompt_parts.append(f"- 売上高: {data['sales']:,}千円")
        prompt_parts.append(f"- 売上総利益: {data['gross_profit']:,}千円")
        prompt_parts.append(f"- 営業利益: {data['operating_profit']:,}千円")
        prompt_parts.append(f"- 経常利益: {data['ordinary_profit']:,}千円")
        prompt_parts.append(f"- 当期純利益: {data['net_profit']:,}千円")
        
        # 貸借対照表情報
        prompt_parts.append("\n#### 貸借対照表")
        prompt_parts.append("【資産の部】")
        prompt_parts.append(f"- 現金及び預金: {data['cash_and_deposits']:,}千円")
        prompt_parts.append(f"- 売掛金: {data['accounts_receivable']:,}千円")
        prompt_parts.append(f"- 棚卸資産: {data['inventory']:,}千円")
        prompt_parts.append(f"- 流動資産合計: {data['total_current_assets']:,}千円")
        prompt_parts.append(f"- 有形固定資産合計: {data['total_tangible_fixed_assets']:,}千円")
        prompt_parts.append(f"- 無形固定資産合計: {data['total_intangible_assets']:,}千円")
        prompt_parts.append(f"- 固定資産合計: {data['total_fixed_assets']:,}千円")
        prompt_parts.append(f"- 資産合計: {data['total_assets']:,}千円")
        prompt_parts.append("【負債の部】")
        prompt_parts.append(f"- 買掛金: {data['accounts_payable']:,}千円")
        prompt_parts.append(f"- 短期借入金: {data['short_term_borrowings']:,}千円")
        prompt_parts.append(f"- 流動負債合計: {data['total_current_liabilities']:,}千円")
        prompt_parts.append(f"- 長期借入金: {data['long_term_borrowings']:,}千円")
        prompt_parts.append(f"- 固定負債合計: {data['total_long_term_liabilities']:,}千円")
        prompt_parts.append(f"- 負債合計: {data['total_liabilities']:,}千円")
        prompt_parts.append("【純資産の部】")
        prompt_parts.append(f"- 資本金: {data['capital_stock']:,}千円")
        prompt_parts.append(f"- 資本剰余金: {data['capital_surplus']:,}千円")
        prompt_parts.append(f"- 利益剰余金: {data['retained_earnings']:,}千円")
        prompt_parts.append(f"- 純資産合計: {data['total_net_assets']:,}千円")
        
        # 税務申告情報
        prompt_parts.append("\n#### 税務申告情報")
        prompt_parts.append(f"- 法人税等: {data['income_taxes']:,}千円" if data.get('income_taxes') else "- 法人税等: データなし")
        
        # 決算留意事項
        if data.get('financial_statement_notes'):
            prompt_parts.append("\n#### 決算留意事項")
            prompt_parts.append(data['financial_statement_notes'])
        
        # 主要指標
        prompt_parts.append("\n#### 主要指標")
        prompt_parts.append(f"- 売上高成長率: {data['sales_growth_rate']:.2f}%" if data['sales_growth_rate'] else "- 売上高成長率: データなし")
        prompt_parts.append(f"- 営業利益率: {data['operating_profit_margin']:.2f}%" if data['operating_profit_margin'] else "- 営業利益率: データなし")
        prompt_parts.append(f"- 労働生産性: {data['labor_productivity']:.2f}千円/人" if data['labor_productivity'] else "- 労働生産性: データなし")
        prompt_parts.append(f"- 自己資本比率: {data['equity_ratio']:.2f}%" if data['equity_ratio'] else "- 自己資本比率: データなし")
        prompt_parts.append(f"- 運転資本回転期間: {data['operating_working_capital_turnover_period']:.2f}日" if data['operating_working_capital_turnover_period'] else "- 運転資本回転期間: データなし")
        prompt_parts.append(f"- EBITDA有利子負債倍率: {data['EBITDA_interest_bearing_debt_ratio']:.2f}" if data['EBITDA_interest_bearing_debt_ratio'] else "- EBITDA有利子負債倍率: データなし")
        
        # スコア
        prompt_parts.append("\n#### スコア（業界内での位置）")
        prompt_parts.append(f"- 売上高成長率スコア: {data['score_sales_growth_rate']}/5" if data['score_sales_growth_rate'] else "- 売上高成長率スコア: データなし")
        prompt_parts.append(f"- 営業利益率スコア: {data['score_operating_profit_margin']}/5" if data['score_operating_profit_margin'] else "- 営業利益率スコア: データなし")
        prompt_parts.append(f"- 労働生産性スコア: {data['score_labor_productivity']}/5" if data['score_labor_productivity'] else "- 労働生産性スコア: データなし")
        prompt_parts.append(f"- 自己資本比率スコア: {data['score_equity_ratio']}/5" if data['score_equity_ratio'] else "- 自己資本比率スコア: データなし")
    
    # ベンチマークデータ
    if fiscal_data['benchmark_data']:
        prompt_parts.append("\n## ローカルベンチマークデータ")
        for indicator_name, benchmark in fiscal_data['benchmark_data'].items():
            prompt_parts.append(f"\n### {indicator_name}")
            prompt_parts.append(f"- 中央値: {benchmark['median']:.2f}")
            prompt_parts.append(f"- 標準偏差: {benchmark['standard_deviation']:.2f}")
            prompt_parts.append(f"- 範囲I（最上位）: {benchmark['range_i']:.2f}")
            prompt_parts.append(f"- 範囲II: {benchmark['range_ii']:.2f}")
            prompt_parts.append(f"- 範囲III: {benchmark['range_iii']:.2f}")
            prompt_parts.append(f"- 範囲IV（最下位）: {benchmark['range_iv']:.2f}")
    
    # 不足情報
    if missing_info:
        prompt_parts.append("\n## 不足している情報")
        for info in missing_info:
            prompt_parts.append(f"- {info}")
    
    # 分析指示
    prompt_parts.append("\n## 分析指示")
    prompt_parts.append("""
上記の財務データとローカルベンチマークデータを基に、経済産業省のローカルベンチマーク分析手法（https://www.meti.go.jp/policy/economy/keiei_innovation/sangyokinyu/locaben/）を参考に、以下の観点から詳細な分析レポートを作成してください。

### 1ページ目: 総合評価と主要指標の分析

**財務状況の総合評価**
- 3期分のデータから見る財務状況の推移を時系列で分析
- 主要指標（売上高成長率、営業利益率、労働生産性、自己資本比率など）の変化とその要因分析
- 各指標のスコアから見る総合的な財務健全性の評価
- 収益性、効率性、安全性、成長性の4つの観点からの評価

**主要指標の詳細分析**
- 売上高成長率: 前期・前々期との比較、成長トレンドの分析
- 営業利益率: 収益性の変化、業界平均との比較
- 労働生産性: 従業員1人当たりの付加価値の推移
- 自己資本比率: 財務安全性の評価
- 運転資本回転期間: 資金効率の評価
- EBITDA有利子負債倍率: 返済能力の評価

### 2ページ目: ローカルベンチマークとの詳細比較分析

**業界内での位置づけ**
- 各指標が業界の中央値（median）と比較してどの位置にあるか
- 標準偏差（standard_deviation）を考慮した業界内での相対的位置
- 範囲I（最上位）、範囲II、範囲III、範囲IV（最下位）のどの範囲に該当するか

**強み・弱みの分析**
- 業界平均を上回っている指標（強み）の特定とその要因分析
- 業界平均を下回っている指標（弱み）の特定と改善の必要性
- 業界内での競争優位性の評価

**ベンチマーク比較の詳細**
- 売上高成長率: 業界中央値との比較、成長性の評価
- 営業利益率: 業界中央値との比較、収益性の評価
- 労働生産性: 業界中央値との比較、効率性の評価
- 自己資本比率: 業界中央値との比較、安全性の評価
- 運転資本回転期間: 業界中央値との比較、資金効率の評価
- EBITDA有利子負債倍率: 業界中央値との比較、返済能力の評価

**業界特性を考慮した分析**
- 業界分類（{fiscal_data['company']['industry_classification'] or '未設定'}）・業界小分類（{fiscal_data['company']['industry_subclassification'] or '未設定'}）・企業規模（{fiscal_data['company']['company_size'] or '未設定'}）を考慮した適切な評価
- 同規模企業との比較における位置づけ
- 業界特有のビジネスモデルや財務構造を考慮した分析
- 業界トレンドや市場環境を踏まえた評価

### 3ページ目: 改善提案と今後の展望

**改善提案**
- 弱みの指標に対する具体的な改善施策の提案
- 改善の優先順位の明確化（緊急度・重要度のマトリクス）
- 各改善施策の期待効果の定量的評価
- 実現可能性を考慮した現実的な提案

**今後の展望**
- 現在の財務状況から見る今後の展望（楽観シナリオ・悲観シナリオ）
- リスク要因の特定と対策
- 業界トレンドを考慮した中長期的な戦略提案

**アクションプラン**
- 短期（1年以内）の改善アクション
- 中期（3年以内）の改善アクション
- 長期（5年以内）の改善アクション

レポートは上記の3ページ構成で、各ページは見出しと箇条書きを適切に使用して読みやすく構成してください。
数値は必ず根拠として示し、主観的な判断ではなく客観的な分析に基づいて記述してください。

データが不足している場合は、その点を明記し、必要な情報を質問形式で提示してください。
""")
    
    return "\n".join(prompt_parts)

