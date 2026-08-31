from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from rest_framework.test import APIClient

from organizations.models import Organization, OrganizationMembership, PropertyAccess
from property.models import InventoryItem, OfficeDetails, PGDetails, Property, Unit
from rooms.models import Room


class Phase2APITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username='p2-owner', phone_number='30001', password='pass')
        self.manager = User.objects.create_user(username='p2-manager', phone_number='30002', password='pass')
        self.stranger = User.objects.create_user(username='p2-stranger', phone_number='30003', password='pass')
        self.org = Organization.objects.create(name='Phase 2 Org')
        self.other_org = Organization.objects.create(name='Other Org')
        OrganizationMembership.objects.create(user=self.owner, organization=self.org, roles=['owner'], all_properties=True)
        self.manager_membership = OrganizationMembership.objects.create(user=self.manager, organization=self.org, roles=['manager'])
        OrganizationMembership.objects.create(user=self.stranger, organization=self.other_org, roles=['owner'], all_properties=True)
        self.client = APIClient()

    def create_property(self, property_type='PG', name='Asset', details=None):
        self.client.force_authenticate(self.owner)
        payload = {'property_type': property_type, 'name': name, 'address': '1 Main St', 'city': 'Bengaluru', 'state': 'Karnataka'}
        if details is not None:
            payload['category_details'] = details
        return self.client.post(f'/api/v2/organizations/{self.org.public_id}/properties/', payload, format='json')

    def test_all_canonical_property_types_and_invalid_type(self):
        for value in ('PG', 'APARTMENT', 'VILLA', 'OFFICE'):
            with self.subTest(value=value):
                response = self.create_property(value, f'Asset {value}')
                self.assertEqual(response.status_code, 201, response.content)
                self.assertEqual(response.json()['data']['property_type'], value)
        self.assertEqual(self.create_property('Co-living', 'Legacy input').status_code, 400)

    def test_matching_detail_is_created_and_wrong_model_rejected(self):
        response = self.create_property('PG', details={'wifi_available': True, 'gender_policy': 'UNISEX'})
        prop = Property.objects.get(public_id=response.json()['data']['id'])
        self.assertTrue(PGDetails.objects.filter(property=prop, wifi_available=True).exists())
        with self.assertRaises(ValidationError):
            OfficeDetails.objects.create(property=prop)

    def test_owner_manager_and_cross_organization_security(self):
        response = self.create_property()
        prop = Property.objects.get(public_id=response.json()['data']['id'])
        PropertyAccess.objects.create(membership=self.manager_membership, property=prop)
        url = f'/api/v2/organizations/{self.org.public_id}/properties/{prop.public_id}/'
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.patch(url, {'description': 'managed'}, format='json').status_code, 200)
        self.client.force_authenticate(self.stranger)
        self.assertEqual(self.client.patch(url, {'description': 'leak'}, format='json').status_code, 404)
        self.client.force_authenticate(get_user_model().objects.create_user(username='none-p2', phone_number='30004'))
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_units_hierarchy_duplicates_and_cross_property_parent(self):
        prop_id = self.create_property().json()['data']['id']
        base = f'/api/v2/organizations/{self.org.public_id}/properties/{prop_id}/units/'
        room = self.client.post(base, {'code': '101', 'unit_type': 'ROOM', 'capacity': 4}, format='json')
        self.assertEqual(room.status_code, 201, room.content)
        child = self.client.post(base, {'code': 'A', 'unit_type': 'CABIN', 'parent_unit_id': room.json()['data']['id']}, format='json')
        self.assertEqual(child.status_code, 201, child.content)
        self.assertEqual(self.client.post(base, {'code': '101', 'unit_type': 'ROOM'}, format='json').status_code, 400)
        other_id = self.create_property('OFFICE', 'Other').json()['data']['id']
        other_base = f'/api/v2/organizations/{self.org.public_id}/properties/{other_id}/units/'
        self.assertEqual(self.client.post(other_base, {'code': 'bad', 'unit_type': 'CABIN', 'parent_unit_id': room.json()['data']['id']}, format='json').status_code, 400)

    def test_inventory_explicit_or_capacity_only(self):
        prop_id = self.create_property().json()['data']['id']
        units_url = f'/api/v2/organizations/{self.org.public_id}/properties/{prop_id}/units/'
        unit = self.client.post(units_url, {'code': '101', 'unit_type': 'ROOM', 'capacity': 4}, format='json').json()['data']
        self.assertEqual(InventoryItem.objects.count(), 0)
        inventory_url = f'/api/v2/organizations/{self.org.public_id}/properties/{prop_id}/inventory/'
        for item_type, code in (('BED', 'A'), ('DESK', 'D1')):
            self.assertEqual(self.client.post(inventory_url, {'unit_id': unit['id'], 'item_type': item_type, 'code': code}, format='json').status_code, 201)
        self.assertEqual(self.client.post(inventory_url, {'unit_id': unit['id'], 'item_type': 'BED', 'code': 'A'}, format='json').status_code, 400)

    def test_property_type_transition_with_detail_is_blocked(self):
        prop_id = self.create_property('PG', details={}).json()['data']['id']
        url = f'/api/v2/organizations/{self.org.public_id}/properties/{prop_id}/'
        self.assertEqual(self.client.patch(url, {'property_type': 'OFFICE'}, format='json').status_code, 400)


class Phase2LegacyCompatibilityTests(TestCase):
    def test_legacy_room_model_remains_available(self):
        user = get_user_model().objects.create_user(username='legacy-owner', phone_number='31001')
        org = Organization.objects.create(name='Legacy Org')
        prop = Property.objects.create(owner=user, organization=org, name='Legacy PG', property_type='PG', address='A', city='C', state='S')
        room = Room.objects.create(property=prop, room_number='7', sharing_type='Double Sharing', total_beds=2, rent=5000)
        self.assertEqual(room.available_beds(), 2)
        self.assertTrue(Room.objects.filter(pk=room.pk).exists())
