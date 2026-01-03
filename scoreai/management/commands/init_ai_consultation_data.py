"""
AI相談機能の初期データ投入コマンド

使用方法:
    docker compose exec django python manage.py init_ai_consultation_data
"""
from django.core.management.base import BaseCommand
from scoreai.models import AIConsultationType, AIConsultationScript, AIConsultationFAQ
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'AI相談機能の初期データを投入します'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("AI相談機能の初期データ投入を開始します..."))
        self.stdout.write("=" * 60)
        
        # 既存の「補助金相談」または「補助金・助成金相談」を「補助金・助成金」に更新
        old_names = ['補助金相談', '補助金・助成金相談']
        for old_name in old_names:
            old_type = AIConsultationType.objects.filter(name=old_name).first()
            if old_type:
                old_type.name = '補助金・助成金'
                old_type.save()
                self.stdout.write(self.style.SUCCESS(f"✓ 既存の「{old_name}」を「補助金・助成金」に更新しました"))
                break

        # 相談タイプの作成
        consultation_types_data = [
            {
                'name': '財務相談',
                'description': '決算書データを基に分析',
                'order': 1,
                'color': '#4CAF50',
            },
            {
                'name': '補助金・助成金',
                'description': '業種・規模を基に提案',
                'order': 2,
                'color': '#2196F3',
            },
            {
                'name': '税務相談',
                'description': '税務情報を基に提案',
                'order': 3,
                'color': '#FF9800',
            },
            {
                'name': '法律相談',
                'description': '契約・法務を基に提案',
                'order': 4,
                'color': '#9C27B0',
            },
            {
                'name': 'DX',
                'description': 'デジタル変革・IT導入を基に提案',
                'order': 5,
                'color': '#00BCD4',
            },
            {
                'name': '予算策定',
                'description': '前期実績と借入情報を基に予算を作成',
                'order': 6,
                'color': '#FF5722',
            },
            {
                'name': '人事相談',
                'description': '人事・労務に関する相談に対応',
                'order': 7,
                'color': '#E91E63',
            },
            {
                'name': '戦略壁打ち',
                'description': '経営戦略や事業計画についての相談に対応',
                'order': 8,
                'color': '#795548',
            },
        ]

        consultation_types = {}
        for data in consultation_types_data:
            consultation_type, created = AIConsultationType.objects.get_or_create(
                name=data['name'],
                defaults={
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
        financial_script = """
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

        # 補助金・助成金のデフォルトスクリプト
        subsidy_script = """会社の業種、規模、財務状況を基に、適切な補助金・助成金制度を提案してください。
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

        if consultation_types.get('補助金・助成金'):
            script, created = AIConsultationScript.objects.get_or_create(
                consultation_type=consultation_types['補助金・助成金'],
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
                self.stdout.write(self.style.SUCCESS("✓ 補助金・助成金のデフォルトスクリプトを作成しました"))
            else:
                self.stdout.write("→ 補助金・助成金のデフォルトスクリプトは既に存在します")

        # 税務相談のデフォルトスクリプト
        tax_script = """会社の財務状況と税務情報を基に、適切な税務アドバイスを提供してください。
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
        legal_script = """会社の状況を基に、適切な法的アドバイスを提供してください。
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

        # DXのデフォルトスクリプト
        dx_script = """会社の業種、規模、財務状況を基に、適切なDX施策やIT導入を提案してください。
返答は日本語で、分かりやすく、具体的な導入方法や効果も含めて説明してください。"""

        dx_template = """【会社情報】
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
1. 業種・規模に適したDX施策の提案
2. ITツール・システムの導入提案
3. 導入による効果とROIの試算
4. 導入の優先順位とステップ
5. 補助金・助成金の活用可能性

回答は日本語で、専門的すぎない言葉で説明してください。
具体的なツール名やサービス名も含めて提案してください。"""

        if consultation_types.get('DX'):
            script, created = AIConsultationScript.objects.get_or_create(
                consultation_type=consultation_types['DX'],
                is_default=True,
                defaults={
                    'name': 'デフォルト',
                    'system_instruction': dx_script,
                    'default_prompt_template': dx_template,
                    'is_active': True,
                    'created_by': superuser,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS("✓ DXのデフォルトスクリプトを作成しました"))
            else:
                self.stdout.write("→ DXのデフォルトスクリプトは既に存在します")

        # 予算策定のデフォルトスクリプト
        budget_script = """あなたは財務分析の専門家です。前期実績と指定された条件を基に、適切な予算を作成してください。
予算は現実的で実現可能な数値である必要があります。借入金残高の計算も正確に行ってください。
返答は必ずJSON形式で返してください。説明文は不要です。"""

        budget_template = """【会社情報】
会社名: {company_name}
業種: {industry}
規模: {size}
決算月: {fiscal_month}月

【前期実績（{previous_year}年）】
{previous_fiscal_summary}

【借入金情報（{target_year}年度末予測残高）】
{debt_info}

【予算策定条件】
- 対象年度: {target_year}年
- 売上高成長率: {sales_growth_rate}%
- 投資予定額: {investment_amount}千円
- 借入予定額: {borrowing_amount}千円
- 資本金増加予定額: {capital_increase}千円

上記の情報を基に、{target_year}年度の予算を作成してください。
予算はJSON形式で返してください。以下のフィールドを含めてください（単位：千円）：
- sales: 売上高
- gross_profit: 粗利益
- operating_profit: 営業利益
- ordinary_profit: 経常利益
- net_profit: 当期純利益
- total_assets: 資産の部合計
- total_liabilities: 負債の部合計
- total_net_assets: 純資産の部合計
- capital_stock: 資本金
- retained_earnings: 利益剰余金
- short_term_loans_payable: 短期借入金（借入金情報のtotal_short_term_loansを反映）
- long_term_loans_payable: 長期借入金（借入金情報のtotal_long_term_loansを反映）
- total_current_assets: 流動資産合計
- total_fixed_assets: 固定資産合計（投資予定額を加算）
- cash_and_deposits: 現金及び預金
- accounts_receivable: 売上債権
- inventory: 棚卸資産

JSONのみを返してください。説明文は不要です。"""

        if consultation_types.get('予算策定'):
            script, created = AIConsultationScript.objects.get_or_create(
                consultation_type=consultation_types['予算策定'],
                is_default=True,
                defaults={
                    'name': 'デフォルト',
                    'system_instruction': budget_script,
                    'default_prompt_template': budget_template,
                    'is_active': True,
                    'created_by': superuser,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS("✓ 予算策定のデフォルトスクリプトを作成しました"))
            else:
                self.stdout.write("→ 予算策定のデフォルトスクリプトは既に存在します")

        # 人事相談のデフォルトスクリプト
        hr_script = """会社の状況を基に、人事・労務に関する適切なアドバイスを提供してください。
返答は日本語で、分かりやすく、具体的な対応方法も含めて説明してください。
労働法規に準拠したアドバイスを心がけてください。"""

        hr_template = """【会社情報】
会社名: {company_name}
業種: {industry}
規模: {size}

【決算書データ】
{fiscal_summary}

【ユーザーの質問】
{user_message}

上記の情報を基に、以下の点を考慮して回答してください：
1. 人事・労務に関する具体的なアドバイス
2. 労働法規に準拠した対応方法
3. 注意すべき法的リスク
4. 推奨される対応手順
5. 必要に応じて専門家への相談を推奨

回答は日本語で、専門的すぎない言葉で説明してください。
重要な法的判断が必要な場合は、専門家（社会保険労務士、弁護士など）への相談を強く推奨してください。"""

        if consultation_types.get('人事相談'):
            script, created = AIConsultationScript.objects.get_or_create(
                consultation_type=consultation_types['人事相談'],
                is_default=True,
                defaults={
                    'name': 'デフォルト',
                    'system_instruction': hr_script,
                    'default_prompt_template': hr_template,
                    'is_active': True,
                    'created_by': superuser,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS("✓ 人事相談のデフォルトスクリプトを作成しました"))
            else:
                self.stdout.write("→ 人事相談のデフォルトスクリプトは既に存在します")

        # 戦略壁打ちのデフォルトスクリプト
        strategy_script = """あなたは経営戦略の専門家です。会社の財務状況、業種、規模を基に、経営戦略や事業計画についての相談に対応してください。
返答は日本語で、分かりやすく、実践的で具体的なアドバイスを提供してください。
経営者の視点に立ち、戦略的な思考を促すような回答を心がけてください。"""

        strategy_template = """【会社情報】
会社名: {company_name}
業種: {industry}
規模: {size}

【決算書データ】
{fiscal_summary}

【借入情報】
{debt_info}

【月次推移データ】
{monthly_data}

【議事録データ】
{meeting_minutes}

【ユーザーの質問】
{user_message}

上記の情報を基に、以下の点を考慮して回答してください：
1. 会社の現状分析（強み・弱み・機会・脅威）
2. 経営戦略や事業計画に関する具体的な提案
3. 優先すべきアクションとその理由
4. リスク要因と対策
5. 中長期的な視点からのアドバイス

回答は日本語で、専門的すぎない言葉で説明してください。
経営者の視点に立ち、実践的で実行可能な提案を心がけてください。"""

        if consultation_types.get('戦略壁打ち'):
            script, created = AIConsultationScript.objects.get_or_create(
                consultation_type=consultation_types['戦略壁打ち'],
                is_default=True,
                defaults={
                    'name': 'デフォルト',
                    'system_instruction': strategy_script,
                    'default_prompt_template': strategy_template,
                    'is_active': True,
                    'created_by': superuser,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS("✓ 戦略壁打ちのデフォルトスクリプトを作成しました"))
            else:
                self.stdout.write("→ 戦略壁打ちのデフォルトスクリプトは既に存在します")

        # よくある質問の作成
        faqs_data = [
            {
                'consultation_type_name': '補助金・助成金',
                'questions': [
                    {'question': '中小企業省力化投資補助金について教えて', 'order': 1},
                    {'question': 'IT導入補助金の申請方法を教えて', 'order': 2},
                    {'question': '補助金の申請期限はいつですか', 'order': 3},
                ]
            },
            {
                'consultation_type_name': '財務相談',
                'questions': [
                    {'question': '今期の着地予測をしてください', 'order': 1},
                    {'question': '財務状況の改善提案をしてください', 'order': 2},
                    {'question': '資金繰り表を作成してください', 'order': 3},
                ]
            },
            {
                'consultation_type_name': '税務相談',
                'questions': [
                    {'question': '節税対策を教えて', 'order': 1},
                    {'question': '消費税の還付について教えて', 'order': 2},
                    {'question': '税務調査の対策を教えて', 'order': 3},
                ]
            },
            {
                'consultation_type_name': '法律相談',
                'questions': [
                    {'question': '契約書の確認をしてください', 'order': 1},
                    {'question': '労働法に関する質問', 'order': 2},
                    {'question': '知的財産権について教えて', 'order': 3},
                ]
            },
            {
                'consultation_type_name': 'DX',
                'questions': [
                    {'question': 'DX施策の提案をしてください', 'order': 1},
                    {'question': 'ITツールの導入提案をしてください', 'order': 2},
                    {'question': '業務効率化のためのシステムを教えて', 'order': 3},
                ]
            },
            {
                'consultation_type_name': '人事相談',
                'questions': [
                    {'question': '採用計画の立て方を教えて', 'order': 1},
                    {'question': '評価制度の設計について相談したい', 'order': 2},
                    {'question': '労働時間管理の方法を教えて', 'order': 3},
                ]
            },
            {
                'consultation_type_name': '戦略壁打ち',
                'questions': [
                    {'question': '事業計画の見直しについて相談したい', 'order': 1},
                    {'question': '新規事業の立ち上げについて相談したい', 'order': 2},
                    {'question': '経営戦略の方向性について相談したい', 'order': 3},
                ]
            },
        ]
        
        for faq_group in faqs_data:
            consultation_type = consultation_types.get(faq_group['consultation_type_name'])
            if consultation_type:
                for q_data in faq_group['questions']:
                    faq, created = AIConsultationFAQ.objects.get_or_create(
                        consultation_type=consultation_type,
                        question=q_data['question'],
                        defaults={
                            'order': q_data['order'],
                            'is_active': True,
                        }
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f"✓ よくある質問を作成しました: {consultation_type.name} - {q_data['question']}"))
                    else:
                        self.stdout.write(f"→ よくある質問は既に存在します: {consultation_type.name} - {q_data['question']}")

        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("初期データ投入が完了しました！"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"\n作成されたデータ:")
        self.stdout.write(f"  相談タイプ: {AIConsultationType.objects.count()}件")
        self.stdout.write(f"  システムスクリプト: {AIConsultationScript.objects.count()}件")
        self.stdout.write(f"  よくある質問: {AIConsultationFAQ.objects.count()}件")
        self.stdout.write("\n次のステップ:")
        self.stdout.write("  1. サーバーを再起動: docker compose restart django")
        self.stdout.write("  2. AI相談センターにアクセス: http://localhost:8000/ai-consultation/")

