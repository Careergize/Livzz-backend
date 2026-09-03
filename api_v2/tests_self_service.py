import base64
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import ListerProfile
from accounts.models import User
from marketplace.models import Listing, PricePlan
from organizations.models import OrganizationMembership


PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')


@override_settings(MEDIA_ROOT='test-media-self-service')
class SelfServiceListingTests(APITestCase):
    def register(self, phone='9000000001'):
        response = self.client.post('/api/v2/auth/register/', {
            'phone_number': phone, 'password': 'strong-pass', 'first_name': 'Asha',
            'email': f'{phone}@example.com'}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + response.json()['data']['token'])
        self.current_user = User.objects.get(phone_number=phone)
        return response

    def become_lister(self, kind='OWNER'):
        response = self.client.post('/api/v2/me/lister-profile/', {'lister_type': kind}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response

    def draft(self, category='PG'):
        response = self.client.post('/api/v2/listing-drafts/', {'property_type': category}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()['data']

    def test_auth_register_login_me_logout_and_anonymous_denied(self):
        self.register()
        self.assertEqual(self.client.get('/api/v2/me/').status_code, 200)
        self.client.credentials()
        self.assertEqual(self.client.post('/api/v2/listing-drafts/', {'property_type': 'PG'}).status_code, 401)
        login = self.client.post('/api/v2/auth/login/', {'phone_number': '9000000001', 'password': 'strong-pass'})
        self.assertEqual(login.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + login.json()['data']['token'])
        self.assertEqual(self.client.post('/api/v2/auth/logout/').status_code, 200)

    def test_profile_types_and_user_cannot_self_verify(self):
        for index, kind in enumerate(('OWNER', 'BROKER', 'PROPERTY_MANAGER'), 1):
            self.register(f'911111111{index}')
            profile = self.become_lister(kind).json()['data']
            self.assertEqual(profile['verification_status'], 'UNVERIFIED')
            self.assertEqual(profile['lister_type'], kind)
            denied = self.client.patch('/api/v2/me/lister-profile/', {'verification_status': 'VERIFIED'})
            self.assertEqual(denied.status_code, 400)
            self.assertEqual(ListerProfile.objects.get(user=self.current_user).verification_status, 'UNVERIFIED')

    def test_draft_create_resume_partial_all_categories_and_org_reuse(self):
        self.register()
        self.become_lister()
        drafts = [self.draft(kind) for kind in ('PG', 'APARTMENT', 'VILLA', 'OFFICE')]
        self.assertEqual(OrganizationMembership.objects.filter(user=self.current_user).count(), 1)
        draft = drafts[0]
        saved = self.client.patch(f'/api/v2/listing-drafts/{draft["draft_id"]}/', {
            'current_step': 'LOCATION', 'property': {'city': 'Bengaluru'}}, format='json')
        self.assertEqual(saved.status_code, 200, saved.content)
        resumed = self.client.get(f'/api/v2/listing-drafts/{draft["draft_id"]}/').json()['data']
        self.assertEqual(resumed['property']['city'], 'Bengaluru')
        self.assertEqual(len(self.client.get('/api/v2/me/listing-drafts/').json()['data']), 4)

    def test_cross_user_draft_and_media_access_denied(self):
        self.register()
        self.become_lister()
        draft = self.draft()
        self.register('9000000002')
        self.become_lister('BROKER')
        base = f'/api/v2/listing-drafts/{draft["draft_id"]}'
        self.assertEqual(self.client.get(base + '/').status_code, 404)
        self.assertEqual(self.client.patch(base + '/', {'title': 'stolen'}, format='json').status_code, 404)
        self.assertEqual(self.client.post(base + '/publish/').status_code, 404)
        self.assertEqual(self.client.post(base + '/media/', {'images': SimpleUploadedFile('a.png', PNG, 'image/png')}).status_code, 404)

    def test_media_upload_multiple_reorder_primary_delete_and_validation(self):
        self.register(); self.become_lister(); draft = self.draft()
        url = f'/api/v2/listing-drafts/{draft["draft_id"]}/media/'
        uploaded = self.client.post(url, {'images': [SimpleUploadedFile('a.png', PNG, 'image/png'),
                                                       SimpleUploadedFile('b.png', PNG, 'image/png')]}, format='multipart')
        self.assertEqual(uploaded.status_code, 201, uploaded.content)
        media = uploaded.json()['data']
        reordered = self.client.patch(url, {'media_ids': [media[1]['id'], media[0]['id']],
                                             'primary_id': media[1]['id']}, format='json')
        self.assertEqual(reordered.status_code, 200, reordered.content)
        self.assertTrue(reordered.json()['data'][0]['is_primary'])
        self.assertEqual(self.client.delete(url + f'{media[1]["id"]}/').status_code, 200)
        invalid = self.client.post(url, {'images': SimpleUploadedFile('fake.png', b'not-image', 'image/png')}, format='multipart')
        self.assertEqual(invalid.status_code, 400)
        large = self.client.post(url, {'images': SimpleUploadedFile('large.png', PNG + b'x' * (10 * 1024 * 1024), 'image/png')}, format='multipart')
        self.assertEqual(large.status_code, 400)

    def test_pricing_unknown_availability_broker_provenance_and_publish(self):
        self.register(); self.become_lister('BROKER'); draft = self.draft('APARTMENT')
        base = f'/api/v2/listing-drafts/{draft["draft_id"]}/'
        incomplete = self.client.post(base + 'publish/')
        self.assertEqual(incomplete.status_code, 400)
        updated = self.client.patch(base, {
            'title': 'Central apartment', 'property': {
                'name': 'Central apartment', 'address': '1 Main Road', 'city': 'Bengaluru',
                'state': 'Karnataka', 'category_details': {'bedrooms': 2}},
            'pricing': {'amount': '25000', 'currency': 'INR', 'billing_cycle': 'MONTHLY',
                        'deposit_amount': '50000', 'maintenance_amount': '2000',
                        'minimum_stay': 180, 'effective_from': (timezone.now() - timedelta(minutes=1)).isoformat()}
        }, format='json')
        self.assertEqual(updated.status_code, 200, updated.content)
        listing = Listing.objects.get(public_id=draft['listing_id'])
        self.assertEqual(PricePlan.objects.get(listing=listing).amount, 25000)
        self.assertFalse(listing.availability_records.exists())
        self.assertEqual(listing.lister_profile.lister_type, 'BROKER')
        self.assertIsNone(listing.property.owner)
        media_url = base + 'media/'
        self.assertEqual(self.client.post(media_url, {'images': SimpleUploadedFile('a.png', PNG, 'image/png')}, format='multipart').status_code, 201)
        published = self.client.post(base + 'publish/')
        self.assertEqual(published.status_code, 200, published.content)
        self.assertEqual(published.json()['data']['status'], 'PUBLISHED')

    def test_explicit_availability_and_space_target(self):
        self.register(); self.become_lister(); draft = self.draft('PG')
        response = self.client.patch(f'/api/v2/listing-drafts/{draft["draft_id"]}/', {
            'space': {'code': '101', 'name': 'Room 101', 'unit_type': 'ROOM', 'capacity': 2,
                      'inventory_item': {'item_type': 'BED', 'code': 'A'}},
            'availability': {'start': timezone.now().isoformat(), 'status': 'AVAILABLE'}}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        listing = Listing.objects.get(public_id=draft['listing_id'])
        self.assertEqual(listing.target.target_type, 'INVENTORY_ITEM')
        self.assertEqual(listing.availability_records.get().status, 'AVAILABLE')
