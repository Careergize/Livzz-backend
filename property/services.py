from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.text import slugify

from organizations.access import user_can
from .models import (
    ApartmentDetails, InventoryItem, OfficeDetails, PGDetails, Property,
    Unit, VillaDetails,
)


DETAIL_MODELS = {
    Property.TYPE_PG: PGDetails,
    Property.TYPE_APARTMENT: ApartmentDetails,
    Property.TYPE_VILLA: VillaDetails,
    Property.TYPE_OFFICE: OfficeDetails,
}


def require_property_access(user, permission, property_obj):
    if not user_can(user, permission, property_obj):
        raise PermissionError(f'{permission} is required for this property.')


def _unique_slug(organization, name, exclude_pk=None):
    base = slugify(name)[:230] or 'property'
    candidate, suffix = base, 2
    query = Property.objects.filter(organization=organization)
    if exclude_pk:
        query = query.exclude(pk=exclude_pk)
    while query.filter(slug=candidate).exists():
        candidate = f'{base[:245-len(str(suffix))]}-{suffix}'
        suffix += 1
    return candidate


def validate_category_details(property_type, category_details):
    if property_type not in Property.CANONICAL_PROPERTY_TYPES:
        raise ValidationError({'property_type': 'Use a canonical property type: PG, APARTMENT, VILLA, or OFFICE.'})
    if category_details is not None and not isinstance(category_details, dict):
        raise ValidationError({'category_details': 'Expected an object.'})
    if category_details is not None:
        allowed = {field.name for field in DETAIL_MODELS[property_type]._meta.fields} - {'id', 'property'}
        unknown = sorted(set(category_details) - allowed)
        if unknown:
            raise ValidationError({'category_details': f'Unknown fields for {property_type}: {", ".join(unknown)}.'})


@transaction.atomic
def create_property(*, user, organization, data, category_details=None):
    if not user_can(user, 'property.manage', organization):
        raise PermissionError('property.manage is required for this organization.')
    validate_category_details(data.get('property_type'), category_details)
    data = dict(data)
    data['organization'] = organization
    data['owner'] = user
    data['slug'] = data.get('slug') or _unique_slug(organization, data['name'])
    prop = Property.objects.create(**data)
    if category_details is not None:
        DETAIL_MODELS[prop.property_type].objects.create(property=prop, **category_details)
    return prop


@transaction.atomic
def update_property(*, user, property_obj, data, category_details=None):
    require_property_access(user, 'property.manage', property_obj)
    new_type = data.get('property_type', property_obj.property_type)
    if 'property_type' in data or category_details is not None:
        validate_category_details(new_type, category_details)
    if new_type != property_obj.property_type:
        existing = [model.__name__ for model in DETAIL_MODELS.values() if model.objects.filter(property=property_obj).exists()]
        if existing:
            raise ValidationError({'property_type': f'Remove or explicitly migrate category details first: {", ".join(existing)}.'})
    for field, value in data.items():
        setattr(property_obj, field, value)
    if 'name' in data and not property_obj.slug:
        property_obj.slug = _unique_slug(property_obj.organization, property_obj.name, property_obj.pk)
    property_obj.full_clean()
    property_obj.save()
    if category_details is not None:
        model = DETAIL_MODELS[new_type]
        detail, _ = model.objects.get_or_create(property=property_obj)
        for field, value in category_details.items():
            setattr(detail, field, value)
        detail.save()
    return property_obj


@transaction.atomic
def create_unit(*, user, property_obj, data):
    require_property_access(user, 'property.manage', property_obj)
    unit = Unit(property=property_obj, **data)
    unit.save()
    return unit


@transaction.atomic
def create_inventory_item(*, user, property_obj, data):
    require_property_access(user, 'property.manage', property_obj)
    item = InventoryItem(property=property_obj, **data)
    item.save()
    return item
