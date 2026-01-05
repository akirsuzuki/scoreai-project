"""
TechnicalTermの初期データを投入するコマンド

使用方法:
    python manage.py init_technical_terms
"""

from django.core.management.base import BaseCommand
from scoreai.models import TechnicalTerm


class Command(BaseCommand):
    help = 'TechnicalTermの初期データを投入します'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('TechnicalTermの初期データ投入を開始します...'))

        # 既存のデータを削除（オプション：必要に応じてコメントアウト）
        # TechnicalTerm.objects.all().delete()

        # 安全性の指標
        safety_terms = [
            {
                'name': '流動比率',
                'term_category': '安全性',
                'description1': '企業の短期的な支払能力を示す指標で、一般的に100%以上が望ましいとされています。',
                'description2': '100%以上',
                'description3': '流動資産 ÷ 流動負債 × 100 (%)',
            },
            {
                'name': '当座比率',
                'term_category': '安全性',
                'description1': '流動比率から在庫を除いた指標で、より厳密な短期的な支払能力を示します。一般的に100%以上が望ましいとされています。',
                'description2': '100%以上',
                'description3': '（流動資産 - 棚卸資産）÷ 流動負債 × 100 (%)',
            },
            {
                'name': '固定比率',
                'term_category': '安全性',
                'description1': '固定資産が自己資本でどの程度賄われているかを示す指標です。100%以下が望ましいとされています。',
                'description2': '100%以下',
                'description3': '固定資産 ÷ 自己資本 × 100 (%)',
            },
            {
                'name': '固定長期適合率',
                'term_category': '安全性',
                'description1': '固定資産が自己資本と固定負債でどの程度賄われているかを示す指標です。100%以下が望ましいとされています。',
                'description2': '100%以下',
                'description3': '固定資産 ÷ （自己資本 + 固定負債）× 100 (%)',
            },
            {
                'name': '負債資本比率',
                'term_category': '安全性',
                'description1': '総負債が自己資本の何倍かを示す指標です。低いほど財務の安全性が高いとされています。',
                'description2': '1.0以下が望ましい',
                'description3': '総負債 ÷ 純資産',
            },
        ]

        # 収益性の指標
        profitability_terms = [
            {
                'name': '売上総利益率（粗利益率）',
                'term_category': '収益性',
                'description1': '売上高に対する粗利益の割合を示す指標です。業種によって異なりますが、一般的に高いほど良いとされています。',
                'description2': '業種により異なる',
                'description3': '売上総利益 ÷ 売上高 × 100 (%)',
            },
            {
                'name': '営業利益率',
                'term_category': '収益性',
                'description1': '売上高に対する営業利益の割合を示す指標です。本業の収益性を示します。',
                'description2': '業種により異なる',
                'description3': '営業利益 ÷ 売上高 × 100 (%)',
            },
            {
                'name': '経常利益率',
                'term_category': '収益性',
                'description1': '売上高に対する経常利益の割合を示す指標です。企業の本業と財務活動を含めた収益性を示します。',
                'description2': '業種により異なる',
                'description3': '経常利益 ÷ 売上高 × 100 (%)',
            },
            {
                'name': 'ROA（総資本経常利益率）',
                'term_category': '収益性',
                'description1': '総資産に対する経常利益の割合を示す指標です。資産をどれだけ効率的に活用して利益を生み出しているかを示します。',
                'description2': '高いほど良い',
                'description3': '経常利益 ÷ 総資産 × 100 (%)',
            },
            {
                'name': 'ROE（自己資本利益率）',
                'term_category': '収益性',
                'description1': '自己資本に対する経常利益の割合を示す指標です。株主資本の運用効率を示します。',
                'description2': '高いほど良い',
                'description3': '経常利益 ÷ 純資産 × 100 (%)',
            },
        ]

        # 生産性の指標
        productivity_terms = [
            {
                'name': '労働生産性',
                'term_category': '生産性',
                'description1': '従業員1人あたりの付加価値額を示す指標です。付加価値 = 営業利益 + 人件費 + 減価償却費 + 支払利息',
                'description2': '高いほど良い',
                'description3': '付加価値 ÷ 従業員数',
            },
        ]

        # 成長性の指標
        growth_terms = [
            {
                'name': '対前年度売上高成長率',
                'term_category': '成長性',
                'description1': '前期と比較した売上高の増減率を示す指標です。企業の成長性を評価する重要な指標です。',
                'description2': '高いほど良い',
                'description3': '（当期売上高 - 前期売上高）÷ 前期売上高 × 100 (%)',
            },
        ]

        # 効率性の指標
        efficiency_terms = [
            {
                'name': '総資産回転率',
                'term_category': '効率性',
                'description1': '総資産をどれだけ効率的に活用して売上を生み出しているかを示す指標です。高いほど資産の活用効率が良いとされています。',
                'description2': '高いほど良い',
                'description3': '売上高 ÷ 総資産',
            },
            {
                'name': '在庫回転期間',
                'term_category': '効率性',
                'description1': '在庫が何ヶ月分の売上に相当するかを示す指標です。短いほど在庫の回転が速く、効率的とされています。',
                'description2': '短いほど良い',
                'description3': '棚卸資産 ÷ 売上高 × 12 (ヶ月)',
            },
            {
                'name': '売上債権回転期間',
                'term_category': '効率性',
                'description1': '売上債権が何ヶ月分の売上に相当するかを示す指標です。短いほど回収が速く、効率的とされています。',
                'description2': '短いほど良い',
                'description3': '売上債権 ÷ 売上高 × 12 (ヶ月)',
            },
            {
                'name': '営業運転資本回転期間',
                'term_category': '効率性',
                'description1': '営業運転資本が何ヶ月分の売上に相当するかを示す指標です。短いほど資金の回転が速く、効率的とされています。',
                'description2': '短いほど良い',
                'description3': '営業運転資本 ÷ 売上高 × 12 (ヶ月)',
            },
        ]

        # すべての用語を統合
        all_terms = safety_terms + profitability_terms + productivity_terms + growth_terms + efficiency_terms

        created_count = 0
        updated_count = 0

        for term_data in all_terms:
            term, created = TechnicalTerm.objects.update_or_create(
                name=term_data['name'],
                defaults={
                    'term_category': term_data['term_category'],
                    'description1': term_data['description1'],
                    'description2': term_data['description2'],
                    'description3': term_data['description3'],
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ 作成: {term.name}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'↻ 更新: {term.name}'))

        self.stdout.write(self.style.SUCCESS(
            f'\n完了: {created_count}件作成、{updated_count}件更新しました。'
        ))

