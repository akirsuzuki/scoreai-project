# Generated by Django 5.1.2 on 2024-12-05 12:00

import ulid.api.api
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scoreai', '0066_alter_company_id_alter_debt_id_alter_firm_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='technicalterm',
            name='term_category',
            field=models.CharField(choices=[('安全性', '安全性'), ('収益性', '収益性'), ('生産性', '生産性'), ('成長性', '成長性'), ('効率性', '効率性'), ('その他', 'その他')], default='その他', max_length=50),
        ),
    ]
