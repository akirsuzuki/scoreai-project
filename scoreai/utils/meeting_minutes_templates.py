"""
議事録テンプレート定義
"""
from typing import Dict, Optional, Tuple
from django.db.models import Q

# 会議体名の日本語マッピング
MEETING_TYPE_NAMES = {
    'shareholders_meeting': '株主総会',
    'board_of_directors': '取締役会',
    'management_committee': '経営会議',
}

# 開催種別名の日本語マッピング
MEETING_CATEGORY_NAMES = {
    'regular': '定時',
    'extraordinary': '臨時',
}

# 議題名の日本語マッピング
AGENDA_NAMES = {
    # 株主総会向け
    'financial_approval': '決算承認',
    'officer_election': '役員選任',
    'surplus_disposition': '剰余金処分',
    'articles_amendment': '定款変更',
    # 取締役会向け
    'representative_director': '代表取締役の選定',
    'asset_disposition': '重要な財産の処分',
    'meeting_convening': '招集決定',
    'new_shares': '新株発行',
    # 経営会議向け
    'business_strategy': '事業戦略の検討',
    'budget_approval': '予算の承認',
    'organization_change': '組織変更の決定',
    'other': 'その他',
}

# 議題の詳細説明
AGENDA_DESCRIPTIONS = {
    'financial_approval': '計算書類（貸借対照表、損益計算書、株主資本等変動計算書、個別注記表）および事業報告の承認',
    'officer_election': '取締役・監査役の選任（任期満了や増員）',
    'surplus_disposition': '剰余金の配当に関する決定',
    'articles_amendment': '定款の変更（商号変更や事業目的の追加など）',
    'representative_director': '代表取締役の選定および役職の決定',
    'asset_disposition': '重要な財産の処分（資産の売却や多額の借入など）',
    'meeting_convening': '株主総会の開催日時・場所の決定',
    'new_shares': '新株発行に関する決定（資金調達・増資）',
    'business_strategy': '事業戦略の検討および決定',
    'budget_approval': '予算の承認',
    'organization_change': '組織変更の決定',
    'other': 'その他の議題',
}


def get_meeting_title(meeting_type: str, meeting_category: str, agenda: str) -> str:
    """会議タイトルを生成"""
    meeting_name = MEETING_TYPE_NAMES.get(meeting_type, meeting_type)
    category_name = MEETING_CATEGORY_NAMES.get(meeting_category, meeting_category)
    agenda_name = AGENDA_NAMES.get(agenda, agenda)
    
    return f'{category_name}{meeting_name}議事録（{agenda_name}）'


def get_meeting_minutes_script(
    meeting_type: str,
    meeting_category: str,
    agenda: str
) -> Optional['MeetingMinutesAIScript']:
    """
    議事録生成用のスクリプトを取得
    
    Args:
        meeting_type: 会議体
        meeting_category: 開催種別
        agenda: 議題
    
    Returns:
        MeetingMinutesAIScriptオブジェクト、見つからない場合はNone
    """
    from ..models import MeetingMinutesAIScript
    
    # まずデフォルトスクリプトを探す
    script = MeetingMinutesAIScript.objects.filter(
        meeting_type=meeting_type,
        meeting_category=meeting_category,
        agenda=agenda,
        is_default=True,
        is_active=True
    ).first()
    
    # デフォルトが見つからない場合は、任意のアクティブなスクリプトを探す
    if not script:
        script = MeetingMinutesAIScript.objects.filter(
            meeting_type=meeting_type,
            meeting_category=meeting_category,
            agenda=agenda,
            is_active=True
        ).first()
    
    return script


def build_meeting_minutes_prompt(
    meeting_type: str,
    meeting_category: str,
    agenda: str,
    additional_info: str = '',
    company_name: str = '',
    script: Optional['MeetingMinutesAIScript'] = None
) -> Tuple[str, Optional[str]]:
    """
    議事録生成用のプロンプトを構築
    
    Args:
        meeting_type: 会議体
        meeting_category: 開催種別
        agenda: 議題
        additional_info: 追加情報
        company_name: 会社名
        script: MeetingMinutesAIScriptオブジェクト（Noneの場合はデフォルトテンプレートを使用）
    
    Returns:
        (prompt, system_instruction)のタプル
    """
    meeting_name = MEETING_TYPE_NAMES.get(meeting_type, meeting_type)
    category_name = MEETING_CATEGORY_NAMES.get(meeting_category, meeting_category)
    agenda_name = AGENDA_NAMES.get(agenda, agenda)
    agenda_description = AGENDA_DESCRIPTIONS.get(agenda, '')
    
    # スクリプトが指定されている場合はそれを使用
    if script:
        system_instruction = script.system_instruction
        template = script.prompt_template
        
        # テンプレート変数を置換
        prompt = template.format(
            meeting_type_name=meeting_name,
            meeting_category_name=category_name,
            agenda_name=agenda_name,
            agenda_description=agenda_description,
            company_name=company_name or '',
            additional_info=additional_info or ''
        )
        
        return prompt, system_instruction
    
    # デフォルトのプロンプト生成（フォールバック）
    prompt = f"""以下の条件に基づいて、{category_name}{meeting_name}の議事録をMarkdown形式で作成してください。

【会議情報】
- 会議体: {meeting_name}
- 開催種別: {category_name}
- 主な議題: {agenda_name}
- 議題の詳細: {agenda_description}
"""
    
    if company_name:
        prompt += f"- 会社名: {company_name}\n"
    
    if additional_info:
        prompt += f"\n【追加情報】\n{additional_info}\n"
    
    prompt += f"""
【議事録の構成】
以下の構成で議事録を作成してください：

1. 表題: 「{category_name}{meeting_name}議事録（{agenda_name}）」
2. 会議の基本情報
   - 開催日時
   - 開催場所
   - 出席者
   - 議長
3. 議題: {agenda_name}
4. 議事の経過
5. 決議事項
6. その他の議事
7. 閉会

【作成要件】
- Markdown形式で記述してください
- 法的に適切な議事録の形式に従ってください
- 具体的で実務的な内容を含めてください
- 日本語で記述してください
- 見出しは適切なレベル（#、##、###）を使用してください
- 箇条書きや表を適切に使用してください

議事録を作成してください。"""
    
    system_instruction = """あなたは企業の議事録作成の専門家です。
法的に適切で、実務的に使用できる議事録を作成してください。
Markdown形式で、見出し、箇条書き、表などを適切に使用して構造化された議事録を作成してください。"""
    
    return prompt, system_instruction

