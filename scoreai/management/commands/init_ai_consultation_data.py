"""
AI相談機能の初期データ投入コマンド

使用方法:
    docker compose exec django python manage.py init_ai_consultation_data
"""
from django.core.management.base import BaseCommand
from scoreai.models import AIConsultationType, AIConsultationScript
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'AI相談機能の初期データを投入します'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("AI相談機能の初期データ投入を開始します..."))
        self.stdout.write("=" * 60)
        
        # 既存の「補助金相談」を「補助金・助成金相談」に更新
        old_type = AIConsultationType.objects.filter(name='補助金相談').first()
        if old_type:
            old_type.name = '補助金・助成金相談'
            old_type.save()
            self.stdout.write(self.style.SUCCESS("✓ 既存の「補助金相談」を「補助金・助成金相談」に更新しました"))

        # 相談タイプの作成
        consultation_types_data = [
            {
                'name': '財務相談',
                'icon': '💰',
                'description': '決算書データを基に分析',
                'order': 1,
                'color': '#4CAF50',
            },
            {
                'name': '補助金・助成金相談',
                'icon': '💼',
                'description': '業種・規模を基に提案',
                'order': 2,
                'color': '#2196F3',
            },
            {
                'name': '税務相談',
                'icon': '📋',
                'description': '税務情報を基に提案',
                'order': 3,
                'color': '#FF9800',
            },
            {
                'name': '法律相談',
                'icon': '⚖️',
                'description': '契約・法務を基に提案',
                'order': 4,
                'color': '#9C27B0',
            },
        ]

        consultation_types = {}
        for data in consultation_types_data:
            consultation_type, created = AIConsultationType.objects.get_or_create(
                name=data['name'],
                defaults={
                    'icon': data['icon'],
                    'description': data['description'],
                    'order': data['order'],
                    'color': data['color'],
                    'is_active': True,
                }
            )
            consultation_types[data['name']] = consultation_type
            if created:
                self.stdout.write(self.style.SUCCESS(f"✓ 相談タイプを作成しました: {data['name']}"))
            else:
                self.stdout.write(f"→ 相談タイプは既に存在します: {data['name']}")

        # スーパーユーザーを取得（デフォルトスクリプトの作成者として使用）
        superuser = User.objects.filter(is_superuser=True).first()
        if not superuser:
            self.stdout.write(self.style.WARNING("⚠️  警告: スーパーユーザーが見つかりません。デフォルトスクリプトの作成者を設定できません。"))
            self.stdout.write(self.style.WARNING("   スーパーユーザーを作成するには: python manage.py createsuperuser"))

        # 財務相談のデフォルトスクリプト
        financial_script = """あなたは経験豊富な財務アドバイザーです。
与えられた財務情報に基づいて、実践的で具体的なアドバイスを提供してください。
返答は日本語で、分かりやすく、専門的すぎない言葉で説明してください。"""

        financial_template = """【会社情報】
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

回答は日本語で、専門的すぎない言葉で説明してください。"""

        if consultation_types.get('財務相談'):
            script, created = AIConsultationScript.objects.get_or_create(
                consultation_type=consultation_types['財務相談'],
                is_default=True,
                defaults={
                    'name': 'デフォルト',
                    'system_instruction': financial_script,
                    'default_prompt_template': financial_template,
                    'is_active': True,
                    'created_by': superuser,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS("✓ 財務相談のデフォルトスクリプトを作成しました"))
            else:
                self.stdout.write("→ 財務相談のデフォルトスクリプトは既に存在します")

        # 補助金・助成金相談のデフォルトスクリプト
        subsidy_script = """あなたは補助金・助成金申請の専門家です。
        会社の業種、規模、財務状況を基に、適切な補助金・助成金制度を提案してください。
返答は日本語で、分かりやすく、具体的な手続き方法も含めて説明してください。"""

        subsidy_template = """【会社情報】
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

回答は日本語で、専門的すぎない言葉で説明してください。"""

        if consultation_types.get('補助金・助成金相談'):
            script, created = AIConsultationScript.objects.get_or_create(
                consultation_type=consultation_types['補助金・助成金相談'],
                is_default=True,
                defaults={
                    'name': 'デフォルト',
                    'system_instruction': subsidy_script,
                    'default_prompt_template': subsidy_template,
                    'is_active': True,
                    'created_by': superuser,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS("✓ 補助金・助成金相談のデフォルトスクリプトを作成しました"))
            else:
                self.stdout.write("→ 補助金・助成金相談のデフォルトスクリプトは既に存在します")

        # 税務相談のデフォルトスクリプト
        tax_script = """あなたは税務の専門家です。
会社の財務状況と税務情報を基に、適切な税務アドバイスを提供してください。
返答は日本語で、分かりやすく、具体的な手続き方法も含めて説明してください。"""

        tax_template = """【会社情報】
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

回答は日本語で、専門的すぎない言葉で説明してください。"""

        if consultation_types.get('税務相談'):
            script, created = AIConsultationScript.objects.get_or_create(
                consultation_type=consultation_types['税務相談'],
                is_default=True,
                defaults={
                    'name': 'デフォルト',
                    'system_instruction': tax_script,
                    'default_prompt_template': tax_template,
                    'is_active': True,
                    'created_by': superuser,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS("✓ 税務相談のデフォルトスクリプトを作成しました"))
            else:
                self.stdout.write("→ 税務相談のデフォルトスクリプトは既に存在します")

        # 法律相談のデフォルトスクリプト
        legal_script = """あなたは法律の専門家です。
会社の状況を基に、適切な法的アドバイスを提供してください。
返答は日本語で、分かりやすく、具体的な手続き方法も含めて説明してください。
ただし、具体的な法律相談については専門家への相談を推奨してください。"""

        legal_template = """【会社情報】
会社名: {company_name}
業種: {industry}
規模: {size}

【ユーザーの質問】
{user_message}

上記の情報を基に、以下の点を考慮して回答してください：
1. 法的な観点からのアドバイス
2. 注意すべき点
3. 推奨される対応
4. 専門家への相談が必要な場合の指摘

回答は日本語で、専門的すぎない言葉で説明してください。
重要な法的判断が必要な場合は、専門家への相談を強く推奨してください。"""

        if consultation_types.get('法律相談'):
            script, created = AIConsultationScript.objects.get_or_create(
                consultation_type=consultation_types['法律相談'],
                is_default=True,
                defaults={
                    'name': 'デフォルト',
                    'system_instruction': legal_script,
                    'default_prompt_template': legal_template,
                    'is_active': True,
                    'created_by': superuser,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS("✓ 法律相談のデフォルトスクリプトを作成しました"))
            else:
                self.stdout.write("→ 法律相談のデフォルトスクリプトは既に存在します")

        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("初期データ投入が完了しました！"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"\n作成されたデータ:")
        self.stdout.write(f"  相談タイプ: {AIConsultationType.objects.count()}件")
        self.stdout.write(f"  システムスクリプト: {AIConsultationScript.objects.count()}件")
        self.stdout.write("\n次のステップ:")
        self.stdout.write("  1. サーバーを再起動: docker compose restart django")
        self.stdout.write("  2. AI相談センターにアクセス: http://localhost:8000/ai-consultation/")

