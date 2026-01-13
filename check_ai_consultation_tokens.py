#!/usr/bin/env python3
"""
AI相談のトークン数統計を取得するスクリプト
"""
import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Django設定を読み込む
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'score.settings')

import django
django.setup()

from django.db.models import Avg, Min, Max, Count, Sum
from scoreai.models import AIConsultationHistory

def main():
    print("=" * 60)
    print("AI相談のトークン数統計")
    print("=" * 60)
    print()
    
    # 全データの統計
    total_count = AIConsultationHistory.objects.filter(total_tokens__gt=0).count()
    
    if total_count == 0:
        print("⚠️  トークン数が記録されているAI相談履歴がありません。")
        print("   実際にAI相談を使用してから、再度このスクリプトを実行してください。")
        return
    
    print(f"【対象データ数】")
    print(f"トークン数が記録されている相談回数: {total_count:,}回")
    print()
    
    # 合計トークン数の統計
    stats = AIConsultationHistory.objects.filter(total_tokens__gt=0).aggregate(
        avg_total=Avg('total_tokens'),
        min_total=Min('total_tokens'),
        max_total=Max('total_tokens'),
        avg_input=Avg('input_tokens'),
        avg_output=Avg('output_tokens'),
    )
    
    print("【合計トークン数（1回あたり）】")
    print(f"平均: {stats['avg_total']:,.0f}トークン")
    print(f"最小: {stats['min_total']:,}トークン")
    print(f"最大: {stats['max_total']:,}トークン")
    print()
    
    print("【入力トークン数（1回あたり）】")
    if stats['avg_input']:
        print(f"平均: {stats['avg_input']:,.0f}トークン")
    else:
        print("データなし")
    print()
    
    print("【出力トークン数（1回あたり）】")
    if stats['avg_output']:
        print(f"平均: {stats['avg_output']:,.0f}トークン")
    else:
        print("データなし")
    print()
    
    # トークン数の分布
    print("【トークン数の分布】")
    ranges = [
        (0, 1000, "1,000トークン未満"),
        (1000, 2000, "1,000-2,000トークン"),
        (2000, 3000, "2,000-3,000トークン"),
        (3000, 5000, "3,000-5,000トークン"),
        (5000, 10000, "5,000-10,000トークン"),
        (10000, None, "10,000トークン以上"),
    ]
    
    for min_val, max_val, label in ranges:
        if max_val:
            count = AIConsultationHistory.objects.filter(
                total_tokens__gte=min_val,
                total_tokens__lt=max_val
            ).count()
        else:
            count = AIConsultationHistory.objects.filter(
                total_tokens__gte=min_val
            ).count()
        percentage = (count / total_count * 100) if total_count > 0 else 0
        print(f"{label}: {count:,}回 ({percentage:.1f}%)")
    print()
    
    # 最近10件の詳細
    print("【最近10件の詳細】")
    recent = AIConsultationHistory.objects.filter(
        total_tokens__gt=0
    ).order_by('-created_at')[:10]
    
    for i, history in enumerate(recent, 1):
        print(f"{i}. {history.created_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"   合計: {history.total_tokens:,}トークン")
        if history.input_tokens:
            print(f"   入力: {history.input_tokens:,}トークン")
        if history.output_tokens:
            print(f"   出力: {history.output_tokens:,}トークン")
        print()
    
    print("=" * 60)
    print("統計取得完了")
    print("=" * 60)

if __name__ == '__main__':
    main()
