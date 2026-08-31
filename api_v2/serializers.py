from rest_framework import serializers

from organizations.access import permissions_for_membership
from organizations.models import Organization, OrganizationMembership
from property.models import Property


class OrganizationSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='public_id', read_only=True)

    class Meta:
        model = Organization
        fields = ('id', 'name', 'legal_name', 'status', 'default_currency', 'timezone', 'created_at', 'updated_at')


class V2PropertySerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='public_id', read_only=True)
    organization_id = serializers.UUIDField(source='organization.public_id', read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = Property
        fields = ('id', 'organization_id', 'name', 'property_type', 'address', 'city', 'state',
                  'latitude', 'longitude', 'description', 'amenities', 'price', 'rating',
                  'total_rooms', 'gender_filter', 'is_active', 'created_at', 'updated_at')


class MembershipSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='public_id', read_only=True)
    organization = OrganizationSerializer(read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationMembership
        fields = ('id', 'organization', 'status', 'roles', 'permissions', 'all_properties', 'joined_at')

    def get_permissions(self, obj):
        return sorted(permissions_for_membership(obj))
