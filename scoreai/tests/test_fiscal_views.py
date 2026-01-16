from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from scoreai.models import Company, UserCompany

User = get_user_model()

class FiscalViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='fiscaltest',
            email='fiscal@example.com',
            password='testpass123'
        )
        self.company = Company.objects.create(
            name='Test Company',
            fiscal_month=3
        )
        UserCompany.objects.create(
            user=self.user,
            company=self.company,
            is_selected=True
        )
        self.client.login(username='fiscaltest', password='testpass123')

    def test_fiscal_year_list_view(self):
        url = reverse('fiscal_summary_year_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_fiscal_month_list_view(self):
        url = reverse('fiscal_summary_month_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_import_year_view(self):
        url = reverse('import_fiscal_summary_year')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_import_month_view(self):
        url = reverse('import_fiscal_summary_month')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
