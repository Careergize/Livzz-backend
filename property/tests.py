from django.contrib.auth import get_user_model
from django.urls import resolve
from rest_framework.test import APITestCase
from property.models import Property
from Tenant.views import TenantListCreateAPIView
from payments.views import PaymentListCreateView


class UIIntegrationTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='owner', phone_number='9876543210', password='test-password', role='owner'
        )
        self.property = Property.objects.create(
            owner=self.user, name='Test apartment', property_type='Apartment',
            city='Bengaluru', state='Karnataka', address='Test street', price=20000
        )

    def test_login_returns_usable_token_for_management(self):
        response = self.client.post('/auth/login/', {
            'phone_number': '9876543210', 'password': 'test-password'
        })
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
        response = self.client.get('/tenants/')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)

    def test_public_list_and_detail_contract(self):
        response = self.client.get('/properties/?property_type=Apartment&city=Bengaluru')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data'][0]['id'], self.property.id)
        self.assertEqual(self.client.get('/properties/?property_type=Villa').data['data'], [])
        response = self.client.get(f'/properties/{self.property.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['name'], 'Test apartment')

    def test_management_routes_are_not_shadowed(self):
        self.assertIs(resolve('/tenants/').func.view_class, TenantListCreateAPIView)
        self.assertIs(resolve('/payments/').func.view_class, PaymentListCreateView)

    def test_management_requires_authentication(self):
        for path in ('/tenants/', '/rooms/', '/staff/', '/visitors/', '/expenses/', '/tickets/', '/payments/', '/notifications/'):
            self.assertEqual(self.client.get(path).status_code, 401, path)
        self.assertEqual(self.client.post('/properties/', {}).status_code, 401)

# Create your tests here.
