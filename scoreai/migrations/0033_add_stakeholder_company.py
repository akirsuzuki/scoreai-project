# Generated by Django 5.0.4 on 2024-10-01 09:15

import django.db.models.deletion
import ulid.api.api
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scoreai', '0032_alter_fiscal_summary_year'),
    ]

    operations = [
        migrations.AddField(
            model_name='stakeholder',
            name='company',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='scoreai.company'),
            preserve_default=False,
        ),
    ]
