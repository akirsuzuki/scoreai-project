"""
モデルのテスト
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from ..models import Company, UserCompany, Debt, FiscalSummary_Year

User = get_user_model()


class CompanyModelTest(TestCase):
    """Companyモデルのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.company = Company.objects.create(
            name='テスト会社',
            fiscal_month=4
        )
        UserCompany.objects.create(
            user=self.user,
            company=self.company,
            is_selected=True
        )
    
    def test_company_creation(self):
        """会社の作成テスト"""
        self.assertEqual(self.company.name, 'テスト会社')
        self.assertEqual(self.company.fiscal_month, 4)
    
    def test_user_company_relationship(self):
        """ユーザーと会社の関係テスト"""
        user_company = UserCompany.objects.get(user=self.user, company=self.company)
        self.assertTrue(user_company.is_selected)
        self.assertEqual(user_company.company, self.company)


class DebtModelTest(TestCase):
    """Debtモデルのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.company = Company.objects.create(
            name='テスト会社',
            fiscal_month=4
        )
        UserCompany.objects.create(
            user=self.user,
            company=self.company,
            is_selected=True
        )
    
    def test_debt_creation(self):
        """借入の作成テスト"""
        from ..models import FinancialInstitution, SecuredType
        
        financial_institution = FinancialInstitution.objects.create(
            name='テスト銀行',
            short_name='テスト',
            JBAcode='0001',
            bank_category='普通銀行'
        )
        secured_type = SecuredType.objects.create(name='担保付')
        
        debt = Debt.objects.create(
            company=self.company,
            financial_institution=financial_institution,
            secured_type=secured_type,
            principal=1000000,
            interest_rate=1.5
        )
        
        self.assertEqual(debt.company, self.company)
        self.assertEqual(debt.principal, 1000000)
        self.assertEqual(debt.interest_rate, 1.5)

