# Generated manually for Todo model changes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scoreai', '0125_populate_todo_categories'),
    ]

    operations = [
        # assigned_toフィールドを削除
        migrations.RemoveField(
            model_name='todo',
            name='assigned_to',
        ),
        # owner_typeフィールドを追加
        migrations.AddField(
            model_name='todo',
            name='owner_type',
            field=models.CharField(
                choices=[('company', '会社'), ('firm', 'Firm')],
                default='company',
                help_text='会社側のタスクかFirm側のタスクかを区別',
                max_length=10,
                verbose_name='タスク所有区分'
            ),
        ),
        # owner_typeにインデックスを追加
        migrations.AddIndex(
            model_name='todo',
            index=models.Index(fields=['company', 'owner_type'], name='scoreai_tod_company_owner_idx'),
        ),
    ]
