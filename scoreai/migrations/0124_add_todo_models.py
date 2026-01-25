# Generated manually for Todo feature

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_ulid.models


class Migration(migrations.Migration):

    dependencies = [
        ('scoreai', '0123_extend_firm_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='TodoCategory',
            fields=[
                ('id', models.CharField(default=django_ulid.models.ulid.new, editable=False, max_length=26, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='カテゴリ名')),
                ('color', models.CharField(default='#6c757d', help_text='例: #FF5733', max_length=7, verbose_name='カラーコード')),
                ('display_order', models.IntegerField(default=0, verbose_name='表示順')),
                ('is_active', models.BooleanField(default=True, verbose_name='有効')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
            ],
            options={
                'verbose_name': 'To Doカテゴリ',
                'verbose_name_plural': 'To Doカテゴリ',
                'ordering': ['display_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Todo',
            fields=[
                ('id', models.CharField(default=django_ulid.models.ulid.new, editable=False, max_length=26, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200, verbose_name='タイトル')),
                ('content', models.TextField(blank=True, verbose_name='内容')),
                ('due_date', models.DateField(blank=True, null=True, verbose_name='期限')),
                ('status', models.CharField(choices=[('pending', '未着手'), ('in_progress', '進行中'), ('completed', '完了')], default='pending', max_length=20, verbose_name='ステータス')),
                ('priority', models.CharField(choices=[('low', '低'), ('medium', '中'), ('high', '高')], default='medium', max_length=10, verbose_name='優先度')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='完了日')),
                ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_todos', to=settings.AUTH_USER_MODEL, verbose_name='担当者')),
                ('categories', models.ManyToManyField(blank=True, related_name='todos', to='scoreai.todocategory', verbose_name='分類タグ')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='todos', to='scoreai.company', verbose_name='会社')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_todos', to=settings.AUTH_USER_MODEL, verbose_name='作成者')),
            ],
            options={
                'verbose_name': 'To Do',
                'verbose_name_plural': 'To Do',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='todo',
            index=models.Index(fields=['company', 'status'], name='scoreai_tod_company_a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='todo',
            index=models.Index(fields=['company', 'due_date'], name='scoreai_tod_company_d4e5f6_idx'),
        ),
        migrations.AddIndex(
            model_name='todo',
            index=models.Index(fields=['company', 'priority'], name='scoreai_tod_company_g7h8i9_idx'),
        ),
    ]
