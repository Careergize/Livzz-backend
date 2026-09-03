from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response

from organizations.access import memberships_for, organizations_accessible_to, properties_accessible_to, user_can
from organizations.models import Organization
from property.models import InventoryItem, Property, Unit
from property.services import create_inventory_item, create_property, create_unit, update_property
from .pagination import V2PageNumberPagination
from .responses import data_response
from .serializers import (InventoryItemSerializer, MembershipSerializer, OrganizationSerializer,
                          PropertyWriteSerializer, UnitSerializer, V2PropertySerializer)


class V2APIView(APIView):
    def handle_exception(self, exc):
        if isinstance(exc, PermissionError):
            exc = PermissionDenied(str(exc))
        elif isinstance(exc, DjangoValidationError):
            exc = ValidationError(getattr(exc, 'message_dict', exc.messages))
        elif isinstance(exc, IntegrityError):
            exc = ValidationError('The request violates a uniqueness or integrity constraint.')
        response = super().handle_exception(exc)
        detail = response.data.get('detail') if isinstance(response.data, dict) else None
        code = getattr(detail, 'code', None) or getattr(exc, 'default_code', 'error')
        message = str(detail if detail is not None else exc)
        response.data = {'errors': [{'code': code, 'field': None, 'message': message}]}
        return response


class MeView(V2APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .self_service import user_data
        memberships = memberships_for(request.user).select_related('organization')
        user = request.user
        return data_response({'user': user_data(user),
                              'memberships': MembershipSerializer(memberships, many=True).data})


class MembershipListView(V2APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = memberships_for(request.user).select_related('organization')
        return data_response(MembershipSerializer(memberships, many=True).data)


class OrganizationListView(V2APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = organizations_accessible_to(request.user).order_by('name')
        paginator = V2PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(OrganizationSerializer(page, many=True).data)


class OrganizationDetailView(V2APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        organization = get_object_or_404(organizations_accessible_to(request.user), public_id=organization_id)
        return data_response(OrganizationSerializer(organization).data)


class OrganizationPropertyListView(V2APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        organization = get_object_or_404(organizations_accessible_to(request.user), public_id=organization_id)
        queryset = (properties_accessible_to(request.user).filter(organization=organization)
                    .select_related('organization').prefetch_related('media_items', 'property_amenities__amenity')
                    .order_by('-created_at'))
        paginator = V2PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(V2PropertySerializer(page, many=True, context={'request': request}).data)

    def post(self, request, organization_id):
        organization = get_object_or_404(organizations_accessible_to(request.user), public_id=organization_id)
        if not user_can(request.user, 'property.manage', organization):
            raise PermissionDenied('property.manage is required for this organization.')
        serializer = PropertyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        details = values.pop('category_details', None)
        prop = create_property(user=request.user, organization=organization, data=values, category_details=details)
        return data_response(V2PropertySerializer(prop, context={'request': request}).data, status=201)


class OrganizationPropertyDetailView(V2APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, organization_id, property_id, permission='property.view'):
        organization = get_object_or_404(organizations_accessible_to(request.user), public_id=organization_id)
        queryset = (properties_accessible_to(request.user, permission).filter(organization=organization)
                    .select_related('organization').prefetch_related('media_items', 'property_amenities__amenity'))
        return get_object_or_404(queryset, public_id=property_id)

    def get(self, request, organization_id, property_id):
        prop = self.get_object(request, organization_id, property_id)
        return data_response(V2PropertySerializer(prop, context={'request': request}).data)

    def patch(self, request, organization_id, property_id):
        prop = self.get_object(request, organization_id, property_id, 'property.manage')
        serializer = PropertyWriteSerializer(prop, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        marker = object()
        details = values.pop('category_details', marker)
        prop = update_property(user=request.user, property_obj=prop, data=values,
                               category_details=None if details is marker else details)
        return data_response(V2PropertySerializer(prop, context={'request': request}).data)


class PropertyScopedView(V2APIView):
    permission_classes = [IsAuthenticated]

    def property(self, request, organization_id, property_id, permission='property.view'):
        organization = get_object_or_404(organizations_accessible_to(request.user), public_id=organization_id)
        return get_object_or_404(properties_accessible_to(request.user, permission).filter(organization=organization), public_id=property_id)


class UnitListView(PropertyScopedView):
    def get(self, request, organization_id, property_id):
        prop = self.property(request, organization_id, property_id)
        return data_response(UnitSerializer(prop.units.select_related('parent_unit').all(), many=True).data)

    def post(self, request, organization_id, property_id):
        prop = self.property(request, organization_id, property_id, 'property.manage')
        serializer = UnitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        unit = create_unit(user=request.user, property_obj=prop, data=serializer.validated_data)
        return data_response(UnitSerializer(unit).data, status=201)


class UnitDetailView(PropertyScopedView):
    def object(self, request, organization_id, property_id, unit_id, permission):
        prop = self.property(request, organization_id, property_id, permission)
        return get_object_or_404(Unit.objects.filter(property=prop), public_id=unit_id)

    def get(self, request, organization_id, property_id, unit_id):
        return data_response(UnitSerializer(self.object(request, organization_id, property_id, unit_id, 'property.view')).data)

    def patch(self, request, organization_id, property_id, unit_id):
        unit = self.object(request, organization_id, property_id, unit_id, 'property.manage')
        serializer = UnitSerializer(unit, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(unit, field, value)
        unit.save()
        return data_response(UnitSerializer(unit).data)


class InventoryListView(PropertyScopedView):
    def get(self, request, organization_id, property_id, unit_id=None):
        prop = self.property(request, organization_id, property_id)
        queryset = prop.inventory_items.select_related('unit')
        if unit_id:
            queryset = queryset.filter(unit__public_id=unit_id)
        return data_response(InventoryItemSerializer(queryset.all(), many=True).data)

    def post(self, request, organization_id, property_id, unit_id=None):
        prop = self.property(request, organization_id, property_id, 'property.manage')
        payload = request.data.copy()
        if unit_id:
            payload['unit_id'] = str(unit_id)
        serializer = InventoryItemSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        item = create_inventory_item(user=request.user, property_obj=prop, data=serializer.validated_data)
        return data_response(InventoryItemSerializer(item).data, status=201)
