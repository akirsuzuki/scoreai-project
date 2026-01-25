# Generated manually for populating initial Todo categories

from django.db import migrations


def create_initial_categories(apps, schema_editor):
    """初期カテゴリを作成"""
    TodoCategory = apps.get_model('scoreai', 'TodoCategory')

    categories = [
        {'name': '決算', 'color': '#0d6efd', 'display_order': 1},
        {'name': '法人税', 'color': '#6610f2', 'display_order': 2},
        {'name': '消費税', 'color': '#6f42c1', 'display_order': 3},
        {'name': '所得税', 'color': '#d63384', 'display_order': 4},
        {'name': '年末調整', 'color': '#dc3545', 'display_order': 5},
        {'name': '源泉徴収', 'color': '#fd7e14', 'display_order': 6},
        {'name': '相続', 'color': '#ffc107', 'display_order': 7},
        {'name': '贈与', 'color': '#198754', 'display_order': 8},
        {'name': '資金調達', 'color': '#20c997', 'display_order': 9},
        {'name': '新規事業', 'color': '#0dcaf0', 'display_order': 10},
    ]

    for cat_data in categories:
        TodoCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults={
                'color': cat_data['color'],
                'display_order': cat_data['display_order'],
                'is_active': True,
            }
        )


def reverse_initial_categories(apps, schema_editor):
    """初期カテゴリを削除"""
    TodoCategory = apps.get_model('scoreai', 'TodoCategory')
    TodoCategory.objects.filter(name__in=[
        '決算', '法人税', '消費税', '所得税', '年末調整',
        '源泉徴収', '相続', '贈与', '資金調達', '新規事業'
    ]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('scoreai', '0124_add_todo_models'),
    ]

    operations = [
        migrations.RunPython(create_initial_categories, reverse_initial_categories),
    ]
