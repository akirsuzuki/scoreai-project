from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils import timezone
from django.db.models import ExpressionWrapper, F, fields, IntegerField, GeneratedField
from django.db.models.functions import Floor, Now, ExtractYear, ExtractMonth
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django_ulid.models import ulid
from django.db.models import Case, When, Value, IntegerField
from datetime import datetime
import json
from decimal import Decimal, ROUND_HALF_UP


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    # ユーザーの追加フィールドを定義
    email = models.EmailField('メールアドレス', unique=True, max_length=255)
    username = models.CharField(
        'ユーザー名',
        max_length=20,
        unique=True,
        help_text='20文字以下のユーザー名を入力してください。',
        validators=[UnicodeUsernameValidator()],
        error_messages={
            'unique': "このユーザー名は既に使用されています。",
        },
    )
    is_active = models.BooleanField(
        'Active',
        default=True,
        help_text='IF the user is Active or not.'
    )
    is_financial_consultant = models.BooleanField(default=False)
    is_company_user = models.BooleanField(default=False)
    is_manager = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 不要なフィールドはNoneに
    first_name = None
    last_name = None
    date_joined = None
    groups = None

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'ユーザー'
        verbose_name_plural = 'ユーザー'


class Company(models.Model):
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    name = models.CharField(max_length=255)
    fiscal_month = models.IntegerField("決算月", validators=[MinValueValidator(1), MaxValueValidator(12)])
    code = models.CharField(max_length=20, unique=True)
    industry_classification = models.ForeignKey('IndustryClassification', on_delete=models.SET_NULL, null=True, blank=True)
    industry_subclassification = models.ForeignKey('IndustrySubClassification', on_delete=models.SET_NULL, null=True, blank=True)
    COMPANY_SIZE_CHOICES = [
        ('s', '小規模'),
        ('m', '中規模'),
        ('l', '大規模'),
    ]
    company_size = models.CharField(
        "Company Size",
        max_length=10,
        choices=COMPANY_SIZE_CHOICES,
        default='s',
    )
    api_key = models.CharField('APIキー', max_length=255, blank=True, null=True, help_text='CompanyのAPIキー（上限超過時に使用、Company Userのみ）')
    api_provider = models.CharField('APIプロバイダー', max_length=20, choices=[('gemini', 'Google Gemini'), ('openai', 'OpenAI')], blank=True, null=True, help_text='APIキーのプロバイダー')
    
    # システム情報
    ACCOUNTING_SYSTEM_CHOICES = [
        ('yayoi', '弥生会計'),
        ('freee', 'freee'),
        ('money_forward', 'Money Forward'),
        ('kansanbogyo_v', '勘定奉行Vシリーズ'),
        ('other', 'その他'),
        ('none', '未使用'),
    ]
    accounting_system = models.CharField(
        '会計システム',
        max_length=50,
        choices=ACCOUNTING_SYSTEM_CHOICES,
        blank=True,
        null=True,
        help_text='使用している会計システム'
    )
    accounting_system_other = models.CharField(
        '会計システム（その他）',
        max_length=100,
        blank=True,
        help_text='会計システムが「その他」の場合のシステム名'
    )
    sales_management_system = models.CharField(
        '販売管理システム',
        max_length=100,
        blank=True,
        help_text='使用している販売管理システム名（未使用の場合は空白）'
    )
    purchase_management_system = models.CharField(
        '購買管理システム',
        max_length=100,
        blank=True,
        help_text='使用している購買管理システム名（未使用の場合は空白）'
    )
    production_management_system = models.CharField(
        '生産管理システム',
        max_length=100,
        blank=True,
        help_text='使用している生産管理システム名（未使用の場合は空白）'
    )
    inventory_management_system = models.CharField(
        '在庫管理システム',
        max_length=100,
        blank=True,
        help_text='使用している在庫管理システム名（未使用の場合は空白）'
    )
    payroll_system = models.CharField(
        '給与計算システム',
        max_length=100,
        blank=True,
        help_text='使用している給与計算システム名（未使用の場合は空白）'
    )
    hr_management_system = models.CharField(
        '人事管理システム',
        max_length=100,
        blank=True,
        help_text='使用している人事管理システム名（未使用の場合は空白）'
    )
    core_system = models.CharField(
        '基幹システム',
        max_length=100,
        blank=True,
        help_text='使用している基幹システム名（未使用の場合は空白）'
    )
    other_systems = models.TextField(
        'その他システム',
        blank=True,
        help_text='その他の使用しているシステム情報（複数ある場合は改行で区切る）'
    )

    @property
    def user_count(self):
        return UserCompany.objects.filter(company=self, active=True).count()

    def __str__(self):
        return self.name


class UserCompany(models.Model):
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    # Cascadeにして関連するUserオブジェクトが削除されたときに、そのUserオブジェクトに関連するUserCompanyオブジェクトも自動的に削除
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='users')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='companies')
    active = models.BooleanField(default=True)
    is_selected = models.BooleanField(default=True)
    is_owner = models.BooleanField(default=False)
    as_consultant = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_selected:
            # 同一Userの他レコードのis_selectedをFalseにする
            UserCompany.objects.filter(user=self.user, is_selected=True).update(is_selected=False)
        else:
            # 同一Userの他レコードにis_selected=Trueが存在しない場合、強制的にTrueにする
            if not UserCompany.objects.filter(user=self.user, is_selected=True).exists():
                self.is_selected = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.company} - {self.user}"


class Firm(models.Model):
    API_PROVIDER_CHOICES = [
        ('gemini', 'Google Gemini'),
        ('openai', 'OpenAI'),
    ]
    
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='firms')
    api_key = models.CharField('APIキー', max_length=255, blank=True, null=True, help_text='FirmのAPIキー（上限超過時に使用）')
    api_provider = models.CharField('APIプロバイダー', max_length=20, choices=API_PROVIDER_CHOICES, blank=True, null=True, help_text='APIキーのプロバイダー')

    def __str__(self):
        return self.name


class UserFirm(models.Model):
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_firms')
    firm = models.ForeignKey(Firm, on_delete=models.CASCADE, related_name='user_firms')
    active = models.BooleanField(default=True)
    is_selected = models.BooleanField(default=True)
    is_owner = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_selected:
            # 同一Userの他レコードのis_selectedをFalseにする
            UserFirm.objects.filter(user=self.user, is_selected=True).update(is_selected=False)
        else:
            # 同一Userの他レコードにis_selected=Trueが存在しない場合、強制的にTrueにする
            if not UserFirm.objects.filter(user=self.user, is_selected=True).exists():
                self.is_selected = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.firm} - {self.user}"


class FirmInvitation(models.Model):
    """Firmへの招待を管理するモデル"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    firm = models.ForeignKey(Firm, on_delete=models.CASCADE, related_name='invitations', verbose_name='Firm')
    email = models.EmailField('メールアドレス')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations', verbose_name='招待者')
    is_owner = models.BooleanField('オーナー権限', default=False)
    invited_at = models.DateTimeField('招待日時', auto_now_add=True)
    accepted_at = models.DateTimeField('承認日時', null=True, blank=True)
    is_accepted = models.BooleanField('承認済み', default=False)
    
    class Meta:
        unique_together = ('firm', 'email', 'is_accepted')
        verbose_name = 'Firm招待'
        verbose_name_plural = 'Firm招待'
        ordering = ['-invited_at']
    
    def save(self, *args, **kwargs):
        """保存時にis_acceptedがTrueになった場合、UserFirmレコードを作成"""
        # 既存のレコードがある場合、is_acceptedの変更を確認
        if self.pk:
            try:
                old_instance = FirmInvitation.objects.get(pk=self.pk)
                # is_acceptedがFalseからTrueに変更された場合
                if not old_instance.is_accepted and self.is_accepted:
                    self._create_user_firm()
            except FirmInvitation.DoesNotExist:
                pass
        else:
            # 新規作成時でis_acceptedがTrueの場合
            if self.is_accepted:
                self._create_user_firm()
        
        # accepted_atを設定
        if self.is_accepted and not self.accepted_at:
            from django.utils import timezone
            self.accepted_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def _create_user_firm(self):
        """UserFirmレコードを作成"""
        from django.utils import timezone
        
        # メールアドレスからユーザーを検索
        try:
            user = User.objects.get(email=self.email)
            
            # 既にUserFirmレコードが存在するか確認
            existing_user_firm = UserFirm.objects.filter(
                user=user,
                firm=self.firm
            ).first()
            
            if existing_user_firm:
                # 既存のレコードがある場合は更新
                existing_user_firm.active = True
                existing_user_firm.is_owner = self.is_owner
                existing_user_firm.is_selected = False
                existing_user_firm.save()
            else:
                # 新規作成
                UserFirm.objects.create(
                    user=user,
                    firm=self.firm,
                    active=True,
                    is_owner=self.is_owner,
                    is_selected=False
                )
        except User.DoesNotExist:
            # ユーザーが存在しない場合は何もしない（新規ユーザー招待の場合）
            pass
    
    def __str__(self):
        status = '承認済み' if self.is_accepted else '招待中'
        return f"{self.firm.name} - {self.email} ({status})"


class CompanyInvitation(models.Model):
    """Companyへの招待を管理するモデル"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='invitations', verbose_name='Company')
    email = models.EmailField('メールアドレス')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_company_invitations', verbose_name='招待者')
    is_owner = models.BooleanField('オーナー権限', default=False)
    is_manager = models.BooleanField('マネージャー権限', default=False)
    invited_at = models.DateTimeField('招待日時', auto_now_add=True)
    accepted_at = models.DateTimeField('承認日時', null=True, blank=True)
    is_accepted = models.BooleanField('承認済み', default=False)
    
    class Meta:
        unique_together = ('company', 'email', 'is_accepted')
        verbose_name = 'Company招待'
        verbose_name_plural = 'Company招待'
        ordering = ['-invited_at']
    
    def save(self, *args, **kwargs):
        """保存時にis_acceptedがTrueになった場合、UserCompanyレコードを作成"""
        # 既存のレコードがある場合、is_acceptedの変更を確認
        if self.pk:
            try:
                old_instance = CompanyInvitation.objects.get(pk=self.pk)
                # is_acceptedがFalseからTrueに変更された場合
                if not old_instance.is_accepted and self.is_accepted:
                    self._create_user_company()
            except CompanyInvitation.DoesNotExist:
                pass
        else:
            # 新規作成時でis_acceptedがTrueの場合
            if self.is_accepted:
                self._create_user_company()
        
        # accepted_atを設定
        if self.is_accepted and not self.accepted_at:
            self.accepted_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def _create_user_company(self):
        """UserCompanyレコードを作成"""
        # メールアドレスからユーザーを検索
        try:
            user = User.objects.get(email=self.email)
            
            # 既にUserCompanyレコードが存在するか確認
            existing_user_company = UserCompany.objects.filter(
                user=user,
                company=self.company
            ).first()
            
            if existing_user_company:
                # 既存のレコードがある場合は更新
                existing_user_company.active = True
                existing_user_company.is_owner = self.is_owner
                existing_user_company.is_selected = False
                existing_user_company.save()
            else:
                # 新規作成
                UserCompany.objects.create(
                    user=user,
                    company=self.company,
                    active=True,
                    is_owner=self.is_owner,
                    is_selected=False
                )
            
            # Userモデルのis_managerを更新（UserCompanyにはis_managerフィールドがないため）
            if self.is_manager:
                user.is_manager = True
                user.save()
        except User.DoesNotExist:
            # ユーザーが存在しない場合は何もしない（新規ユーザー招待の場合）
            pass
    
    def __str__(self):
        status = '承認済み' if self.is_accepted else '招待中'
        return f"{self.company.name} - {self.email} ({status})"


class FirmCompany(models.Model):
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    firm = models.ForeignKey(Firm, on_delete=models.CASCADE, related_name='firm_companies')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='firm_companies')
    active = models.BooleanField(default=True)
    start_date = models.DateField("開始日")
    end_date = models.DateField("終了日", null=True, blank=True)
    grace_period_end = models.DateField(
        'グレース期間終了日',
        null=True,
        blank=True,
        help_text='プランダウングレード時の一時的な保持期間'
    )
    # Companyごとの利用枠設定
    api_limit = models.IntegerField(
        'API利用枠',
        default=0,
        help_text='このCompanyに割り当てられたAPI利用枠（0の場合は未割り当て）'
    )
    ocr_limit = models.IntegerField(
        'OCR利用枠',
        default=0,
        help_text='このCompanyに割り当てられたOCR利用枠（0の場合は未割り当て）'
    )
    # Firmユーザーによる代理利用許可フラグ
    allow_firm_api_usage = models.BooleanField(
        'コンサルタントによるAPI代理利用を許可',
        default=False,
        help_text='チェックされている場合、コンサルタントがこの会社のAPI利用枠内でAPIを利用可能'
    )
    allow_firm_ocr_usage = models.BooleanField(
        'コンサルタントによるOCR代理利用を許可',
        default=False,
        help_text='チェックされている場合、コンサルタントがこの会社のOCR利用枠内でOCRを利用可能'
    )

    def clean(self):
        if self.end_date and self.start_date > self.end_date:
            raise ValidationError("終了日は開始日より後でなければなりません。")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.firm} - {self.company}"

    class Meta:
        unique_together = ('firm', 'company')
        verbose_name = 'ファーム会社関連'
        verbose_name_plural = 'ファーム会社関連'


# プラン・サブスクリプション関連のモデル

class FirmPlan(models.Model):
    """Firm向けプランの定義"""
    PLAN_TYPE_CHOICES = [
        ('free', 'Freeプラン（無料・試用）'),
        ('starter', 'Starterプラン'),
        ('professional', 'Professionalプラン'),
        ('enterprise', 'Enterpriseプラン'),
    ]
    
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    plan_type = models.CharField('プランタイプ', max_length=20, choices=PLAN_TYPE_CHOICES, unique=True)
    name = models.CharField('プラン名', max_length=255)
    description = models.TextField('説明', blank=True)
    
    # 料金設定
    monthly_price = models.DecimalField('月額料金', max_digits=10, decimal_places=2, default=0)
    yearly_price = models.DecimalField('年額料金', max_digits=10, decimal_places=2, null=True, blank=True)
    yearly_discount_months = models.IntegerField('年払い割引（無料月数）', default=2)
    
    # 機能制限
    max_companies = models.IntegerField('最大Company数', default=1, help_text='0の場合は無制限')
    max_ai_consultations_per_month = models.IntegerField('月間AI相談回数上限', default=10, help_text='0の場合は無制限')
    max_ocr_per_month = models.IntegerField('月間OCR読み込み回数上限', default=5, help_text='0の場合は無制限')
    api_limit = models.IntegerField('API利用上限数', default=30, help_text='FirmによるAPI利用上限数。上限まではSCOREのAPIを使用し、超えたらFirmのAPIキーを使用')
    
    # 機能フラグ
    cloud_storage_google_drive = models.BooleanField('Google Drive連携', default=False)
    cloud_storage_box = models.BooleanField('Box連携', default=False)
    cloud_storage_dropbox = models.BooleanField('Dropbox連携', default=False)
    cloud_storage_onedrive = models.BooleanField('OneDrive連携', default=False)
    
    report_basic = models.BooleanField('基本レポート', default=True)
    report_advanced = models.BooleanField('高度なレポート（PDF/Excel）', default=False)
    report_custom = models.BooleanField('カスタムレポート', default=False)
    
    marketing_support = models.BooleanField('マーケティング支援', default=False)
    marketing_support_seminar = models.IntegerField('セミナー共催回数/年', default=0)
    marketing_support_offline = models.IntegerField('オフ会実施支援回数/年', default=0)
    marketing_support_newsletter = models.BooleanField('メルマガ配信支援', default=False)
    
    api_integration = models.BooleanField('API連携', default=False)
    priority_support = models.BooleanField('優先サポート', default=False)
    profile_page_enhanced = models.BooleanField('プロフィールページ強化', default=False)
    
    # Stripe関連
    stripe_price_id_monthly = models.CharField('Stripe月額価格ID', max_length=255, blank=True)
    stripe_price_id_yearly = models.CharField('Stripe年額価格ID', max_length=255, blank=True)
    
    is_active = models.BooleanField('有効', default=True)
    order = models.IntegerField('表示順', default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Firmプラン'
        verbose_name_plural = 'Firmプラン'
        ordering = ['order', 'plan_type']
    
    def __str__(self):
        return self.name
    
    @property
    def is_unlimited_companies(self):
        """Company数が無制限かどうか"""
        return self.max_companies == 0
    
    @property
    def is_unlimited_ai_consultations(self):
        """AI相談回数が無制限かどうか"""
        return self.max_ai_consultations_per_month == 0
    
    @property
    def is_unlimited_ocr(self):
        """OCR回数が無制限かどうか"""
        return self.max_ocr_per_month == 0


class FirmSubscription(models.Model):
    """Firmのプラン契約情報"""
    STATUS_CHOICES = [
        ('trial', '試用期間中'),
        ('active', '有効'),
        ('past_due', '支払い遅延'),
        ('canceled', 'キャンセル済み'),
        ('unpaid', '未払い'),
        ('incomplete', '未完了'),
        ('incomplete_expired', '未完了（期限切れ）'),
    ]
    
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    firm = models.OneToOneField(Firm, on_delete=models.CASCADE, related_name='subscription', verbose_name='Firm')
    plan = models.ForeignKey(FirmPlan, on_delete=models.PROTECT, related_name='subscriptions', verbose_name='プラン')
    
    # 契約期間
    status = models.CharField('ステータス', max_length=20, choices=STATUS_CHOICES, default='trial')
    started_at = models.DateTimeField('開始日時', auto_now_add=True)
    trial_ends_at = models.DateTimeField('試用期間終了日時', null=True, blank=True)
    current_period_start = models.DateTimeField('現在の請求期間開始日時', null=True, blank=True)
    current_period_end = models.DateTimeField('現在の請求期間終了日時', null=True, blank=True)
    canceled_at = models.DateTimeField('キャンセル日時', null=True, blank=True)
    ends_at = models.DateTimeField('終了日時', null=True, blank=True)
    
    # Stripe関連
    stripe_customer_id = models.CharField('Stripe顧客ID', max_length=255, blank=True)
    stripe_subscription_id = models.CharField('StripeサブスクリプションID', max_length=255, blank=True)
    stripe_price_id = models.CharField('Stripe価格ID', max_length=255, blank=True)
    stripe_payment_method_id = models.CharField('Stripe支払い方法ID', max_length=255, blank=True)
    
    # Enterpriseプラン用の追加Company数
    additional_companies = models.IntegerField('追加Company数', default=0, help_text='Enterpriseプランの場合、10社ごとの追加分')
    
    # 年払い/月払い
    billing_cycle = models.CharField('請求サイクル', max_length=10, choices=[('monthly', '月払い'), ('yearly', '年払い')], default='monthly')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Firmサブスクリプション'
        verbose_name_plural = 'Firmサブスクリプション'
    
    def __str__(self):
        return f"{self.firm.name} - {self.plan.name}"
    
    @property
    def total_companies_allowed(self):
        """許可される総Company数"""
        if self.plan.is_unlimited_companies:
            return 0  # 無制限
        base = self.plan.max_companies
        if self.plan.plan_type == 'enterprise':
            # Enterpriseプランは基本10社 + 追加分
            return base + self.additional_companies
        return base
    
    @property
    def total_ai_consultations_allowed(self):
        """許可される総AI相談回数（月次）"""
        if self.plan.is_unlimited_ai_consultations:
            return 0  # 無制限
        base = self.plan.max_ai_consultations_per_month
        if self.plan.plan_type == 'enterprise':
            # Enterpriseプランは基本500回 + 追加分（10社あたり200回）
            additional = (self.additional_companies // 10) * 200
            return base + additional
        return base
    
    @property
    def total_ocr_allowed(self):
        """許可される総OCR回数（月次）"""
        if self.plan.is_unlimited_ocr:
            return 0  # 無制限
        base = self.plan.max_ocr_per_month
        if self.plan.plan_type == 'enterprise':
            # Enterpriseプランは基本250回 + 追加分（10社あたり100回）
            additional = (self.additional_companies // 10) * 100
            return base + additional
        return base
    
    @property
    def api_limit(self):
        """API利用上限数（Firmによる）"""
        return self.plan.api_limit
    
    @property
    def is_active_subscription(self):
        """有効なサブスクリプションかどうか"""
        return self.status in ['trial', 'active']
    
    @property
    def is_trial(self):
        """試用期間中かどうか"""
        return self.status == 'trial' and self.trial_ends_at and timezone.now() < self.trial_ends_at


class FirmUsageTracking(models.Model):
    """Firmの月次利用状況追跡"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    firm = models.ForeignKey(Firm, on_delete=models.CASCADE, related_name='usage_tracking', verbose_name='Firm')
    subscription = models.ForeignKey(FirmSubscription, on_delete=models.CASCADE, related_name='usage_tracking', verbose_name='サブスクリプション')
    
    # 追跡期間
    year = models.IntegerField('年')
    month = models.IntegerField('月', validators=[MinValueValidator(1), MaxValueValidator(12)])
    
    # 利用状況
    ai_consultation_count = models.IntegerField('AI相談回数', default=0)
    ai_consultation_tokens = models.IntegerField('AI相談トークン数', default=0, help_text='AI相談で使用した合計トークン数（将来の制限用、現状は記録のみ）')
    ocr_count = models.IntegerField('OCR読み込み回数', default=0)
    api_count = models.IntegerField('API利用回数', default=0, help_text='FirmによるAPI利用回数（上限まではSCOREのAPIを使用）')
    
    # リセットフラグ
    is_reset = models.BooleanField('リセット済み', default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Firm利用状況'
        verbose_name_plural = 'Firm利用状況'
        unique_together = ('firm', 'year', 'month')
        ordering = ['-year', '-month']
    
    def __str__(self):
        return f"{self.firm.name} - {self.year}年{self.month}月"
    
    @property
    def ai_consultation_remaining(self):
        """残りのAI相談回数"""
        if self.subscription.plan.is_unlimited_ai_consultations:
            return None  # 無制限
        total = self.subscription.total_ai_consultations_allowed
        return max(0, total - self.ai_consultation_count)
    
    @property
    def ocr_remaining(self):
        """残りのOCR回数"""
        if self.subscription.plan.is_unlimited_ocr:
            return None  # 無制限
        total = self.subscription.total_ocr_allowed
        return max(0, total - self.ocr_count)
    
    @property
    def ai_consultation_usage_percentage(self):
        """AI相談利用割合"""
        if self.subscription.plan.is_unlimited_ai_consultations:
            return None
        total = self.subscription.total_ai_consultations_allowed
        if total == 0:
            return 0
        return min(100, (self.ai_consultation_count / total) * 100)
    
    @property
    def ocr_usage_percentage(self):
        """OCR利用割合"""
        if self.subscription.plan.is_unlimited_ocr:
            return None
        total = self.subscription.total_ocr_allowed
        if total == 0:
            return 0
        return min(100, (self.ocr_count / total) * 100)
    
    @property
    def api_remaining(self):
        """残りのAPI利用回数（Firmによる）"""
        api_limit = self.subscription.api_limit
        if api_limit == 0:
            return None  # 無制限
        return max(0, api_limit - self.api_count)
    
    @property
    def api_usage_percentage(self):
        """API利用割合（Firmによる）"""
        api_limit = self.subscription.api_limit
        if api_limit == 0:
            return None
        if api_limit == 0:
            return 0
        return min(100, (self.api_count / api_limit) * 100)


class CompanyUsageTracking(models.Model):
    """Companyの月次利用状況追跡"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='usage_tracking', verbose_name='Company')
    firm = models.ForeignKey(Firm, on_delete=models.CASCADE, related_name='company_usage_tracking', verbose_name='Firm')
    
    # 追跡期間
    year = models.IntegerField('年')
    month = models.IntegerField('月', validators=[MinValueValidator(1), MaxValueValidator(12)])
    
    # 利用状況
    ai_consultation_count = models.IntegerField('AI相談回数', default=0)
    ocr_count = models.IntegerField('OCR読み込み回数', default=0)
    api_count = models.IntegerField('API利用回数', default=0, help_text='CompanyによるAPI利用回数')
    
    # リセットフラグ
    is_reset = models.BooleanField('リセット済み', default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Company利用状況'
        verbose_name_plural = 'Company利用状況'
        unique_together = ('company', 'firm', 'year', 'month')
        ordering = ['-year', '-month']
    
    def __str__(self):
        return f"{self.company.name} - {self.firm.name} - {self.year}年{self.month}月"


class SubscriptionHistory(models.Model):
    """プラン変更履歴"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    firm = models.ForeignKey(Firm, on_delete=models.CASCADE, related_name='subscription_history', verbose_name='Firm')
    subscription = models.ForeignKey(FirmSubscription, on_delete=models.CASCADE, related_name='history', verbose_name='サブスクリプション')
    
    # 変更前のプラン
    old_plan = models.ForeignKey(FirmPlan, on_delete=models.PROTECT, related_name='old_subscription_history', null=True, blank=True, verbose_name='変更前プラン')
    
    # 変更後のプラン
    new_plan = models.ForeignKey(FirmPlan, on_delete=models.PROTECT, related_name='new_subscription_history', verbose_name='変更後プラン')
    
    # 変更理由
    reason = models.TextField('変更理由', blank=True)
    
    # 変更日時
    changed_at = models.DateTimeField('変更日時', auto_now_add=True)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='変更者')
    
    class Meta:
        verbose_name = 'プラン変更履歴'
        verbose_name_plural = 'プラン変更履歴'
        ordering = ['-changed_at']
    
    def __str__(self):
        old_name = self.old_plan.name if self.old_plan else 'なし'
        return f"{self.firm.name} - {old_name} → {self.new_plan.name} ({self.changed_at.strftime('%Y-%m-%d')})"


class FirmNotification(models.Model):
    """Firm向け通知"""
    NOTIFICATION_TYPES = [
        ('plan_limit_warning', 'プラン制限警告'),
        ('payment_failed', '支払い失敗'),
        ('subscription_updated', 'サブスクリプション更新'),
        ('member_invited', 'メンバー招待'),
        ('plan_downgrade', 'プランダウングレード'),
        ('grace_period_ending', 'グレース期間終了間近'),
    ]
    
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    firm = models.ForeignKey(Firm, on_delete=models.CASCADE, related_name='notifications', verbose_name='Firm')
    notification_type = models.CharField('通知タイプ', max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField('タイトル', max_length=255)
    message = models.TextField('メッセージ')
    is_read = models.BooleanField('既読', default=False)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    read_at = models.DateTimeField('既読日時', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Firm通知'
        verbose_name_plural = 'Firm通知'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.firm.name} - {self.title}"


class FinancialInstitution(models.Model):
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=24)
    JBAcode = models.CharField(max_length=6, unique=True)  # ユニーク制を追加
    bank_category =  models.CharField(
        max_length=50,
        choices=(
            ('都市銀行', '都市銀行'),
            ('地方銀行', '地方銀行'),
            ('第二地銀協加盟行', '第二地銀協加盟行'),
            ('信金中央金庫', '信金中央金庫'),
            ('信用金庫', '信用金庫'),
            ('商工組合中央金庫', '商工組合中央金庫'),
            ('労働金庫連合会', '労働金庫連合会'),
            ('農林中央金庫', '農林中央金庫'),
            ('政府関係機関', '政府関係機関'),
            ('信用組合', '信用組合'),
            ('その他', 'その他'),
        ),
        default = '地方銀行',
    )
    def __str__(self):
        return self.short_name


class SecuredType(models.Model):
    name = models.CharField('保証区分', max_length=60)
    def __str__(self):
        return self.name

        
class Debt(models.Model):
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    financial_institution = models.ForeignKey(FinancialInstitution, on_delete=models.CASCADE, verbose_name="金融機関名")
    principal = models.IntegerField("借入元本", help_text="単位：円")
    issue_date = models.DateField("実行日")
    start_date = models.DateField("返済開始日")
    interest_rate = models.DecimalField("利息", max_digits=6, decimal_places=4, help_text="単位：%")
    monthly_repayment = models.IntegerField("月返済額", help_text="単位：円")
    adjusted_amount_first = models.IntegerField("初月調整額", default=0, help_text="単位：円。初月だけ返済額が異なる場合は通常月との差額を入力。差がなければゼロ。")
    adjusted_amount_last = models.IntegerField("最終月調整額", default=0, help_text="単位：円。最終月だけ返済額が異なる場合は通常月との差額を入力。差がなければゼロ。")
    is_securedby_management = models.BooleanField("経営者保証", default=False)
    is_collateraled = models.BooleanField("担保", default=False)
    is_rescheduled = models.BooleanField("リスケ", default=False, help_text="リスケした場合はチェックし、リスケ日とリスケ時点の残高を入力してください。")
    reschedule_date = models.DateField("リスケ日", null=True, blank=True)
    reschedule_balance = models.IntegerField("リスケ時点の残高", null=True, blank=True)
    memo_long = models.TextField("長文メモ", blank=True)
    memo_short = models.CharField("短文メモ", max_length=126, blank=True)
    is_nodisplay = models.BooleanField("非表示", default=False)
    secured_type = models.ForeignKey(SecuredType, on_delete=models.CASCADE, verbose_name="保証協会")
    document_url = models.URLField("返済予定表へのリンク", max_length=300, blank=True, null=True)
    document_url2 = models.URLField("金銭消費貸借契約書へのリンク", max_length=300, blank=True, null=True)
    document_url3 = models.URLField("保証協会資料・担保契約書などへのリンク", max_length=300, blank=True, null=True)
    document_url4 = models.URLField("その他資料へのリンク", max_length=300, blank=True, null=True)
    document_url_c1 = models.URLField("コンサル用資料リンク１", max_length=300, blank=True, null=True)
    document_url_c2 = models.URLField("コンサル用資料リンク２", max_length=300, blank=True, null=True)
    document_url_c3 = models.URLField("コンサル用資料リンク３", max_length=300, blank=True, null=True)

    @property
    def payment_terms(self):
        total_amount = self.principal + self.adjusted_amount_first + self.adjusted_amount_last
        months_difference = (self.start_date.year - self.issue_date.year) * 12 + (self.start_date.month - self.issue_date.month)
        return int(total_amount / self.monthly_repayment + months_difference)

    @property
    def remaining_months(self):
        payment_terms = self.payment_terms
        elapsed_months = self.elapsed_months
        return max(0, payment_terms - elapsed_months)

    @property
    def months_suspended(self):
        start_date = self.start_date
        issue_date = self.issue_date
        return (start_date.year - issue_date.year) * 12 + (start_date.month - issue_date.month)

    # 返済開始してからの月数
    # 返済が開始していない場合はマイナスの値を返す。
    @property
    def elapsed_months(self):
        start_date = datetime.combine(self.start_date, datetime.min.time())
        now = datetime.now()
        # if start_date > now:
        #     return 0
        return (now.year - start_date.year) * 12 + (now.month - start_date.month) + 1

    # 指定した月が経過した時点の残高（最終回は考慮せず）
    # 返済開始前の場合はmonthがマイナスの値となるが、projected_balanceは元本となる。
    def balance_after_months(self, months):
        if months == 0:
            projected_balance = self.principal
        else:
            projected_balance = self.principal - (self.monthly_repayment * months + self.adjusted_amount_first)
        projected_balance = min(self.principal, max(0, projected_balance))
        projected_interest_amount = projected_balance * self.interest_rate / 12 / 100
        return projected_balance, projected_interest_amount

    # 月々の残高
    @property
    def balances_monthly(self):
        start_month = self.elapsed_months
        return [self.balance_after_months(month)[0] for month in range(start_month, start_month + 12)]

    @property
    def interest_amount_monthly(self):
        """
        今後12ヶ月間の各月の月次利息額を計算して返す
        年利を12で割って月次利息率に変換し、各月の残高に掛けて計算
        """
        start_month = self.elapsed_months
        return [int(self.balance_after_months(month)[1]) for month in range(start_month, start_month + 12)]

    @property
    def fiscal_year_months(self):
        """
        現在の日付から次の決算月までの月数を計算します。
        決算月が現在の月より前にある場合は、次の年の決算月までの月数を計算します。
        """
        fiscal_month = self.company.fiscal_month
        current_date = datetime.now()
        current_month = current_date.month
        current_year = current_date.year
        
        if current_month <= fiscal_month:
            months_to_fy1 = fiscal_month - current_month
        else:
            months_to_fy1 = (12 - current_month) + fiscal_month
        
        return months_to_fy1

    @property
    def balance_fy1(self):
        months_to_fy1 = self.elapsed_months + self.fiscal_year_months
        return self.balance_after_months(months_to_fy1)[0]

    @property
    def balance_fy2(self):
        months_to_fy2 = self.elapsed_months + self.fiscal_year_months + 12
        return self.balance_after_months(months_to_fy2)[0]

    @property
    def balance_fy3(self):
        months_to_fy3 = self.elapsed_months + self.fiscal_year_months + 24
        return self.balance_after_months(months_to_fy3)[0]

    @property
    def balance_fy4(self):
        months_to_fy4 = self.elapsed_months + self.fiscal_year_months + 36
        return self.balance_after_months(months_to_fy4)[0]

    @property
    def balance_fy5(self):
        months_to_fy5 = self.elapsed_months + self.fiscal_year_months + 48
        return self.balance_after_months(months_to_fy5)[0]

    @property
    def balances_fiscalyears(self):
        return [self.balance_fy1, self.balance_fy2, self.balance_fy3, self.balance_fy4, self.balance_fy5]

    # バリデーション
    def clean(self):
        super().clean()
        if self.issue_date and self.start_date and self.issue_date > self.start_date:
            raise ValidationError("実行日は返済開始日以前でなければなりません。")
        if self.monthly_repayment <= 0:
            raise ValidationError({
                'monthly_repayment': "月返済額は正の数でなければなりません。"
            })
        if self.principal <= 0:
            raise ValidationError({
                'principal': "借入元本は正の数でなければなりません。"
            })
        # 初月の返済額（adjusted_amount_first + monthly_repayment）が正の数か確認
        total_first_repayment = self.adjusted_amount_first + self.monthly_repayment
        if total_first_repayment <= 0:
            raise ValidationError({
                'adjusted_amount_first': "初月調整額と月返済額の合計は正の数でなければなりません。"
            })
        # 最終月の返済額（adjusted_amount_last + monthly_repayment）が正の数か確認
        total_last_repayment = self.adjusted_amount_last + self.monthly_repayment
        if total_last_repayment <= 0:
            raise ValidationError({
                'adjusted_amount_last': "最終月調整額と月返済額の合計は正の数でなければなりません。"
            })


    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.company.name} - {self.issue_date} - ¥{self.principal:,}"


class MeetingMinutes(models.Model):
    CATEGORY_CHOICES = [
        ('meeting', '打ち合わせ'),
        ('shareholders', '株主総会'),
        ('board', '取締役会'),
        ('management', '経営会議/執行役員会'),
        ('other', 'その他'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    meeting_date = models.DateField("ミーティング日")
    category = models.CharField("カテゴリ", max_length=20, choices=CATEGORY_CHOICES, default='meeting')
    created_at = models.DateTimeField("作成日", auto_now_add=True)
    updated_at = models.DateTimeField("更新日", auto_now=True)
    notes = models.TextField("ミーティングノート")

    def __str__(self):
        return F"{self.company.name}"


class BlogCategory(models.Model):
    """ブログカテゴリー"""
    name = models.CharField(max_length=50, unique=True, verbose_name="カテゴリー名")
    slug = models.SlugField(max_length=50, unique=True, verbose_name="スラッグ")
    description = models.TextField(blank=True, verbose_name="説明")
    order = models.IntegerField(default=0, verbose_name="表示順")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")
    
    class Meta:
        verbose_name = "ブログカテゴリー"
        verbose_name_plural = "ブログカテゴリー"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class Blog(models.Model):
    title = models.CharField(max_length=255, verbose_name="タイトル")
    post_date = models.DateField("投稿日")
    article = models.TextField(verbose_name="本文")
    is_draft = models.BooleanField(default=False, verbose_name="下書き")
    written_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="作成者")
    categories = models.ManyToManyField(
        BlogCategory,
        blank=True,
        related_name='blogs',
        verbose_name="カテゴリー"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")
    
    class Meta:
        verbose_name = "ブログ"
        verbose_name_plural = "ブログ"
        ordering = ['-post_date', '-created_at']
        indexes = [
            models.Index(fields=['-post_date']),
            models.Index(fields=['is_draft']),
        ]
    
    def __str__(self):
        return self.title


class FiscalSummary_Year(models.Model):
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='fiscal_summary_years')
    year = models.IntegerField("年度", validators=[MinValueValidator(2000), MaxValueValidator(2100)])
    version = models.IntegerField("バージョン", default=1)
    is_draft = models.BooleanField("下書きモード", default=False)
    is_budget = models.BooleanField("予算", default=False)

    # BS情報
    cash_and_deposits = models.IntegerField("現金及び預金合計（千円）", default=0)
    accounts_receivable = models.IntegerField("売上債権合計（千円）", default=0)
    inventory = models.IntegerField("棚卸資産合計（千円）", default=0)
    short_term_loans_receivable = models.IntegerField("短期貸付金（千円）", default=0)
    other_current_assets = models.IntegerField("その他の流動資産（千円）", default=0)
    total_current_assets = models.IntegerField("流動資産合計（千円）", default=0)
    land = models.IntegerField("土地（千円）", default=0, validators=[MinValueValidator(0)])
    buildings = models.IntegerField("建物及び附属設備（千円）", default=0, validators=[MinValueValidator(0)])
    machinery_equipment = models.IntegerField("機械及び装置（千円）", default=0, validators=[MinValueValidator(0)])
    vehicles = models.IntegerField("車両運搬具（千円）", default=0, validators=[MinValueValidator(0)])
    accumulated_depreciation = models.IntegerField("有形固定資産の減価償却累計額（千円）", default=0, help_text="有形固定資産の取得原価から減価償却累計額を引いた額。直接法の場合はゼロ。", validators=[MaxValueValidator(0)])
    other_tangible_fixed_assets = models.IntegerField("その他の有形固定資産（千円）", default=0)
    total_tangible_fixed_assets = models.IntegerField("有形固定資産合計（千円）", default=0)
    goodwill = models.IntegerField("のれん（千円）", default=0)
    other_intangible_assets = models.IntegerField("その他の無形固定資産（千円）", default=0)
    total_intangible_assets = models.IntegerField("無形固定資産合計（千円）", default=0)
    long_term_loans_receivable = models.IntegerField("長期貸付金（千円）", default=0)
    investment_other_assets = models.IntegerField("投資その他の資産（千円）", default=0)
    deferred_assets = models.IntegerField("繰延資産合計（千円）", default=0)
    total_fixed_assets = models.IntegerField("固定資産合計（千円）", default=0)
    total_assets = models.IntegerField("資産の部合計（千円）", default=0, validators=[MinValueValidator(0)])
    accounts_payable = models.IntegerField("仕入債務合計（千円）", default=0)
    short_term_loans_payable = models.IntegerField("短期借入金（千円）", default=0)
    other_current_liabilities = models.IntegerField("その他の流動負債（千円）", default=0)
    total_current_liabilities = models.IntegerField("流動負債合計（千円）", default=0)
    long_term_loans_payable = models.IntegerField("長期借入金（千円）", default=0)
    other_long_term_liabilities = models.IntegerField("その他の固定負債（千円）", default=0)
    total_long_term_liabilities = models.IntegerField("固定負債合計（千円）", default=0)
    total_liabilities = models.IntegerField("負債の部合計（千円）", default=0, validators=[MinValueValidator(0)])
    total_stakeholder_equity = models.IntegerField("株主資本合計（千円）", default=0)
    capital_stock = models.IntegerField("資本金合計（千円）", default=0, validators=[MinValueValidator(0)])
    capital_surplus = models.IntegerField("資本剰余金合計（千円）", default=0, validators=[MinValueValidator(0)])
    retained_earnings = models.IntegerField("利益剰余金合計（千円）", default=0)
    valuation_and_translation_adjustment = models.IntegerField("評価・換算差額合計（千円）", default=0)
    new_shares_reserve = models.IntegerField("新株予約権合計（千円）", default=0)
    total_net_assets = models.IntegerField("純資産の部合計（千円）", default=0)

    # BS特殊情報
    directors_loan = models.IntegerField("役員貸付・借入金（千円）", default=0, help_text="貸付ならプラス、借入ならマイナス")

    # PL情報
    sales = models.IntegerField("売上高（千円）", default=0)
    gross_profit = models.IntegerField("粗利益（千円）", default=0)
    depreciation_cogs = models.IntegerField("減価償却費（売上原価）（千円）", default=0)
    depreciation_expense = models.IntegerField("減価償却額（販管費）（千円）", default=0)
    other_amortization_expense = models.IntegerField("その他の償却額（販管費）（千円）", default=0)
    directors_compensation = models.IntegerField("役員報酬（千円）", default=0)
    payroll_expense = models.IntegerField("給与・雑給（千円）", default=0)
    operating_profit = models.IntegerField("営業利益（千円）", default=0)
    non_operating_amortization_expense = models.IntegerField("営業外で計上された償却費（千円）", default=0)
    interest_expense = models.IntegerField("支払利息（千円）", default=0)
    other_income = models.IntegerField("営業外収益合計（千円）", default=0)
    other_loss = models.IntegerField("営業外費用合計（千円）", default=0)
    ordinary_profit = models.IntegerField("経常利益（千円）", default=0)
    extraordinary_income = models.IntegerField("特別利益合計（千円）", default=0)
    extraordinary_loss = models.IntegerField("特別損失合計（千円）", default=0)
    income_taxes = models.IntegerField("法人税等（千円）", default=0)
    net_profit = models.IntegerField("当期純利益（千円）", default=0)

    # 税務情報
    tax_loss_carryforward = models.IntegerField("繰越欠損金（千円）", default=0, validators=[MinValueValidator(0)])
    number_of_employees_EOY = models.IntegerField("期末従業員数", default=0, validators=[MinValueValidator(0)])
    issued_shares_EOY = models.IntegerField("期末発行済み株式数（株）", default=0, validators=[MinValueValidator(0)])
    
    # 決算留意事項
    financial_statement_notes = models.TextField("決算留意事項", blank=True)
    document_url = models.URLField("クラウドストレージへのリンク", max_length=300, blank=True, null=True)

    # 財務スコア情報
    score_sales_growth_rate = models.IntegerField("売上高増加率", validators=[MinValueValidator(0), MaxValueValidator(5)], default=0, null=True, blank=True)
    score_operating_profit_margin = models.IntegerField("営業利益率", validators=[MinValueValidator(0), MaxValueValidator(5)], default=0, null=True, blank=True)
    score_labor_productivity = models.IntegerField("労働生産性", validators=[MinValueValidator(0), MaxValueValidator(5)], default=0, null=True, blank=True)
    score_EBITDA_interest_bearing_debt_ratio = models.IntegerField("EBITDA有利子負債倍率", validators=[MinValueValidator(0), MaxValueValidator(5)], default=0, null=True, blank=True)
    score_operating_working_capital_turnover_period = models.IntegerField("営業運転資本回転期間", validators=[MinValueValidator(0), MaxValueValidator(5)], default=0, null=True, blank=True)
    score_equity_ratio = models.IntegerField("自己資本比率", validators=[MinValueValidator(0), MaxValueValidator(5)], default=0, null=True, blank=True)

    @property
    def current_ratio(self):
        """流動比率"""
        if self.total_current_liabilities != 0:
            ratio = (self.total_current_assets / self.total_current_liabilities) * 100
            return Decimal(ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return Decimal('0.00')

    @property
    def previous_year_sales(self):
        previous_year_summary = FiscalSummary_Year.objects.filter(
            company=self.company,
            year=self.year - 1
        ).order_by('-version').first()
        if previous_year_summary:
            return previous_year_summary.sales
        else:
            return None

    @property
    def operating_profit_margin(self):
        """営業利益率 = 営業利益 ÷ 売上高 × 100 (%)"""
        if self.sales != 0:
            ratio = (self.operating_profit / self.sales) * 100
            return Decimal(ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return Decimal('0.00')

    @property
    def sales_growth_rate(self):
        """売上高増加率 = （当期売上高 - 前期売上高）÷ 前期売上高 × 100 (%)"""
        previous_sales = self.get_previous_year_sales()
        if previous_sales and previous_sales != 0:
            growth_rate = ((self.sales - previous_sales) / previous_sales) * 100
            return Decimal(growth_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return None

    @property
    def labor_productivity(self):
        """
        労働生産性 = 付加価値 ÷ 従業員数
        付加価値 = 営業利益 + 人件費 + 減価償却費 + 支払利息
        人件費 = 給与・雑給 + 役員報酬
        減価償却費 = 売上原価の減価償却費 + 販管費の減価償却費 + その他の償却費 + 営業外償却費
        """
        labor_costs = self.payroll_expense + self.directors_compensation
        depreciation_amortization = (
            self.depreciation_cogs +
            self.depreciation_expense +
            self.other_amortization_expense +
            self.non_operating_amortization_expense
        )
        value_added = self.operating_profit + labor_costs + depreciation_amortization + self.interest_expense

        if self.number_of_employees_EOY != 0:
            productivity = value_added / self.number_of_employees_EOY
            return Decimal(productivity).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return None

    @property
    def EBITDA(self):
        """EBITDA = 営業利益 + 減価償却費"""
        depreciation_amortization = (
            self.depreciation_cogs +
            self.depreciation_expense +
            self.other_amortization_expense +
            self.non_operating_amortization_expense
        )
        ebitda = self.operating_profit + depreciation_amortization
        return ebitda

    @property
    def EBITDA_interest_bearing_debt_ratio(self):
        """EBITDA有利子負債倍率 = 有利子負債 ÷ EBITDA"""
        interest_bearing_debt = self.short_term_loans_payable + self.long_term_loans_payable
        ebitda = self.EBITDA
        # EBITDAが0以上の場合のみ計算する
        if ebitda > 0:
            ratio = interest_bearing_debt / ebitda
            return Decimal(ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return None

    @property
    def operating_working_capital_turnover_period(self):
        """営業運転資本回転期間（月）= 営業運転資本 ÷ 売上高 × 12 (ヶ月)"""
        operating_working_capital = self.accounts_receivable + self.inventory - self.accounts_payable

        if self.sales > 0:
            period = (operating_working_capital / self.sales) * 12
            return Decimal(period).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return None

    @property
    def equity_ratio(self):
        """自己資本比率 = 純資産 ÷ 総資産 × 100 (%)"""
        # 純資産がマイナスの場合はマイナス値を返す
        if self.total_assets > 0:
            ratio = (self.total_net_assets / self.total_assets) * 100
            return Decimal(ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return Decimal('0.00')

    @property
    def ROA(self):
        """総資本経常利益率（ROA）= 経常利益 ÷ 総資産 × 100 (%)"""
        if self.total_assets != 0:
            ratio = (self.ordinary_profit / self.total_assets) * 100
            return Decimal(ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return Decimal('0.00')

    @property
    def gross_profit_margin(self):
        """売上総利益率 = 売上総利益 ÷ 売上高 × 100 (%)"""
        if self.sales != 0:
            ratio = (self.gross_profit / self.sales) * 100
            return Decimal(ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return Decimal('0.00')

    @property
    def fixed_ratio(self):
        """固定比率 = 固定資産 ÷ 自己資本 × 100 (%)"""
        if self.total_net_assets != 0:
            ratio = (self.total_fixed_assets / self.total_net_assets) * 100
            return Decimal(ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return None

    @property
    def fixed_long_term_adequacy_ratio(self):
        """固定長期適合率 = 固定資産 ÷ （自己資本 + 固定負債）× 100 (%)"""
        long_term_capital = self.total_net_assets + self.total_long_term_liabilities
        if long_term_capital != 0:
            ratio = (self.total_fixed_assets / long_term_capital) * 100
            return Decimal(ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return None

    @property
    def quick_ratio(self):
        """当座比率 = （流動資産 - 棚卸資産）÷ 流動負債 × 100 (%)"""
        if self.total_current_liabilities != 0:
            quick_assets = self.total_current_assets - self.inventory
            ratio = (quick_assets / self.total_current_liabilities) * 100
            return Decimal(ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return Decimal('0.00')

    @property
    def ROE(self):
        """自己資本利益率（ROE）= 経常利益 ÷ 純資産 × 100 (%)"""
        if self.total_net_assets != 0:
            ratio = (self.ordinary_profit / self.total_net_assets) * 100
            return Decimal(ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return None

    @property
    def total_asset_turnover(self):
        """総資産回転率 = 売上高 ÷ 総資産"""
        if self.total_assets != 0:
            turnover = self.sales / self.total_assets
            return Decimal(turnover).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return Decimal('0.00')

    @property
    def ordinary_profit_rate(self):
        """経常利益率 = 経常利益 ÷ 売上高 × 100 (%)"""
        if self.sales != 0:
            ratio = (self.ordinary_profit / self.sales) * 100
            return Decimal(ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return Decimal('0.00')

    @property
    def debt_to_equity_ratio(self):
        """負債資本比率 = 総負債 ÷ 純資産"""
        if self.total_net_assets != 0:
            ratio = self.total_liabilities / self.total_net_assets
            return Decimal(ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return None

    @property
    def inventory_turnover_period(self):
        """在庫回転期間（月）= 棚卸資産 ÷ 売上高 × 12 (ヶ月)"""
        if self.sales > 0:
            period = (self.inventory / self.sales) * 12
            return Decimal(period).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return None

    @property
    def accounts_receivable_turnover_period(self):
        """売上債権回転期間（月）= 売上債権 ÷ 売上高 × 12 (ヶ月)"""
        if self.sales > 0:
            period = (self.accounts_receivable / self.sales) * 12
            return Decimal(period).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return None

    # 前年売上高を取得するメソッド
    def get_previous_year_sales(self):
        previous_year_summary = FiscalSummary_Year.objects.filter(
            company=self.company,
            year=self.year - 1
        ).order_by('-version').first()
        if previous_year_summary:
            return previous_year_summary.sales
        return None

    class Meta:
        unique_together = ('company', 'year', 'is_budget')
        verbose_name = '年次決算情報'
        verbose_name_plural = '年次決算情報'

    def __str__(self):
        budget_label = "予算" if self.is_budget else "実績"
        return f"{self.company.name} - {self.year}年 ({budget_label})"
        

class FiscalSummary_Month(models.Model):
    fiscal_summary_year = models.ForeignKey(FiscalSummary_Year, on_delete=models.PROTECT, related_name='monthly_summaries')
    period = models.IntegerField("月度", validators=[MinValueValidator(1), MaxValueValidator(13)])
    sales = models.DecimalField("売上高", max_digits=12, decimal_places=2)
    gross_profit = models.DecimalField("粗利益", max_digits=12, decimal_places=2)
    operating_profit = models.DecimalField("営業利益", max_digits=12, decimal_places=2)
    ordinary_profit = models.DecimalField("経常利益", max_digits=12, decimal_places=2)
    is_budget = models.BooleanField("予算", default=False)

    @property
    def gross_profit_rate(self):
        if self.sales > 0:
            return round(float(self.gross_profit) / float(self.sales) * 100, 3)
        return 0.0     

    @property
    def operating_profit_rate(self):
        if self.sales > 0:
            return round(float(self.operating_profit) / float(self.sales) * 100, 3)
        return 0.0

    @property
    def ordinary_profit_rate(self):
        if self.sales > 0:
            return round(float(self.ordinary_profit) / float(self.sales) * 100, 3)
        return 0.0

    class Meta:
        unique_together = ('fiscal_summary_year', 'period', 'is_budget')
        verbose_name = '月次決算情報'
        verbose_name_plural = '月次決算情報'

    def __str__(self):
        return f"{self.fiscal_summary_year.company.name} - {self.fiscal_summary_year.year} - 月{self.period}"

    def clean(self):
        if self.period < 1 or self.period > 13:
            raise ValidationError("月度は1から13の間でなければなりません。")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

# 株式発行 Captableの機能
class Stakeholder_name(models.Model):
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    name = models.CharField("株主名", max_length=255)
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    is_representative = models.BooleanField("代表取締役", default=True)
    is_board_member = models.BooleanField("取締役", default=True)
    is_related_person = models.BooleanField("代表者の家族", default=True)
    is_employee = models.BooleanField("従業員", default=False)
    memo = models.TextField("備考", blank=True)

    def __str__(self):
        return self.name

class StockEvent(models.Model):
    fiscal_summary_year = models.ForeignKey(FiscalSummary_Year, on_delete=models.PROTECT, related_name='stock_events')
    name = models.CharField("株式イベント名", max_length=255)
    event_date = models.DateField("日付")
    event_type = models.CharField("種別", max_length=255)
    memo = models.TextField("備考", blank=True)

    def __str__(self):
        return f"{self.fiscal_summary_year.company.name} - {self.fiscal_summary_year.year} - {self.name}"

class StockEventLine(models.Model):
    stock_event = models.ForeignKey(StockEvent, on_delete=models.CASCADE, related_name='details')
    stakeholder = models.ForeignKey(Stakeholder_name, on_delete=models.PROTECT)
    share_quantity = models.IntegerField("株式数", default=0)
    share_type = models.CharField("株式種類", max_length=255)
    acquisition_price = models.IntegerField("取得単価", default=0)
    memo = models.TextField("備考", blank=True)

    def __str__(self):
        return f"{self.stock_event.fiscal_summary_year.company.name} - {self.stock_event.fiscal_summary_year.year} - {self.stock_event.name} - {self.stakeholder.name}"

# 経営指標用の業界大分類
class IndustryClassification(models.Model):
    name = models.CharField("業界名", max_length=255)
    code = models.CharField("分類コード", max_length=7, unique=True)
    memo = models.TextField("備考", blank=True)

    def __str__(self):
        return self.name

# 経営指標用の業界小分類
class IndustrySubClassification(models.Model):
    industry_classification = models.ForeignKey(IndustryClassification, on_delete=models.CASCADE)
    name = models.CharField("業界小分類名", max_length=255)
    code = models.CharField("小分類コード", max_length=7, unique=True)
    memo = models.TextField("備考", blank=True)

    def __str__(self):
        return self.name


class IndustryIndicator(models.Model):
    name = models.CharField("指標名", max_length=255)
    label = models.CharField("日本語ラベル", max_length=255, null=True, blank=True)
    memo = models.TextField("備考", blank=True)

    def __str__(self):
        return self.name

# 業種別経営指標の値を持つモデル
class IndustryBenchmark(models.Model):
    year = models.IntegerField("年度", validators=[MinValueValidator(1900), MaxValueValidator(2100)])
    industry_classification = models.ForeignKey(IndustryClassification, on_delete=models.CASCADE)
    industry_subclassification = models.ForeignKey(IndustrySubClassification, on_delete=models.CASCADE)
    COMPANY_SIZE_CHOICES = [
        ('s', '小規模'),
        ('m', '中規模'),
        ('l', '大規模'),
    ]
    company_size = models.CharField(
        "Company Size",
        max_length=10,
        choices=COMPANY_SIZE_CHOICES,
        default='s',
    )
    indicator = models.ForeignKey(IndustryIndicator, on_delete=models.CASCADE)
    median = models.DecimalField("中央値", max_digits=12, decimal_places=2)
    standard_deviation = models.DecimalField("標準偏差", max_digits=12, decimal_places=2)
    range_iv = models.DecimalField("iv", max_digits=12, decimal_places=2)
    range_iii = models.DecimalField("iii", max_digits=12, decimal_places=2)
    range_ii = models.DecimalField("ii", max_digits=12, decimal_places=2)
    range_i = models.DecimalField("i", max_digits=12, decimal_places=2)
    memo = models.TextField("備考", blank=True)

    def __str__(self):
        return self.indicator.name

    class Meta:
        unique_together = ('year', 'industry_classification', 'industry_subclassification', 'company_size', 'indicator')
        verbose_name = '業界別経営指標'
        verbose_name_plural = '業界別経営指標'


class TechnicalTerm(models.Model):
    name = models.CharField("用語名", max_length=255)
    term_category =  models.CharField(
        max_length=50,
        choices=(
            ('安全性', '安全性'),
            ('収益性', '収益性'),
            ('生産性', '生産性'),
            ('成長性', '成長性'),
            ('効率性', '効率性'),
            ('その他', 'その他'),
        ),
        default = 'その他',
    )
    description1 = models.TextField("説明", blank=True)
    description2 = models.TextField("目安", blank=True)
    description3 = models.TextField("計算式", blank=True)

    def __str__(self):
        return self.name

class Help(models.Model):
    title = models.CharField("タイトル", max_length=255)
    category =  models.CharField(
        max_length=50,
        choices=(
            ('ai_usage', 'AIの活用'),
            ('data_entry', 'データ登録'),
            ('login', 'ログイン'),
            ('others', 'その他'),
        ),
        default = 'others',
    )

    content = models.TextField("内容")

    def __str__(self):
        return self.title


class Manual(models.Model):
    """マニュアルモデル - 操作手順をステップバイステップで説明"""
    USER_TYPE_CHOICES = [
        ('company_admin', '会社ユーザー（管理者）'),
        ('company_user', '会社ユーザー（一般）'),
        ('firm_admin', 'Firmユーザー（管理者）'),
        ('firm_user', 'Firmユーザー（一般）'),
    ]
    
    CATEGORY_CHOICES = [
        ('getting_started', 'はじめに'),
        ('dashboard', 'ダッシュボード'),
        ('financial_management', '財務管理'),
        ('budget_management', '予算管理'),
        ('debt_management', '借入管理'),
        ('ai_consultation', 'AI相談'),
        ('data_import', 'データ取り込み'),
        ('other_data', 'その他データ'),
        ('settings', '設定'),
    ]
    
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    user_type = models.CharField(
        "ユーザータイプ",
        max_length=20,
        choices=USER_TYPE_CHOICES,
        help_text="このマニュアルが対象とするユーザータイプ"
    )
    category = models.CharField(
        "カテゴリ",
        max_length=50,
        choices=CATEGORY_CHOICES,
        help_text="マニュアルのカテゴリ"
    )
    order = models.IntegerField(
        "表示順序",
        default=0,
        help_text="同じカテゴリ内での表示順序（小さい順）"
    )
    title = models.CharField("タイトル", max_length=255)
    content = models.TextField("内容", help_text="Markdown形式で記述可能")
    is_active = models.BooleanField("有効", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'マニュアル'
        verbose_name_plural = 'マニュアル'
        ordering = ['user_type', 'category', 'order', 'id']
        indexes = [
            models.Index(fields=['user_type', 'category', 'order']),
        ]
    
    def __str__(self):
        return f"{self.get_user_type_display()} - {self.get_category_display()} - {self.title}"


# AI相談機能関連のモデル
class AIConsultationType(models.Model):
    """相談タイプ（財務、補助金・助成金、税務、法律など）"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    name = models.CharField(max_length=50, unique=True, verbose_name="相談タイプ名")  # "財務相談"
    description = models.TextField(verbose_name="説明")  # 相談タイプの説明
    is_active = models.BooleanField(default=True, verbose_name="有効")
    order = models.IntegerField(default=0, verbose_name="表示順序")  # 表示順序
    color = models.CharField(max_length=7, default="#007bff", verbose_name="カラー")  # カードの色
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'AI相談タイプ'
        verbose_name_plural = 'AI相談タイプ'
    
    def __str__(self):
        return self.name


class AIConsultationFAQ(models.Model):
    """AI相談のよくある質問"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    consultation_type = models.ForeignKey(
        AIConsultationType,
        on_delete=models.CASCADE,
        related_name='faqs',
        verbose_name="相談タイプ"
    )
    question = models.CharField(max_length=200, verbose_name="質問")
    script = models.TextField(verbose_name="スクリプト", blank=True, null=True, help_text="この質問専用のシステムプロンプト。空の場合は相談タイプのデフォルトスクリプトを使用します。")
    order = models.IntegerField(default=0, verbose_name="表示順序")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['consultation_type', 'order', 'question']
        verbose_name = 'AI相談よくある質問'
        verbose_name_plural = 'AI相談よくある質問'
    
    def __str__(self):
        return f"{self.consultation_type.name}: {self.question}"


class AIConsultationScript(models.Model):
    """AI相談スクリプト（システム全体用・管理者が編集）"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    consultation_type = models.ForeignKey(
        AIConsultationType,
        on_delete=models.CASCADE,
        related_name='system_scripts',
        verbose_name="相談タイプ"
    )
    name = models.CharField(max_length=100, verbose_name="スクリプト名")  # スクリプト名
    system_instruction = models.TextField(verbose_name="システムプロンプト")  # システムプロンプト
    default_prompt_template = models.TextField(verbose_name="プロンプトテンプレート")  # デフォルトプロンプトテンプレート
    is_default = models.BooleanField(default=True, verbose_name="デフォルト")  # デフォルトスクリプトか
    is_active = models.BooleanField(default=True, verbose_name="有効")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="作成者")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'AI相談スクリプト（システム）'
        verbose_name_plural = 'AI相談スクリプト（システム）'
        unique_together = [['consultation_type', 'is_default']]
    
    def __str__(self):
        return f"{self.consultation_type.name} - {self.name}"


class UserAIConsultationScript(models.Model):
    """ユーザー独自のAI相談スクリプト"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ai_scripts',
        verbose_name="ユーザー"
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='ai_scripts',
        verbose_name="Company",
        null=True,
        blank=True,
        help_text="このスクリプトが紐づくCompany。Companyに属するUserはこのスクリプトを共有できます。"
    )
    consultation_type = models.ForeignKey(
        AIConsultationType,
        on_delete=models.CASCADE,
        related_name='user_scripts',
        verbose_name="相談タイプ"
    )
    name = models.CharField(max_length=100, verbose_name="スクリプト名")  # スクリプト名
    system_instruction = models.TextField(verbose_name="システムプロンプト")  # システムプロンプト
    prompt_template = models.TextField(verbose_name="プロンプトテンプレート")  # プロンプトテンプレート
    is_active = models.BooleanField(default=True, verbose_name="有効")
    is_default = models.BooleanField(default=False, verbose_name="デフォルト")  # このタイプのデフォルトか
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'AI相談スクリプト（ユーザー）'
        verbose_name_plural = 'AI相談スクリプト（ユーザー）'
        unique_together = [['user', 'company', 'consultation_type', 'is_default']]
    
    def __str__(self):
        company_name = self.company.name if self.company else "個人"
        return f"{self.user.username} - {company_name} - {self.consultation_type.name} - {self.name}"


class MeetingMinutesAIScript(models.Model):
    """AI議事録生成スクリプト（システム全体用・管理者が編集）"""
    MEETING_TYPE_CHOICES = [
        ('shareholders_meeting', '株主総会'),
        ('board_of_directors', '取締役会'),
        ('management_committee', '経営会議 / 執行役員会'),
    ]
    
    MEETING_CATEGORY_CHOICES = [
        ('regular', '定時'),
        ('extraordinary', '臨時'),
    ]
    
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    meeting_type = models.CharField('会議体', max_length=50, choices=MEETING_TYPE_CHOICES)
    meeting_category = models.CharField('開催種別', max_length=50, choices=MEETING_CATEGORY_CHOICES)
    agenda = models.CharField('議題', max_length=100, help_text="議題のキー（financial_approval, officer_election等）")
    name = models.CharField('スクリプト名', max_length=100)
    system_instruction = models.TextField('システムプロンプト', help_text="AIの役割や振る舞いを定義するシステムプロンプト")
    prompt_template = models.TextField('プロンプトテンプレート', help_text="議事録生成用のプロンプトテンプレート。利用可能な変数: {meeting_type_name}, {meeting_category_name}, {agenda_name}, {agenda_description}, {company_name}, {additional_info}")
    is_default = models.BooleanField('デフォルト', default=True, help_text="この組み合わせのデフォルトスクリプトか")
    is_active = models.BooleanField('有効', default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="作成者")
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = 'AI議事録生成スクリプト'
        verbose_name_plural = 'AI議事録生成スクリプト'
        unique_together = [['meeting_type', 'meeting_category', 'agenda', 'is_default']]
        ordering = ['meeting_type', 'meeting_category', 'agenda', '-is_default', 'name']
    
    def __str__(self):
        return f"{self.get_meeting_type_display()} - {self.get_meeting_category_display()} - {self.agenda} - {self.name}"


class CloudStorageSetting(models.Model):
    """クラウドストレージ設定（ユーザー×Companyごと）"""
    STORAGE_CHOICES = [
        ('google_drive', 'Google Drive'),
        ('box', 'Box'),
        ('dropbox', 'Dropbox'),
        ('onedrive', 'OneDrive'),
    ]
    
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='cloud_storage_settings',
        verbose_name="ユーザー"
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='cloud_storage_settings',
        verbose_name="Company"
    )
    storage_type = models.CharField(
        "ストレージタイプ",
        max_length=20,
        choices=STORAGE_CHOICES,
        null=True,
        blank=True
    )
    access_token = models.TextField("アクセストークン", blank=True, help_text="OAuth2アクセストークン（暗号化推奨）")
    refresh_token = models.TextField("リフレッシュトークン", blank=True, help_text="OAuth2リフレッシュトークン（暗号化推奨）")
    token_expires_at = models.DateTimeField("トークン有効期限", null=True, blank=True)
    root_folder_id = models.CharField("ルートフォルダID", max_length=255, blank=True, help_text="ストレージ内のルートフォルダID")
    is_active = models.BooleanField("有効", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'クラウドストレージ設定'
        verbose_name_plural = 'クラウドストレージ設定'
        unique_together = ('user', 'company')
    
    def __str__(self):
        return f"{self.user.username} - {self.company.name} - {self.get_storage_type_display() or '未設定'}"


class DocumentFolder(models.Model):
    """ドキュメントフォルダ構造（システム規定）"""
    FOLDER_TYPES = [
        ('financial_statement', '決算書'),
        ('trial_balance', '試算表'),
        ('loan_contract', '金銭消費貸借契約書'),
        ('contract', '契約書'),
    ]
    
    SUBFOLDER_TYPES = [
        ('balance_sheet', '貸借対照表'),
        ('profit_loss', '損益計算書'),
        ('monthly_pl', '月次推移損益計算書'),
        ('department_pl', '部門別損益計算書'),
        ('lease', 'リース契約書'),
        ('sales', '商品売買契約'),
        ('rental', '賃貸借契約'),
    ]
    
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    folder_type = models.CharField("フォルダタイプ", max_length=30, choices=FOLDER_TYPES)
    subfolder_type = models.CharField("サブフォルダタイプ", max_length=30, choices=SUBFOLDER_TYPES, blank=True)
    name = models.CharField("フォルダ名", max_length=100)
    order = models.IntegerField("表示順", default=0)
    is_active = models.BooleanField("有効", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'ドキュメントフォルダ'
        verbose_name_plural = 'ドキュメントフォルダ'
        unique_together = ('folder_type', 'subfolder_type')
        ordering = ['folder_type', 'order', 'subfolder_type']
    
    def __str__(self):
        if self.subfolder_type:
            return f"{self.get_folder_type_display()} / {self.get_subfolder_type_display()}"
        return self.get_folder_type_display()


class UploadedDocument(models.Model):
    """アップロードされたドキュメント"""
    DOCUMENT_TYPES = [
        ('financial_statement', '決算書'),
        ('trial_balance', '試算表'),
        ('loan_contract', '金銭消費貸借契約書'),
        ('contract', '契約書'),
        ('other', 'その他'),
    ]
    
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_documents',
        verbose_name="ユーザー"
    )
    company = models.ForeignKey(
        'Company',
        on_delete=models.CASCADE,
        related_name='uploaded_documents',
        verbose_name="会社"
    )
    document_type = models.CharField("ドキュメントタイプ", max_length=30, choices=DOCUMENT_TYPES)
    subfolder_type = models.CharField("サブフォルダタイプ", max_length=30, blank=True)
    original_filename = models.CharField("元のファイル名", max_length=255)
    stored_filename = models.CharField("保存ファイル名", max_length=255, help_text="システムが自動生成したファイル名")
    storage_type = models.CharField("ストレージタイプ", max_length=20, choices=CloudStorageSetting.STORAGE_CHOICES)
    file_id = models.CharField("ファイルID", max_length=255, help_text="ストレージ内のファイルID")
    folder_id = models.CharField("フォルダID", max_length=255, help_text="ストレージ内のフォルダID")
    file_url = models.URLField("ファイルURL", max_length=500, blank=True)
    file_size = models.BigIntegerField("ファイルサイズ（バイト）", null=True, blank=True)
    mime_type = models.CharField("MIMEタイプ", max_length=100, blank=True)
    
    # OCR処理関連
    is_ocr_processed = models.BooleanField("OCR処理済み", default=False)
    ocr_processed_at = models.DateTimeField("OCR処理日時", null=True, blank=True)
    
    # データ保存関連
    is_data_saved = models.BooleanField("データ保存済み", default=False)
    saved_to_model = models.CharField("保存先モデル", max_length=50, blank=True, help_text="例: FiscalSummary_Year, Debt")
    saved_record_id = models.CharField("保存レコードID", max_length=26, blank=True)
    
    # メタデータ
    metadata = models.JSONField("メタデータ", null=True, blank=True, help_text="追加情報（年度、金融機関名など）")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'アップロードドキュメント'
        verbose_name_plural = 'アップロードドキュメント'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'company', 'document_type']),
            models.Index(fields=['is_ocr_processed']),
            models.Index(fields=['is_data_saved']),
        ]
    
    def __str__(self):
        return f"{self.company.name} - {self.get_document_type_display()} - {self.stored_filename}"
    
    def get_subfolder_type_display(self):
        """サブフォルダタイプの表示名を取得"""
        if not self.subfolder_type:
            return ''
        
        subfolder_names = {
            'balance_sheet': '貸借対照表',
            'profit_loss': '損益計算書',
            'monthly_pl': '月次推移損益計算書',
            'department_pl': '部門別損益計算書',
            'lease': 'リース契約書',
            'sales': '商品売買契約',
            'rental': '賃貸借契約',
        }
        
        return subfolder_names.get(self.subfolder_type, self.subfolder_type)


class AIConsultationHistory(models.Model):
    """AI相談の履歴"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='consultation_histories', verbose_name="ユーザー")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='consultation_histories', verbose_name="会社")
    consultation_type = models.ForeignKey(AIConsultationType, on_delete=models.CASCADE, verbose_name="相談タイプ")
    user_message = models.TextField(verbose_name="ユーザーの質問")  # ユーザーの質問
    ai_response = models.TextField(verbose_name="AIの応答")  # AIの応答
    script_used = models.ForeignKey(
        AIConsultationScript,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="使用したスクリプト（システム）"
    )  # 使用したスクリプト（システム用）
    user_script_used = models.ForeignKey(
        UserAIConsultationScript,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="使用したスクリプト（ユーザー）"
    )  # 使用したスクリプト（ユーザー用）
    data_snapshot = models.JSONField(default=dict, verbose_name="データスナップショット")  # 相談時に使用したデータのスナップショット
    # トークン数（将来の制限用、現状は記録のみ）
    input_tokens = models.IntegerField("入力トークン数", default=0, null=True, blank=True, help_text="プロンプトのトークン数")
    output_tokens = models.IntegerField("出力トークン数", default=0, null=True, blank=True, help_text="AI応答のトークン数")
    total_tokens = models.IntegerField("合計トークン数", default=0, null=True, blank=True, help_text="入力+出力の合計トークン数")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'AI相談履歴'
        verbose_name_plural = 'AI相談履歴'
    
    def __str__(self):
        return f"{self.user.username} - {self.consultation_type.name} - {self.created_at}"
    
    @property
    def tokens_display(self):
        """トークン数の表示用"""
        if self.total_tokens:
            return f"{self.total_tokens:,}トークン (入力: {self.input_tokens or 0:,}, 出力: {self.output_tokens or 0:,})"
        return "未記録"


# ============================================================================
# 業界別専門相談室 モデル
# ============================================================================

class IndustryCategory(models.Model):
    """業界カテゴリー"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    name = models.CharField(max_length=100, verbose_name="業界名")  # 例: "外食業界"
    description = models.TextField(verbose_name="説明", blank=True)
    icon = models.CharField(max_length=50, verbose_name="アイコン", blank=True, help_text="Font Awesome等のアイコン名")  # アイコン名（Font Awesome等）
    order = models.IntegerField(default=0, verbose_name="表示順")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = '業界カテゴリー'
        verbose_name_plural = '業界カテゴリー'
    
    def __str__(self):
        return self.name


class IndustryConsultationType(models.Model):
    """業界別相談タイプ"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    industry_category = models.ForeignKey(IndustryCategory, on_delete=models.CASCADE, related_name='consultation_types', verbose_name="業界カテゴリー")
    name = models.CharField(max_length=100, verbose_name="相談タイプ名")  # 例: "居酒屋出店計画作成"
    description = models.TextField(verbose_name="説明", blank=True)
    template_type = models.CharField(
        max_length=50,
        choices=[
            ('izakaya_plan', '居酒屋出店計画'),
            ('cafe_plan', 'カフェ出店計画'),
            # 将来拡張用
        ],
        verbose_name="テンプレートタイプ"
    )
    is_active = models.BooleanField(default=True, verbose_name="有効")
    order = models.IntegerField(default=0, verbose_name="表示順")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = '業界別相談タイプ'
        verbose_name_plural = '業界別相談タイプ'
    
    def __str__(self):
        return f"{self.industry_category.name} - {self.name}"


class IzakayaPlan(models.Model):
    """居酒屋出店計画データ"""
    id = models.CharField(primary_key=True, default=ulid.new, editable=False, max_length=26)
    # 必須: 選択中のCompanyを保持（SelectedCompanyMixinと連携）
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='izakaya_plans', verbose_name="会社")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='izakaya_plans', verbose_name="ユーザー")
    
    # 基本情報
    store_concept = models.CharField(max_length=200, verbose_name="店のコンセプト", blank=True)  # 店のコンセプト
    number_of_seats = models.IntegerField(verbose_name="席数", default=0)  # 席数
    target_customer = models.CharField(max_length=200, verbose_name="ターゲット顧客", blank=True)  # ターゲット
    
    # 昼の営業時間帯
    lunch_start_time = models.TimeField(verbose_name="昼の営業開始時間", null=True, blank=True, help_text="参考情報（売上計算には使用しません）")
    lunch_end_time = models.TimeField(verbose_name="昼の営業終了時間", null=True, blank=True, help_text="参考情報（売上計算には使用しません）")
    lunch_operating_days = models.JSONField(default=list, verbose_name="昼の営業曜日", blank=True, help_text="['monday', 'tuesday', ...]の形式")
    lunch_price_per_customer = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="昼の客単価（円）", default=0)
    lunch_customer_count = models.IntegerField(verbose_name="昼の客数（人/日）", default=0, help_text="1日あたりの客数")
    lunch_cost_rate = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="昼の原価率（%）", default=30.0, help_text="0-100の値")
    lunch_monthly_coefficients = models.JSONField(default=dict, verbose_name="昼の月毎指数", blank=True, help_text="{'1': 1.0, '2': 1.1, ...}の形式（1-12月）")
    
    # 夜の営業時間帯
    dinner_24hours = models.BooleanField(verbose_name="24時間営業", default=False, help_text="24時間営業（昼夜連続）の場合はチェック")
    dinner_start_time = models.TimeField(verbose_name="夜の営業開始時間", null=True, blank=True, help_text="参考情報（売上計算には使用しません）")
    dinner_end_time = models.CharField(verbose_name="夜の営業終了時間", max_length=5, null=True, blank=True, help_text="参考情報（売上計算には使用しません）。28時（翌日4時）まで入力可能。例: 28:00")
    dinner_operating_days = models.JSONField(default=list, verbose_name="夜の営業曜日", blank=True, help_text="['monday', 'tuesday', ...]の形式。24時間営業の場合は全曜日")
    dinner_price_per_customer = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="夜の客単価（円）", default=0)
    dinner_customer_count = models.IntegerField(verbose_name="夜の客数（人/日）", default=0, help_text="1日あたりの客数。24時間営業の場合は合計客数を入力")
    dinner_cost_rate = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="夜の原価率（%）", default=30.0, help_text="0-100の値")
    dinner_monthly_coefficients = models.JSONField(default=dict, verbose_name="夜の月毎指数", blank=True, help_text="{'1': 1.0, '2': 1.1, ...}の形式（1-12月）")
    
    # 後方互換性のためのフィールド（非推奨）
    opening_hours_start = models.TimeField(verbose_name="営業開始時間（旧）", null=True, blank=True)  # 非推奨
    opening_hours_end = models.TimeField(verbose_name="営業終了時間（旧）", null=True, blank=True)  # 非推奨
    average_price_per_customer = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="客単価（円）（旧）", default=0)  # 非推奨
    sales_coefficients = models.JSONField(default=dict, verbose_name="売上係数（旧）", blank=True)  # 非推奨
    
    # 投資情報
    initial_investment = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="初期投資額（円）", default=0)  # 初期投資額（円）
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="月額家賃（円）", default=0)  # 月額家賃（円）
    
    # 人件費
    number_of_staff = models.IntegerField(verbose_name="社員人数", default=0)  # 社員人数
    staff_monthly_salary = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="社員月給（円）", default=0)  # 社員月給（円）
    part_time_hours_per_month = models.IntegerField(verbose_name="アルバイト時間数/月", default=0)  # アルバイト時間数/月
    part_time_hourly_wage = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="アルバイト時給（円）", default=0)  # アルバイト時給（円）
    
    # 追加経費項目
    monthly_utilities = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="光熱費（円/月）", default=0)
    monthly_supplies = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="消耗品費（円/月）", default=0)
    monthly_advertising = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="広告宣伝費（円/月）", default=0)
    monthly_fees = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="手数料（円/月）", default=0)
    monthly_other_expenses = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="その他販管費（円/月）", default=0)
    
    # 計算結果（自動計算）
    monthly_revenue = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True, verbose_name="月間売上（円）")  # 月間売上
    monthly_cost_of_goods_sold = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True, verbose_name="月間売上原価（円）")  # 売上原価
    monthly_gross_profit = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True, verbose_name="月間粗利益（円）")  # 粗利益
    monthly_cost = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True, verbose_name="月間経費（円）")  # 月間経費
    monthly_profit = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True, verbose_name="月間利益（円）")  # 月間利益
    payback_period_months = models.IntegerField(null=True, blank=True, verbose_name="回収期間（月）")  # 回収期間（月）
    payback_period_years = models.IntegerField(null=True, blank=True, verbose_name="回収期間（年）")  # 回収期間（年）
    
    # メタ情報
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")
    is_draft = models.BooleanField(default=True, verbose_name="下書き")  # 下書きかどうか
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = '居酒屋出店計画'
        verbose_name_plural = '居酒屋出店計画'
    
    def __str__(self):
        return f"{self.company.name} - {self.store_concept or '無題'} ({self.created_at.strftime('%Y-%m-%d')})"
    
    def get_absolute_url(self):
        """編集ページのURL"""
        from django.urls import reverse
        return reverse('izakaya_plan_update', kwargs={'pk': self.id})
    
    def get_preview_url(self):
        """プレビューページのURL"""
        from django.urls import reverse
        return reverse('izakaya_plan_preview', kwargs={'pk': self.id})