# Generated manually

from django.db import migrations, models


def set_default_debt_type(apps, schema_editor):
    """既存のDebtレコードを全て証書貸付に設定"""
    Debt = apps.get_model('scoreai', 'Debt')
    Debt.objects.all().update(debt_type='certificate')


def reverse_set_default_debt_type(apps, schema_editor):
    """ロールバック時は何もしない（フィールドが削除されるため）"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('scoreai', '0115_remove_dinner_24hours'),
    ]

    operations = [
        migrations.AddField(
            model_name='debt',
            name='debt_type',
            field=models.CharField(
                choices=[('certificate', '証書貸付'), ('corporate_bond', '社債')],
                default='certificate',
                help_text='証書貸付: 毎月返済、社債: 指定月のみ返済',
                max_length=20,
                verbose_name='借入区分'
            ),
        ),
        migrations.AddField(
            model_name='debt',
            name='repayment_months',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='社債の場合のみ使用。返済月を指定（例: [1, 7] で1月と7月に返済）。証書貸付の場合は空欄。',
                verbose_name='返済月'
            ),
        ),
        migrations.RunPython(set_default_debt_type, reverse_set_default_debt_type),
    ]

