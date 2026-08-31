from rest_framework import serializers

from organizations.access import permissions_for_membership
from organizations.models import Organization, OrganizationMembership
from property.models import (
    ApartmentDetails, InventoryItem, OfficeDetails, PGDetails, Property,
    PropertyAmenity, PropertyMedia, Unit, VillaDetails,
)


class OrganizationSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='public_id', read_only=True)

    class Meta:
        model = Organization
        fields = ('id', 'name', 'legal_name', 'status', 'default_currency', 'timezone', 'created_at', 'updated_at')


class V2PropertySerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='public_id', read_only=True)
    organization_id = serializers.UUIDField(source='organization.public_id', read_only=True)
    location = serializers.SerializerMethodField()
    category_details = serializers.SerializerMethodField()
    amenities = serializers.SerializerMethodField()
    media = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = ('id', 'organization_id', 'slug', 'property_type', 'name', 'description',
                  'status', 'location', 'timezone', 'currency', 'category_details',
                  'amenities', 'media', 'created_at', 'updated_at')

    def get_location(self, obj):
        return {field: getattr(obj, field) for field in
                ('address', 'locality', 'city', 'state', 'country', 'postal_code', 'latitude', 'longitude')}

    def get_category_details(self, obj):
        mapping = {
            Property.TYPE_PG: (PGDetails, ('gender_policy', 'meal_available', 'meal_policy', 'curfew_policy', 'housekeeping_available', 'laundry_available', 'electricity_policy', 'wifi_available', 'visitor_policy', 'minimum_stay', 'notice_period')),
            Property.TYPE_APARTMENT: (ApartmentDetails, ('bedrooms', 'bathrooms', 'balconies', 'furnishing_status', 'preferred_tenant_type', 'maintenance_charge', 'parking_available', 'floor_number', 'total_floors', 'year_built')),
            Property.TYPE_VILLA: (VillaDetails, ('bedrooms', 'bathrooms', 'balconies', 'furnishing_status', 'parking_capacity', 'plot_area', 'built_up_area', 'floors', 'private_garden', 'gated_property')),
            Property.TYPE_OFFICE: (OfficeDetails, ('office_type', 'total_area', 'fitout_status', 'total_workstations', 'meeting_rooms', 'cabins', 'parking_capacity', 'power_backup', 'access_hours', 'lease_type')),
        }
        config = mapping.get(obj.property_type)
        if not config:
            return None
        detail = config[0].objects.filter(property=obj).first()
        return None if detail is None else {field: getattr(detail, field) for field in config[1]}

    def get_amenities(self, obj):
        return [{'code': link.amenity.code, 'name': link.amenity.name, 'category': link.amenity.category,
                 'value': link.value, 'details': link.details}
                for link in obj.property_amenities.select_related('amenity').all()]

    def get_media(self, obj):
        request = self.context.get('request')
        result = []
        for item in obj.media_items.all():
            url = item.file.url if item.file else None
            result.append({'id': item.pk, 'url': request.build_absolute_uri(url) if request and url else url,
                           'media_type': item.media_type, 'caption': item.caption,
                           'sort_order': item.sort_order, 'is_primary': item.is_primary})
        if not result and obj.image:
            url = obj.image.url
            result.append({'id': None, 'url': request.build_absolute_uri(url) if request else url,
                           'media_type': 'IMAGE', 'caption': '', 'sort_order': 0, 'is_primary': True})
        return result


class PropertyWriteSerializer(serializers.ModelSerializer):
    category_details = serializers.JSONField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Property
        fields = ('slug', 'property_type', 'name', 'description', 'status', 'address', 'locality',
                  'city', 'state', 'country', 'postal_code', 'latitude', 'longitude', 'timezone',
                  'currency', 'category_details')
        extra_kwargs = {'slug': {'required': False, 'allow_null': True}}

    def validate_property_type(self, value):
        if value not in Property.CANONICAL_PROPERTY_TYPES:
            raise serializers.ValidationError('Use PG, APARTMENT, VILLA, or OFFICE.')
        return value

    def validate_latitude(self, value):
        if value is not None and not -90 <= value <= 90:
            raise serializers.ValidationError('Latitude must be between -90 and 90.')
        return value

    def validate_longitude(self, value):
        if value is not None and not -180 <= value <= 180:
            raise serializers.ValidationError('Longitude must be between -180 and 180.')
        return value


class UnitSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='public_id', read_only=True)
    parent_unit_id = serializers.SlugRelatedField(source='parent_unit', slug_field='public_id', queryset=Unit.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Unit
        fields = ('id', 'parent_unit_id', 'code', 'name', 'unit_type', 'floor', 'capacity', 'area',
                  'area_unit', 'status', 'attributes', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')


class InventoryItemSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='public_id', read_only=True)
    unit_id = serializers.SlugRelatedField(source='unit', slug_field='public_id', queryset=Unit.objects.all())

    class Meta:
        model = InventoryItem
        fields = ('id', 'unit_id', 'item_type', 'code', 'status', 'attributes', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')


class MembershipSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='public_id', read_only=True)
    organization = OrganizationSerializer(read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationMembership
        fields = ('id', 'organization', 'status', 'roles', 'permissions', 'all_properties', 'joined_at')

    def get_permissions(self, obj):
        return sorted(permissions_for_membership(obj))
