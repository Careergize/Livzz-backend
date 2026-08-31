from decimal import Decimal

from django.db import migrations
from django.utils.text import slugify


def unique_slug(Listing, title):
    base = slugify(title)[:230] or 'listing'
    value, suffix = base, 2
    while Listing.objects.filter(slug=value).exists():
        value = f'{base[:240]}-{suffix}'
        suffix += 1
    return value


def migrate_legacy_offers(apps, schema_editor):
    Listing = apps.get_model('marketplace', 'Listing')
    ListingTarget = apps.get_model('marketplace', 'ListingTarget')
    PricePlan = apps.get_model('marketplace', 'PricePlan')
    Property = apps.get_model('property', 'Property')
    RoomConfiguration = apps.get_model('property', 'RoomConfiguration')
    Unit = apps.get_model('property', 'Unit')
    LegacyMappingIssue = apps.get_model('property', 'LegacyMappingIssue')

    for prop in Property.objects.filter(property_type__in=('PG', 'APARTMENT', 'VILLA', 'OFFICE')).iterator():
        if prop.price and prop.price > Decimal('0'):
            title = prop.name
            listing = Listing.objects.create(
                organization_id=prop.organization_id, property_id=prop.id, created_by_id=prop.owner_id,
                slug=unique_slug(Listing, title), category=prop.property_type, title=title,
                description=prop.description or '', status='DRAFT',
                legacy_source={'model': 'Property', 'id': prop.id, 'field': 'price'},
            )
            ListingTarget.objects.create(listing_id=listing.id, target_type='PROPERTY')
            PricePlan.objects.create(listing_id=listing.id, amount=prop.price, currency=prop.currency or 'INR',
                                     billing_cycle='MONTHLY', deposit_amount=0,
                                     effective_from=prop.created_at, status='ACTIVE')

    for config in RoomConfiguration.objects.select_related('property').all().iterator():
        prop = config.property
        if prop.property_type != 'PG':
            LegacyMappingIssue.objects.get_or_create(
                property_id=prop.id, source_field='RoomConfiguration.marketplace', source_value=str(config.id),
                defaults={'reason': 'Room configuration belongs to a non-canonical PG property; no listing was guessed.'})
            continue
        candidates = list(Unit.objects.filter(property_id=prop.id, unit_type='ROOM', capacity=config.total_beds).values_list('id', flat=True)[:2])
        if len(candidates) != 1 or not config.total_beds:
            LegacyMappingIssue.objects.get_or_create(
                property_id=prop.id, source_field='RoomConfiguration.marketplace', source_value=str(config.id),
                defaults={'reason': 'Configuration could not be mapped to exactly one physical room/capacity pool.'})
            continue
        title = f'{config.room_type} at {prop.name}'
        listing = Listing.objects.create(
            organization_id=prop.organization_id, property_id=prop.id, created_by_id=prop.owner_id,
            slug=unique_slug(Listing, title), category='PG', title=title,
            description='', status='DRAFT',
            legacy_source={'model': 'RoomConfiguration', 'id': config.id},
        )
        ListingTarget.objects.create(listing_id=listing.id, target_type='CAPACITY_POOL', unit_id=candidates[0], capacity=config.total_beds)
        PricePlan.objects.create(listing_id=listing.id, amount=config.rent, currency=prop.currency or 'INR',
                                 billing_cycle='MONTHLY', deposit_amount=config.deposit,
                                 effective_from=prop.created_at, status='ACTIVE')


class Migration(migrations.Migration):
    dependencies = [('marketplace', '0001_initial'), ('property', '0006_backfill_phase2_assets')]
    operations = [migrations.RunPython(migrate_legacy_offers, migrations.RunPython.noop)]
