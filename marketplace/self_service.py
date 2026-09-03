from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from organizations.models import PropertyAccess
from organizations.services import ensure_lister_organization
from property.models import (Amenity, InventoryItem, Property, PropertyAmenity, Unit)
from property.services import DETAIL_MODELS, validate_category_details
from .models import Availability, Listing, ListingDraft, ListingMedia, ListingTarget, PricePlan
from .services import unique_listing_slug


@transaction.atomic
def create_listing_draft(*, user, property_type, title=''):
    try:
        profile = user.lister_profile
    except Exception:
        raise ValidationError({'lister_profile': 'Create a lister profile before starting a listing.'})
    if property_type not in Property.CANONICAL_PROPERTY_TYPES:
        raise ValidationError({'property_type': 'Use PG, APARTMENT, VILLA, or OFFICE.'})
    organization, membership = ensure_lister_organization(user)
    label = (title or f'Untitled {property_type.title()}')[:255]
    legacy_owner = user if profile.lister_type == profile.OWNER else None
    prop = Property.objects.create(owner=legacy_owner, organization=organization, name=label,
                                   property_type=property_type, address='', city='', state='')
    PropertyAccess.objects.get_or_create(membership=membership, property=prop)
    listing = Listing.objects.create(organization=organization, property=prop,
                                     category=property_type, title=label,
                                     slug=unique_listing_slug(label), created_by=user,
                                     lister_profile=profile)
    ListingTarget.objects.create(listing=listing, target_type=ListingTarget.PROPERTY)
    return ListingDraft.objects.create(listing=listing)


def drafts_for(user):
    return ListingDraft.objects.filter(listing__created_by=user).select_related(
        'listing__property', 'listing__organization', 'listing__lister_profile')


@transaction.atomic
def update_listing_draft(*, user, draft, data):
    if draft.listing.created_by_id != user.id:
        raise PermissionError('You cannot modify this draft.')
    listing, prop = draft.listing, draft.listing.property
    if 'current_step' in data:
        draft.current_step = data['current_step']
        draft.save(update_fields=('current_step', 'updated_at'))
    for field in ('title', 'description'):
        if field in data:
            setattr(listing, field, data[field])
    listing.save()
    property_data = dict(data.get('property', {}))
    details = property_data.pop('category_details', None)
    if property_data or details is not None:
        allowed = {'name', 'description', 'address', 'locality', 'city', 'state', 'country',
                   'postal_code', 'latitude', 'longitude', 'timezone', 'currency'}
        unknown = set(property_data) - allowed
        if unknown:
            raise ValidationError({'property': f'Unsupported fields: {", ".join(sorted(unknown))}.'})
        if property_data.get('latitude') is not None and not -90 <= property_data['latitude'] <= 90:
            raise ValidationError({'latitude': 'Latitude must be between -90 and 90.'})
        if property_data.get('longitude') is not None and not -180 <= property_data['longitude'] <= 180:
            raise ValidationError({'longitude': 'Longitude must be between -180 and 180.'})
        for field, value in property_data.items():
            setattr(prop, field, value)
        if property_data:
            prop.save(update_fields=tuple(property_data) + ('updated_at',))
        if details is not None:
            validate_category_details(prop.property_type, details)
            detail, _ = DETAIL_MODELS[prop.property_type].objects.get_or_create(property=prop)
            for field, value in details.items():
                setattr(detail, field, value)
            detail.save()
    if 'amenities' in data:
        codes = data['amenities']
        amenities = list(Amenity.objects.filter(code__in=codes, is_active=True))
        if len(amenities) != len(set(codes)):
            raise ValidationError({'amenities': 'Every amenity must be an active canonical code.'})
        PropertyAmenity.objects.filter(property=prop).exclude(amenity__in=amenities).delete()
        for amenity in amenities:
            PropertyAmenity.objects.get_or_create(property=prop, amenity=amenity)
    if 'target' in data:
        values = dict(data['target'])
        if values.get('unit_id'):
            values['unit'] = Unit.objects.get(public_id=values.pop('unit_id'), property=prop)
        if values.get('inventory_item_id'):
            values['inventory_item'] = InventoryItem.objects.get(public_id=values.pop('inventory_item_id'), property=prop)
        ListingTarget.objects.update_or_create(listing=listing, defaults=values)
    if 'space' in data:
        values = dict(data['space'])
        inventory = values.pop('inventory_item', None)
        unit_id = values.pop('unit_id', None)
        unit = (Unit.objects.get(public_id=unit_id, property=prop) if unit_id else
                Unit.objects.create(property=prop, **values))
        target = {'target_type': ListingTarget.UNIT, 'unit': unit,
                  'inventory_item': None, 'capacity': None}
        if inventory:
            item = InventoryItem.objects.create(property=prop, unit=unit, **inventory)
            target = {'target_type': ListingTarget.INVENTORY_ITEM, 'unit': None,
                      'inventory_item': item, 'capacity': None}
        ListingTarget.objects.update_or_create(listing=listing, defaults=target)
    if 'pricing' in data:
        values = dict(data['pricing'])
        PricePlan.objects.filter(listing=listing, status=PricePlan.ACTIVE).update(status=PricePlan.INACTIVE)
        values.setdefault('effective_from', timezone.now())
        PricePlan.objects.create(listing=listing, **values)
    if 'availability' in data:
        values = data['availability']
        listing.availability_records.all().delete()
        if values is not None:
            Availability.objects.create(listing=listing, **values)
    return draft


@transaction.atomic
def reorder_media(*, listing, media_ids, primary_id=None):
    items = list(listing.media_items.filter(id__in=media_ids))
    if len(items) != len(media_ids):
        raise ValidationError({'media_ids': 'Media must belong to this listing.'})
    if primary_id is not None and primary_id not in media_ids:
        raise ValidationError({'primary_id': 'Primary media must be in media_ids.'})
    listing.media_items.update(is_primary=False)
    for order, media_id in enumerate(media_ids):
        ListingMedia.objects.filter(listing=listing, id=media_id).update(
            sort_order=order, is_primary=(media_id == primary_id))
