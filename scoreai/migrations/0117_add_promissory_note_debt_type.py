# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scoreai', '0116_add_debt_type_and_repayment_months'),
    ]

    operations = [
        migrations.AlterField(
            model_name='debt',
            name='debt_type',
            field=models.CharField(
                choices=[('certificate', '証書貸付'), ('corporate_bond', '社債'), ('promissory_note', '手形貸付')],
                default='certificate',
                help_text='証書貸付: 毎月返済、社債: 指定月のみ返済、手形貸付: 期日一括償還',
                max_length=20,
                verbose_name='借入区分'
            ),
        ),
    ]

