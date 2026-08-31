from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from organizations.access import properties_accessible_to, user_can
from organizations.models import Organization, OrganizationMembership, PropertyAccess
from property.models import Property


class OrganizationAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner_a = User.objects.create_user(username='owner-a', phone_number='10001', password='pass')
        self.manager_a = User.objects.create_user(username='manager-a', phone_number='10002', password='pass')
        self.owner_b = User.objects.create_user(username='owner-b', phone_number='10003', password='pass')
        self.unaffiliated = User.objects.create_user(username='none', phone_number='10004', password='pass')
        self.org_a = Organization.objects.create(name='Organization A')
        self.org_b = Organization.objects.create(name='Organization B')
        OrganizationMembership.objects.create(user=self.owner_a, organization=self.org_a, roles=['owner'], all_properties=True)
        self.manager_membership = OrganizationMembership.objects.create(user=self.manager_a, organization=self.org_a, roles=['manager'])
        OrganizationMembership.objects.create(user=self.owner_b, organization=self.org_b, roles=['owner'], all_properties=True)
        self.a1 = self.make_property(self.owner_a, self.org_a, 'A1')
        self.a2 = self.make_property(self.owner_a, self.org_a, 'A2')
        self.b1 = self.make_property(self.owner_b, self.org_b, 'B1')
        PropertyAccess.objects.create(membership=self.manager_membership, property=self.a1)
        self.client = APIClient()

    @staticmethod
    def make_property(owner, organization, name):
        return Property.objects.create(owner=owner, organization=organization, name=name, property_type='PG', address='Address', city='City', state='State')

    def test_owner_access_is_limited_to_organization(self):
        self.assertSetEqual(set(properties_accessible_to(self.owner_a)), {self.a1, self.a2})
        self.assertNotIn(self.b1, properties_accessible_to(self.owner_a))
        self.assertFalse(user_can(self.owner_a, 'property.view', self.b1))

    def test_restricted_manager_sees_assigned_property_only(self):
        self.assertSetEqual(set(properties_accessible_to(self.manager_a)), {self.a1})
        self.assertTrue(user_can(self.manager_a, 'property.manage', self.a1))
        self.assertFalse(user_can(self.manager_a, 'property.manage', self.a2))

    def test_other_owner_and_unaffiliated_user_see_no_a_resources(self):
        self.assertNotIn(self.a1, properties_accessible_to(self.owner_b))
        self.assertFalse(properties_accessible_to(self.unaffiliated).exists())

    def test_v2_organization_and_property_scope_uses_404(self):
        self.client.force_authenticate(self.owner_a)
        own = self.client.get(f'/api/v2/organizations/{self.org_a.public_id}/properties/')
        foreign = self.client.get(f'/api/v2/organizations/{self.org_b.public_id}/properties/')
        self.assertEqual(own.status_code, 200)
        self.assertEqual(own.json()['meta']['count'], 2)
        self.assertEqual(foreign.status_code, 404)

    def test_v2_me_reports_roles_and_named_permissions(self):
        self.client.force_authenticate(self.manager_a)
        response = self.client.get('/api/v2/me/')
        self.assertEqual(response.status_code, 200)
        membership = response.json()['data']['memberships'][0]
        self.assertEqual(membership['roles'], ['manager'])
        self.assertIn('property.manage', membership['permissions'])


class SecurityAndLegacyContractTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username='owner', phone_number='20001', password='pass')
        self.organization = Organization.objects.create(name='Public Org')
        OrganizationMembership.objects.create(user=self.owner, organization=self.organization, roles=['owner'], all_properties=True)
        self.property = Property.objects.create(owner=self.owner, organization=self.organization, name='Public PG', property_type='PG', address='Address', city='City', state='State', is_active=True)
        self.client = APIClient()

    def test_private_management_endpoints_require_authentication(self):
        for url in ('/properties/', '/rooms/', '/tenants/', '/staff/', '/expenses/', '/tickets/', '/payments/'):
            with self.subTest(url=url):
                self.assertIn(self.client.get(url).status_code, (401, 403))

    def test_public_legacy_marketplace_contract_remains_anonymous(self):
        search = self.client.get('/properties/search/')
        detail = self.client.get(f'/properties/{self.property.pk}/')
        locations = self.client.get('/')
        self.assertEqual(search.status_code, 200)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(locations.status_code, 200)
        self.assertIn('data', search.json())
        self.assertIn('data', detail.json())

    def test_authenticated_user_cannot_enumerate_foreign_legacy_property(self):
        stranger = get_user_model().objects.create_user(username='stranger', phone_number='20002', password='pass')
        self.client.force_authenticate(stranger)
        response = self.client.get('/properties/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data'], [])
