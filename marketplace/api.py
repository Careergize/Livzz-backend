from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from api_v2.pagination import V2PageNumberPagination
from api_v2.responses import data_response
from organizations.access import organizations_accessible_to, properties_accessible_to, user_can
from organizations.models import Organization
from property.models import InventoryItem, Property, Unit
from .models import Availability, Listing, ListingMedia, ListingTarget, PricePlan
from .services import (PublishValidationError, create_listing, current_availability,
                       pause_listing, publish_listing, resolve_current_price)


class PricePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricePlan
        fields = ('id', 'amount', 'currency', 'billing_cycle', 'deposit_amount', 'maintenance_amount',
                  'effective_from', 'effective_to', 'minimum_stay', 'status', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')


class AvailabilitySerializer(serializers.ModelSerializer):
    unit_id = serializers.SlugRelatedField(source='unit', slug_field='public_id', queryset=Unit.objects.all(), required=False, allow_null=True)
    inventory_item_id = serializers.SlugRelatedField(source='inventory_item', slug_field='public_id', queryset=InventoryItem.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Availability
        fields = ('id', 'unit_id', 'inventory_item_id', 'start', 'end', 'quantity', 'status', 'created_at')
        read_only_fields = ('created_at',)


class TargetSerializer(serializers.ModelSerializer):
    unit_id = serializers.SlugRelatedField(source='unit', slug_field='public_id', queryset=Unit.objects.all(), required=False, allow_null=True)
    inventory_item_id = serializers.SlugRelatedField(source='inventory_item', slug_field='public_id', queryset=InventoryItem.objects.all(), required=False, allow_null=True)

    class Meta:
        model = ListingTarget
        fields = ('target_type', 'unit_id', 'inventory_item_id', 'capacity')


class ListingManageSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='public_id', read_only=True)
    property_id = serializers.SlugRelatedField(source='property', slug_field='public_id', queryset=Property.objects.all())
    target = TargetSerializer(required=False)

    class Meta:
        model = Listing
        fields = ('id', 'property_id', 'slug', 'category', 'title', 'description', 'status', 'published_at',
                  'unpublished_at', 'target', 'created_at', 'updated_at')
        read_only_fields = ('status', 'published_at', 'unpublished_at', 'created_at', 'updated_at')
        extra_kwargs = {'slug': {'required': False, 'allow_blank': True}}

    def validate(self, attrs):
        prop = attrs.get('property', getattr(self.instance, 'property', None))
        organization = self.context['organization']
        if prop and prop.organization_id != organization.id:
            raise serializers.ValidationError({'property_id': 'Property must belong to the URL organization.'})
        if self.instance and prop != self.instance.property:
            raise serializers.ValidationError({'property_id': 'Listing property cannot be changed.'})
        return attrs


def _file_url(request, field):
    if not field:
        return None
    try:
        return request.build_absolute_uri(field.url) if request else field.url
    except (ValueError, RuntimeError):
        return None


def _public_coordinate(value, minimum, maximum):
    """Return only a valid stored coordinate; never infer a replacement."""
    if value is None or not minimum <= value <= maximum:
        return None
    return value


class PublicListingSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='public_id')
    property = serializers.SerializerMethodField()
    offer = serializers.SerializerMethodField()
    pricing = serializers.SerializerMethodField()
    availability = serializers.SerializerMethodField()
    amenities = serializers.SerializerMethodField()
    media = serializers.SerializerMethodField()
    category_details = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = ('id', 'slug', 'category', 'title', 'description', 'property', 'offer', 'pricing',
                  'availability', 'amenities', 'media', 'category_details', 'published_at')

    def get_property(self, obj):
        prop = obj.property
        return {'id': str(prop.public_id), 'name': prop.name, 'location': {
            'address': prop.address, 'locality': prop.locality or None, 'city': prop.city,
            'state': prop.state, 'country': prop.country, 'postal_code': prop.postal_code or None,
            'latitude': _public_coordinate(prop.latitude, -90, 90),
            'longitude': _public_coordinate(prop.longitude, -180, 180),
        }}

    def get_offer(self, obj):
        target = obj.target
        unit = target.unit or (target.inventory_item.unit if target.inventory_item_id else None)
        return {'target_type': target.target_type, 'unit_type': unit.unit_type if unit else None,
                'capacity': target.capacity if target.target_type == ListingTarget.CAPACITY_POOL else (unit.capacity if unit else None),
                'unit_id': str(unit.public_id) if unit else None,
                'inventory_item_id': str(target.inventory_item.public_id) if target.inventory_item_id else None}

    def get_pricing(self, obj):
        price = resolve_current_price(obj)
        if not price:
            return None
        return {'amount': f'{price.amount:.2f}', 'currency': price.currency, 'billing_cycle': price.billing_cycle,
                'deposit': f'{price.deposit_amount:.2f}',
                'maintenance': f'{price.maintenance_amount:.2f}' if price.maintenance_amount is not None else None,
                'minimum_stay': price.minimum_stay}

    def get_availability(self, obj):
        return current_availability(obj)

    def get_amenities(self, obj):
        return [{'code': link.amenity.code, 'name': link.amenity.name, 'value': link.value or None}
                for link in obj.property.property_amenities.all() if link.amenity.is_active]

    def get_media(self, obj):
        request = self.context.get('request')
        listing_media = list(obj.media_items.all())
        result = []
        if listing_media:
            for item in listing_media:
                source = item.property_media.file if item.property_media_id else item.file
                result.append({'url': _file_url(request, source), 'type': item.property_media.media_type if item.property_media_id else 'IMAGE',
                               'caption': item.caption or (item.property_media.caption if item.property_media_id else ''), 'is_primary': item.is_primary})
        else:
            prop_media = list(obj.property.media_items.all())
            for item in prop_media:
                result.append({'url': _file_url(request, item.file), 'type': item.media_type, 'caption': item.caption, 'is_primary': item.is_primary})
            if not result and obj.property.image:
                result.append({'url': _file_url(request, obj.property.image), 'type': 'IMAGE', 'caption': '', 'is_primary': True})
        if result and not any(item['is_primary'] for item in result):
            result[0]['is_primary'] = True
        return result

    def get_category_details(self, obj):
        relation = {'PG': 'pgdetails', 'APARTMENT': 'apartmentdetails', 'VILLA': 'villadetails', 'OFFICE': 'officedetails'}[obj.category]
        detail = getattr(obj.property, relation, None)
        if detail is None:
            return None
        excluded = {'id', 'property'}
        return {field.name: getattr(detail, field.name) for field in detail._meta.fields if field.name not in excluded}


def public_queryset(request, category=None):
    now = timezone.now()
    current_prices = PricePlan.objects.filter(listing=OuterRef('pk'), status=PricePlan.ACTIVE, effective_from__lte=now).filter(Q(effective_to__isnull=True) | Q(effective_to__gt=now))
    qs = Listing.objects.filter(status=Listing.PUBLISHED).select_related(
        'property', 'target__unit', 'target__inventory_item__unit', 'property__pgdetails',
        'property__apartmentdetails', 'property__villadetails', 'property__officedetails',
    ).prefetch_related('price_plans', 'availability_records', 'media_items__property_media',
                       'property__media_items', 'property__property_amenities__amenity')
    qs = qs.annotate(
        current_amount=Subquery(current_prices.values('amount')[:1]),
        current_minimum_stay=Subquery(current_prices.values('minimum_stay')[:1]),
        has_current_price=Exists(current_prices),
    ).filter(has_current_price=True)
    if category:
        qs = qs.filter(category=category)
    params = request.query_params
    if params.get('city'):
        qs = qs.filter(property__city__iexact=params['city'])
    if params.get('locality'):
        qs = qs.filter(property__locality__iexact=params['locality'])
    if params.get('min_price'):
        qs = qs.filter(current_amount__gte=params['min_price'])
    if params.get('max_price'):
        qs = qs.filter(current_amount__lte=params['max_price'])
    if params.get('amenities'):
        for code in filter(None, params['amenities'].split(',')):
            qs = qs.filter(property__property_amenities__amenity__code=code)
    if params.get('availability'):
        active = Availability.objects.filter(listing=OuterRef('pk'), start__lte=now).filter(Q(end__isnull=True) | Q(end__gt=now))
        wanted = params['availability'].upper()
        if wanted == Availability.AVAILABLE:
            qs = qs.annotate(has_available=Exists(active.filter(status=Availability.AVAILABLE))).filter(has_available=True)
        elif wanted in (Availability.BLOCKED, Availability.UNAVAILABLE):
            qs = qs.annotate(has_state=Exists(active.filter(status=wanted))).filter(has_state=True)
    specific = {
        'gender_policy': 'property__pgdetails__gender_policy',
        'sharing': 'target__capacity' if category == 'PG' else None,
        'meals': 'property__pgdetails__meal_available',
        'minimum_stay': 'current_minimum_stay' if category == 'PG' else None,
        'bedrooms': {'APARTMENT': 'property__apartmentdetails__bedrooms', 'VILLA': 'property__villadetails__bedrooms'}.get(category),
        'preferred_tenant': 'property__apartmentdetails__preferred_tenant_type' if category == 'APARTMENT' else None,
        'parking': 'property__apartmentdetails__parking_available' if category == 'APARTMENT' else None,
        'office_type': 'property__officedetails__office_type' if category == 'OFFICE' else None,
        'lease_type': 'property__officedetails__lease_type' if category == 'OFFICE' else None,
        'furnishing': ({'APARTMENT': 'property__apartmentdetails__furnishing_status',
                        'VILLA': 'property__villadetails__furnishing_status',
                        'OFFICE': 'property__officedetails__fitout_status'}.get(category)),
        'fit_out': 'property__officedetails__fitout_status' if category == 'OFFICE' else None,
        'area': 'property__officedetails__total_area' if category == 'OFFICE' else None,
        'capacity': {'PG': 'target__capacity', 'OFFICE': 'property__officedetails__total_workstations'}.get(category),
    }
    for param, field in specific.items():
        if field and params.get(param) is not None:
            value = params[param]
            if param in ('meals', 'parking'):
                value = value.lower() in ('1', 'true', 'yes')
            qs = qs.filter(**{field: value})
    if category in ('VILLA', 'OFFICE') and params.get('parking') is not None:
        field = 'property__villadetails__parking_capacity' if category == 'VILLA' else 'property__officedetails__parking_capacity'
        qs = qs.filter(**({f'{field}__gt': 0} if params['parking'].lower() in ('1', 'true', 'yes') else {field: 0}))
    if category == 'OFFICE':
        if params.get('min_area'):
            qs = qs.filter(property__officedetails__total_area__gte=params['min_area'])
        if params.get('max_area'):
            qs = qs.filter(property__officedetails__total_area__lte=params['max_area'])
    ordering = {'PRICE_LOW': ('current_amount', 'id'), 'PRICE_HIGH': ('-current_amount', 'id'), 'NEWEST': ('-published_at', 'id')}
    qs = qs.order_by(*ordering.get(params.get('sort', '').upper(), ('-published_at', '-created_at', 'id')))
    return qs.distinct()


class PublicListingListView(APIView):
    permission_classes = [AllowAny]
    category = None

    def get(self, request):
        paginator = V2PageNumberPagination()
        page = paginator.paginate_queryset(public_queryset(request, self.category), request)
        return paginator.get_paginated_response(PublicListingSerializer(page, many=True, context={'request': request}).data)


class PublicListingDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        listing = get_object_or_404(public_queryset(request), slug=slug)
        return data_response(PublicListingSerializer(listing, context={'request': request}).data)


class OrganizationListingMixin:
    permission_classes = [IsAuthenticated]

    def organization(self):
        return get_object_or_404(organizations_accessible_to(self.request.user), public_id=self.kwargs['organization_id'])

    def listings(self, permission='listing.view'):
        organization = self.organization()
        properties = properties_accessible_to(self.request.user, permission).filter(organization=organization)
        return Listing.objects.filter(organization=organization, property__in=properties).select_related('property', 'target__unit', 'target__inventory_item')

    def listing(self, permission='listing.view'):
        return get_object_or_404(self.listings(permission), public_id=self.kwargs['listing_id'])


class OrganizationListingListView(OrganizationListingMixin, APIView):
    def get(self, request, organization_id):
        paginator = V2PageNumberPagination()
        page = paginator.paginate_queryset(self.listings(), request)
        return paginator.get_paginated_response(ListingManageSerializer(page, many=True, context={'organization': self.organization()}).data)

    @transaction.atomic
    def post(self, request, organization_id):
        org = self.organization()
        serializer = ListingManageSerializer(data=request.data, context={'organization': org})
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        prop, target = data.pop('property'), data.pop('target', None)
        if not user_can(request.user, 'listing.manage', prop):
            raise PermissionDenied('listing.manage is required.')
        try:
            listing = create_listing(user=request.user, organization=org, property_obj=prop, data=data, target_data=target)
        except (DjangoValidationError, IntegrityError) as exc:
            raise ValidationError(getattr(exc, 'message_dict', str(exc)))
        return data_response(ListingManageSerializer(listing, context={'organization': org}).data, status=201)


class OrganizationListingDetailView(OrganizationListingMixin, APIView):
    def get(self, request, organization_id, listing_id):
        listing = self.listing()
        return data_response(ListingManageSerializer(listing, context={'organization': self.organization()}).data)

    @transaction.atomic
    def patch(self, request, organization_id, listing_id):
        listing = self.listing('listing.manage')
        serializer = ListingManageSerializer(listing, data=request.data, partial=True, context={'organization': self.organization()})
        serializer.is_valid(raise_exception=True)
        target = serializer.validated_data.pop('target', None)
        try:
            listing = serializer.save()
            if target is not None:
                ListingTarget.objects.update_or_create(listing=listing, defaults=target)
        except (DjangoValidationError, IntegrityError) as exc:
            raise ValidationError(getattr(exc, 'message_dict', str(exc)))
        return data_response(ListingManageSerializer(listing, context={'organization': self.organization()}).data)


class ListingActionView(OrganizationListingMixin, APIView):
    action = None

    def post(self, request, organization_id, listing_id):
        listing = self.listing('listing.publish')
        try:
            listing = publish_listing(user=request.user, listing=listing) if self.action == 'publish' else pause_listing(user=request.user, listing=listing)
        except PublishValidationError as exc:
            from rest_framework.response import Response
            return Response({'errors': exc.errors}, status=400)
        return data_response(ListingManageSerializer(listing, context={'organization': self.organization()}).data)


class ListingChildrenView(OrganizationListingMixin, APIView):
    model = None
    serializer_class = None
    related_name = None

    def get(self, request, organization_id, listing_id):
        listing = self.listing()
        records = getattr(listing, self.related_name).all()
        return data_response(self.serializer_class(records, many=True).data)

    @transaction.atomic
    def post(self, request, organization_id, listing_id):
        listing = self.listing('listing.manage')
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            record = self.model(listing=listing, **serializer.validated_data)
            record.save()
        except (DjangoValidationError, IntegrityError) as exc:
            raise ValidationError(getattr(exc, 'message_dict', str(exc)))
        return data_response(self.serializer_class(record).data, status=201)


class ListingPriceView(ListingChildrenView):
    model, serializer_class, related_name = PricePlan, PricePlanSerializer, 'price_plans'


class ListingAvailabilityView(ListingChildrenView):
    model, serializer_class, related_name = Availability, AvailabilitySerializer, 'availability_records'
