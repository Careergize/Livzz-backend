from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from organizations.models import Organization, OrganizationMembership, PropertyAccess
from property.models import (ApartmentDetails, InventoryItem, OfficeDetails, PGDetails,
                             Property, PropertyAmenity, PropertyMedia, Unit, VillaDetails, Amenity)
from .models import Availability, Listing, ListingTarget, PricePlan
from .services import PublishValidationError, publish_listing, resolve_current_price


class MarketplaceFixture(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username='market-owner', phone_number='41001', password='pass')
        self.manager = User.objects.create_user(username='market-manager', phone_number='41002', password='pass')
        self.stranger = User.objects.create_user(username='market-stranger', phone_number='41003', password='pass')
        self.org = Organization.objects.create(name='Marketplace Org')
        self.other_org = Organization.objects.create(name='Foreign Org')
        OrganizationMembership.objects.create(user=self.owner, organization=self.org, roles=['owner'], all_properties=True)
        self.manager_membership = OrganizationMembership.objects.create(user=self.manager, organization=self.org, roles=['manager'])
        OrganizationMembership.objects.create(user=self.stranger, organization=self.other_org, roles=['owner'], all_properties=True)
        self.client = APIClient()

    def property(self, category='PG', name=None, with_details=True):
        prop = Property.objects.create(owner=self.owner, organization=self.org, name=name or category,
                                       property_type=category, address='1 Real Street', locality='Indiranagar',
                                       city='Bengaluru', state='Karnataka')
        if with_details:
            {'PG': PGDetails, 'APARTMENT': ApartmentDetails, 'VILLA': VillaDetails, 'OFFICE': OfficeDetails}[category].objects.create(property=prop)
        return prop

    def listing(self, category='PG', target_type='PROPERTY', published=False, price=True, media=True, **target):
        prop = self.property(category, f'{category}-{Listing.objects.count()}')
        listing = Listing.objects.create(organization=self.org, property=prop, category=category,
                                         title=f'{category} offer', slug=f'{category.lower()}-{Listing.objects.count()}', created_by=self.owner)
        ListingTarget.objects.create(listing=listing, target_type=target_type, **target)
        if price:
            PricePlan.objects.create(listing=listing, amount='9000', effective_from=timezone.now() - timedelta(days=1))
        if media:
            PropertyMedia.objects.create(property=prop, file='property_media/real.jpg', is_primary=True)
        if published:
            publish_listing(user=self.owner, listing=listing)
        return listing


class ListingAndTargetTests(MarketplaceFixture):
    def test_all_categories_and_category_mismatch(self):
        for category in ('PG', 'APARTMENT', 'VILLA', 'OFFICE'):
            self.assertEqual(self.listing(category).category, category)
        prop = self.property('PG', 'Mismatch')
        with self.assertRaises(ValidationError):
            Listing.objects.create(organization=self.org, property=prop, category='OFFICE', title='Bad', slug='bad')

    def test_property_unit_inventory_and_capacity_targets(self):
        self.listing(target_type='PROPERTY')
        prop = self.property('PG', 'Targets')
        unit = Unit.objects.create(property=prop, code='101', unit_type='ROOM', capacity=3)
        item = InventoryItem.objects.create(property=prop, unit=unit, item_type='BED', code='A')
        for suffix, kind, kwargs in (('u', 'UNIT', {'unit': unit}), ('i', 'INVENTORY_ITEM', {'inventory_item': item}),
                                     ('c', 'CAPACITY_POOL', {'unit': unit, 'capacity': 2})):
            listing = Listing.objects.create(organization=self.org, property=prop, category='PG', title=suffix, slug=f'target-{suffix}')
            ListingTarget.objects.create(listing=listing, target_type=kind, **kwargs)

    def test_cross_property_and_cross_organization_targets_rejected(self):
        listing = self.listing()
        other = self.property('PG', 'Other target')
        unit = Unit.objects.create(property=other, code='1', unit_type='ROOM')
        with self.assertRaises(ValidationError):
            ListingTarget.objects.update_or_create(listing=listing, defaults={'target_type': 'UNIT', 'unit': unit})
        foreign = Property.objects.create(owner=self.stranger, organization=self.other_org, name='Foreign', property_type='PG', address='A', city='C', state='S')
        with self.assertRaises(ValidationError):
            Listing.objects.create(organization=self.org, property=foreign, category='PG', title='Foreign', slug='foreign')


class PricingAvailabilityPublishingTests(MarketplaceFixture):
    def test_active_future_expired_and_decimal_resolution(self):
        listing = self.listing(price=False)
        now = timezone.now()
        PricePlan.objects.create(listing=listing, amount='1000.25', effective_from=now - timedelta(days=2), effective_to=now + timedelta(days=1))
        PricePlan.objects.create(listing=listing, amount='1200', effective_from=now + timedelta(days=1), effective_to=now + timedelta(days=2))
        self.assertEqual(resolve_current_price(listing).amount, Decimal('1000.25'))
        self.assertEqual(resolve_current_price(listing, now + timedelta(days=1, seconds=1)).amount, Decimal('1200.00'))
        self.assertIsNone(resolve_current_price(listing, now + timedelta(days=3)))

    def test_conflicting_active_prices_rejected(self):
        listing = self.listing()
        with self.assertRaises(ValidationError):
            PricePlan.objects.create(listing=listing, amount=10, effective_from=timezone.now())

    def test_availability_quantity_and_lineage(self):
        prop = self.property('PG', 'Pool')
        unit = Unit.objects.create(property=prop, code='P', unit_type='ROOM', capacity=4)
        listing = Listing.objects.create(organization=self.org, property=prop, category='PG', title='Pool', slug='pool')
        ListingTarget.objects.create(listing=listing, target_type='CAPACITY_POOL', unit=unit, capacity=4)
        Availability.objects.create(listing=listing, unit=unit, start=timezone.now(), quantity=2, status='AVAILABLE')
        foreign_unit = Unit.objects.create(property=self.property('PG', 'Wrong'), code='W', unit_type='ROOM')
        with self.assertRaises(ValidationError):
            Availability.objects.create(listing=listing, unit=foreign_unit, start=timezone.now(), status='BLOCKED')

    def test_publish_validation_and_lifecycle_visibility(self):
        incomplete = self.listing(price=False)
        with self.assertRaises(PublishValidationError):
            publish_listing(user=self.owner, listing=incomplete)
        listing = self.listing(published=True)
        self.assertEqual(self.client.get('/api/v2/marketplace/listings/').json()['meta']['count'], 1)
        self.client.force_authenticate(self.owner)
        pause = self.client.post(f'/api/v2/organizations/{self.org.public_id}/listings/{listing.public_id}/pause/')
        self.assertEqual(pause.status_code, 200)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/v2/marketplace/listings/').json()['meta']['count'], 0)


class MarketplaceAPITests(MarketplaceFixture):
    def test_public_contract_filters_categories_and_no_fabricated_facts(self):
        pg = self.listing('PG', published=True)
        apartment = self.listing('APARTMENT', published=True)
        amenity, _ = Amenity.objects.get_or_create(code='wifi', defaults={'name': 'Wi-Fi'})
        PropertyAmenity.objects.create(property=pg.property, amenity=amenity)
        response = self.client.get('/api/v2/marketplace/pg/?city=Bengaluru&locality=Indiranagar&amenities=wifi&min_price=8000&max_price=10000')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['meta']['count'], 1)
        data = response.json()['data'][0]
        self.assertEqual(data['pricing']['amount'], '9000.00')
        self.assertIsNone(data['availability'])
        for fabricated in ('rating', 'reviews', 'verified', 'distance', 'ai_score'):
            self.assertNotIn(fabricated, data)
        self.assertEqual(self.client.get('/api/v2/marketplace/apartments/').json()['meta']['count'], 1)
        self.assertEqual(self.client.get('/api/v2/marketplace/villas/').json()['meta']['count'], 0)

    def test_draft_never_public_and_public_mutation_impossible(self):
        listing = self.listing()
        self.assertEqual(self.client.get('/api/v2/marketplace/listings/').json()['meta']['count'], 0)
        self.assertEqual(self.client.post('/api/v2/marketplace/listings/', {'title': 'bad'}).status_code, 405)
        self.assertEqual(self.client.get(f'/api/v2/marketplace/listings/{listing.slug}/').status_code, 404)

    def test_owner_manager_and_unrelated_organization_security(self):
        prop = self.property('PG', 'Managed')
        PropertyAccess.objects.create(membership=self.manager_membership, property=prop)
        url = f'/api/v2/organizations/{self.org.public_id}/listings/'
        payload = {'property_id': str(prop.public_id), 'category': 'PG', 'title': 'Managed offer',
                   'target': {'target_type': 'PROPERTY'}}
        self.client.force_authenticate(self.manager)
        created = self.client.post(url, payload, format='json')
        self.assertEqual(created.status_code, 201, created.content)
        self.client.force_authenticate(self.stranger)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.patch(f'{url}{created.json()["data"]["id"]}/', {'title': 'stolen'}, format='json').status_code, 404)

    def test_management_price_availability_and_publish_errors(self):
        listing = self.listing(price=False, media=False)
        self.client.force_authenticate(self.owner)
        base = f'/api/v2/organizations/{self.org.public_id}/listings/{listing.public_id}'
        price = self.client.post(f'{base}/prices/', {'amount': '7500.50', 'currency': 'inr', 'billing_cycle': 'MONTHLY',
                                 'deposit_amount': '5000', 'effective_from': (timezone.now() - timedelta(minutes=1)).isoformat()}, format='json')
        self.assertEqual(price.status_code, 201, price.content)
        self.assertEqual(price.json()['data']['amount'], '7500.50')
        available = self.client.post(f'{base}/availability/', {'start': timezone.now().isoformat(), 'status': 'AVAILABLE'}, format='json')
        self.assertEqual(available.status_code, 201, available.content)
        errors = self.client.post(f'{base}/publish/').json()['errors']
        self.assertTrue(any(error['field'] == 'media' for error in errors))
