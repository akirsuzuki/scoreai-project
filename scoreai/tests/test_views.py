"""
ビューのテスト
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from ..models import Company, UserCompany

User = get_user_model()


class IndexViewTest(TestCase):
    """IndexViewのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.client = Client()
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
    
    def test_index_view_requires_login(self):
        """ログインが必要なことを確認"""
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 302)  # リダイレクト
    
    def test_index_view_with_login(self):
        """ログイン後のアクセステスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ダッシュボード')


class CompanyViewTest(TestCase):
    """会社関連ビューのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.client = Client()
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
    
    def test_company_detail_view(self):
        """会社詳細ビューのテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('company_detail', kwargs={'id': self.company.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト会社')

