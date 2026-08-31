from django.db import migrations
from django.utils.text import slugify


AMENITIES = {
    'wifi': ('Wi-Fi', 'connectivity'),
    'parking': ('Parking', 'transport'),
    'air_conditioning': ('Air conditioning', 'comfort'),
    'power_backup': ('Power backup', 'utilities'),
    'gym': ('Gym', 'wellness'),
    'laundry': ('Laundry', 'services'),
    'housekeeping': ('Housekeeping', 'services'),
    'security': ('Security', 'safety'),
    'cctv': ('CCTV', 'safety'),
}
ALIASES = {
    'wi-fi': 'wifi', 'wi fi': 'wifi', 'wifi': 'wifi', 'parking': 'parking',
    'ac': 'air_conditioning', 'air conditioning': 'air_conditioning',
    'power backup': 'power_backup', 'gym': 'gym', 'laundry': 'laundry',
    'housekeeping': 'housekeeping', 'security': 'security', 'cctv': 'cctv',
}


def forward(apps, schema_editor):
    Property = apps.get_model('property', 'Property')
    Room = apps.get_model('rooms', 'Room')
    Unit = apps.get_model('property', 'Unit')
    Amenity = apps.get_model('property', 'Amenity')
    PropertyAmenity = apps.get_model('property', 'PropertyAmenity')
    Issue = apps.get_model('property', 'LegacyMappingIssue')

    amenity_rows = {}
    for code, (name, category) in AMENITIES.items():
        amenity_rows[code], _ = Amenity.objects.get_or_create(code=code, defaults={'name': name, 'category': category})

    for prop in Property.objects.all().iterator():
        base = slugify(prop.name)[:230] or f'property-{prop.pk}'
        candidate, suffix = base, 2
        while Property.objects.filter(organization_id=prop.organization_id, slug=candidate).exclude(pk=prop.pk).exists():
            candidate = f'{base[:245-len(str(suffix))]}-{suffix}'
            suffix += 1
        prop.slug = candidate
        if prop.property_type == 'Apartment':
            prop.property_type = 'APARTMENT'
        elif prop.property_type == 'Villa':
            prop.property_type = 'VILLA'
        elif prop.property_type not in ('PG', 'APARTMENT', 'VILLA', 'OFFICE'):
            Issue.objects.get_or_create(property=prop, source_field='property_type', source_value=prop.property_type,
                                        defaults={'reason': 'No confident canonical Phase 2 mapping.'})
        prop.save(update_fields=('slug', 'property_type'))

        values = prop.amenities if isinstance(prop.amenities, list) else []
        for raw in values:
            if not isinstance(raw, str):
                Issue.objects.get_or_create(property=prop, source_field='amenities', source_value=repr(raw),
                                            defaults={'reason': 'Amenity is not a string.'})
                continue
            code = ALIASES.get(raw.strip().lower())
            if code:
                PropertyAmenity.objects.get_or_create(property=prop, amenity=amenity_rows[code])
            else:
                Issue.objects.get_or_create(property=prop, source_field='amenities', source_value=raw,
                                            defaults={'reason': 'No confident canonical amenity mapping.'})

    for room in Room.objects.select_related('property').all().iterator():
        code = room.room_number
        if Unit.objects.filter(property_id=room.property_id, parent_unit__isnull=True, code=code).exists():
            Issue.objects.get_or_create(property_id=room.property_id, source_field='room.room_number', source_value=code,
                                        defaults={'reason': f'Duplicate room code; Room {room.pk} received a disambiguated Unit code.'})
            code = f'{code}-legacy-{room.pk}'
        Unit.objects.get_or_create(legacy_room_id=room.pk, defaults={
            'property_id': room.property_id, 'code': code, 'name': f'Room {room.room_number}',
            'unit_type': 'ROOM', 'capacity': max(room.total_beds, 0),
            'status': 'active' if room.is_active else 'inactive',
            'attributes': {},
        })


def backward(apps, schema_editor):
    Unit = apps.get_model('property', 'Unit')
    Unit.objects.filter(legacy_room_id__isnull=False).delete()


class Migration(migrations.Migration):
    dependencies = [('property', '0005_amenity_apartmentdetails_inventoryitem_and_more')]
    operations = [migrations.RunPython(forward, backward)]
