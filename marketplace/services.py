from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from organizations.access import user_can
from property.models import ApartmentDetails, OfficeDetails, PGDetails, VillaDetails
from .models import Availability, Listing, ListingTarget, PricePlan


DETAIL_RELATIONS = {
    'PG': ('pgdetails', PGDetails),
    'APARTMENT': ('apartmentdetails', ApartmentDetails),
    'VILLA': ('villadetails', VillaDetails),
    'OFFICE': ('officedetails', OfficeDetails),
}


def current_price_queryset(listing, at=None):
    at = at or timezone.now()
    return listing.price_plans.filter(
        status=PricePlan.ACTIVE, effective_from__lte=at,
    ).filter(Q(effective_to__isnull=True) | Q(effective_to__gt=at))


def resolve_current_price(listing, at=None):
    at = at or timezone.now()
    cached = getattr(listing, '_prefetched_objects_cache', {}).get('price_plans')
    if cached is not None:
        plans = [plan for plan in cached if plan.status == PricePlan.ACTIVE and plan.effective_from <= at and
                 (plan.effective_to is None or plan.effective_to > at)][:2]
    else:
        plans = list(current_price_queryset(listing, at)[:2])
    if len(plans) > 1:
        raise ValidationError({'price': 'Conflicting current price plans require correction.'})
    return plans[0] if plans else None


def current_availability(listing, at=None):
    at = at or timezone.now()
    cached = getattr(listing, '_prefetched_objects_cache', {}).get('availability_records')
    if cached is not None:
        records = [record for record in cached if record.start <= at and (record.end is None or record.end > at)]
    else:
        records = list(listing.availability_records.filter(start__lte=at).filter(Q(end__isnull=True) | Q(end__gt=at)).order_by('start', 'id'))
    if not records:
        return None
    status = Availability.AVAILABLE
    if any(record.status == Availability.BLOCKED for record in records):
        status = Availability.BLOCKED
    elif any(record.status == Availability.UNAVAILABLE for record in records):
        status = Availability.UNAVAILABLE
    quantities = [record.quantity for record in records if record.quantity is not None and record.status == Availability.AVAILABLE]
    return {'status': status, 'quantity': min(quantities) if quantities else None}


def validate_listing_for_publish(listing):
    errors = []
    def add(code, field, message):
        errors.append({'code': code, 'field': field, 'message': message})

    if not listing.organization_id or not listing.property_id:
        add('required', 'property', 'Organization and property are required.')
        return errors
    if listing.organization_id != listing.property.organization_id:
        add('invalid_lineage', 'organization', 'Organization must own the property.')
    if listing.category != listing.property.property_type:
        add('category_mismatch', 'category', 'Category must match property type.')
    if not listing.title.strip():
        add('required', 'title', 'Title is required.')
    try:
        listing.target
    except ListingTarget.DoesNotExist:
        add('required', 'target', 'A listing target is required.')
    try:
        price = resolve_current_price(listing)
    except ValidationError:
        price = None
        add('conflicting_price', 'price', 'Current price plans conflict.')
    if price is None and not any(item['code'] == 'conflicting_price' for item in errors):
        add('required', 'price', 'A currently effective price is required.')
    prop = listing.property
    if not prop.address.strip() or not prop.city.strip() or not prop.state.strip():
        add('incomplete_location', 'property.location', 'Address, city, and state are required.')
    relation, model = DETAIL_RELATIONS[listing.category]
    if not model.objects.filter(property=prop).exists():
        add('category_details_required', 'category_details', f'{listing.category} details are required.')
    has_media = listing.media_items.exists() or prop.media_items.exists() or bool(prop.image)
    if not has_media:
        add('media_required', 'media', 'Property or listing media is required.')
    return errors


def unique_listing_slug(title):
    base = slugify(title)[:230] or 'listing'
    candidate, suffix = base, 2
    while Listing.objects.filter(slug=candidate).exists():
        candidate = f'{base[:245-len(str(suffix))]}-{suffix}'
        suffix += 1
    return candidate


@transaction.atomic
def create_listing(*, user, organization, property_obj, data, target_data=None):
    if not user_can(user, 'listing.manage', property_obj):
        raise PermissionError('listing.manage is required.')
    listing = Listing(organization=organization, property=property_obj, created_by=user, **data)
    listing.slug = listing.slug or unique_listing_slug(listing.title)
    listing.save()
    if target_data:
        ListingTarget.objects.create(listing=listing, **target_data)
    return listing


@transaction.atomic
def publish_listing(*, user, listing):
    if not user_can(user, 'listing.publish', listing):
        raise PermissionError('listing.publish is required.')
    errors = validate_listing_for_publish(listing)
    if errors:
        raise PublishValidationError(errors)
    now = timezone.now()
    listing.status = Listing.PUBLISHED
    listing.published_at = listing.published_at or now
    listing.unpublished_at = None
    listing.save(update_fields=('status', 'published_at', 'unpublished_at', 'updated_at'))
    return listing


@transaction.atomic
def pause_listing(*, user, listing):
    if not user_can(user, 'listing.publish', listing):
        raise PermissionError('listing.publish is required.')
    listing.status = Listing.PAUSED
    listing.unpublished_at = timezone.now()
    listing.save(update_fields=('status', 'unpublished_at', 'updated_at'))
    return listing


class PublishValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__('Listing is not publishable.')
