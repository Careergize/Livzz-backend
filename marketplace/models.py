import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from property.models import InventoryItem, Property, PropertyMedia, Unit


class Listing(models.Model):
    CATEGORIES = tuple((value, value.title()) for value in Property.CANONICAL_PROPERTY_TYPES)
    DRAFT, PUBLISHED, PAUSED, ARCHIVED = 'DRAFT', 'PUBLISHED', 'PAUSED', 'ARCHIVED'
    STATUSES = tuple((value, value.title()) for value in (DRAFT, PUBLISHED, PAUSED, ARCHIVED))

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    organization = models.ForeignKey('organizations.Organization', on_delete=models.PROTECT, related_name='listings')
    property = models.ForeignKey(Property, on_delete=models.PROTECT, related_name='listings')
    slug = models.SlugField(max_length=255, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORIES, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default=DRAFT, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    unpublished_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='created_listings')
    lister_profile = models.ForeignKey('accounts.ListerProfile', null=True, blank=True,
                                       on_delete=models.PROTECT, related_name='listings')
    legacy_source = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-published_at', '-created_at', 'id')
        indexes = [
            models.Index(fields=('status', 'category')),
            models.Index(fields=('property', 'status')),
            models.Index(fields=('organization', 'status')),
        ]

    def clean(self):
        if self.property_id and self.organization_id != self.property.organization_id:
            raise ValidationError({'organization': 'Listing organization must own the property.'})
        if self.property_id and self.category != self.property.property_type:
            raise ValidationError({'category': 'Listing category must match the canonical property type.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class ListingTarget(models.Model):
    PROPERTY, UNIT, INVENTORY_ITEM, CAPACITY_POOL = 'PROPERTY', 'UNIT', 'INVENTORY_ITEM', 'CAPACITY_POOL'
    TARGET_TYPES = tuple((value, value.replace('_', ' ').title()) for value in (PROPERTY, UNIT, INVENTORY_ITEM, CAPACITY_POOL))

    listing = models.OneToOneField(Listing, on_delete=models.CASCADE, related_name='target')
    target_type = models.CharField(max_length=30, choices=TARGET_TYPES)
    unit = models.ForeignKey(Unit, null=True, blank=True, on_delete=models.PROTECT, related_name='listing_targets')
    inventory_item = models.ForeignKey(InventoryItem, null=True, blank=True, on_delete=models.PROTECT, related_name='listing_targets')
    capacity = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=(
            Q(target_type='PROPERTY', unit__isnull=True, inventory_item__isnull=True, capacity__isnull=True) |
            Q(target_type='UNIT', unit__isnull=False, inventory_item__isnull=True, capacity__isnull=True) |
            Q(target_type='INVENTORY_ITEM', unit__isnull=True, inventory_item__isnull=False, capacity__isnull=True) |
            Q(target_type='CAPACITY_POOL', unit__isnull=False, inventory_item__isnull=True, capacity__gt=0)
        ), name='valid_listing_target_shape')]

    def clean(self):
        errors = {}
        if self.target_type == self.PROPERTY and (self.unit_id or self.inventory_item_id or self.capacity is not None):
            errors['target_type'] = 'Property targets cannot specify a unit, inventory item, or capacity.'
        elif self.target_type == self.UNIT and (not self.unit_id or self.inventory_item_id or self.capacity is not None):
            errors['target_type'] = 'Unit targets require only a unit.'
        elif self.target_type == self.INVENTORY_ITEM and (not self.inventory_item_id or self.unit_id or self.capacity is not None):
            errors['target_type'] = 'Inventory targets require only an inventory item.'
        elif self.target_type == self.CAPACITY_POOL and (not self.unit_id or self.inventory_item_id or not self.capacity):
            errors['target_type'] = 'Capacity-pool targets require a unit and positive capacity.'
        if self.unit_id and self.unit.property_id != self.listing.property_id:
            errors['unit'] = 'Target unit must belong to the listing property.'
        if self.inventory_item_id and self.inventory_item.property_id != self.listing.property_id:
            errors['inventory_item'] = 'Target inventory item must belong to the listing property.'
        if self.target_type == self.CAPACITY_POOL and self.unit_id and self.capacity and self.unit.capacity and self.capacity > self.unit.capacity:
            errors['capacity'] = 'Target capacity cannot exceed unit capacity.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class PricePlan(models.Model):
    MONTHLY, DAILY, WEEKLY, ONE_TIME, CUSTOM = 'MONTHLY', 'DAILY', 'WEEKLY', 'ONE_TIME', 'CUSTOM'
    BILLING_CYCLES = tuple((value, value.replace('_', ' ').title()) for value in (MONTHLY, DAILY, WEEKLY, ONE_TIME, CUSTOM))
    ACTIVE, INACTIVE = 'ACTIVE', 'INACTIVE'
    STATUSES = ((ACTIVE, 'Active'), (INACTIVE, 'Inactive'))

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='price_plans')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLES, default=MONTHLY)
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    maintenance_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    effective_from = models.DateTimeField()
    effective_to = models.DateTimeField(null=True, blank=True)
    minimum_stay = models.PositiveIntegerField(null=True, blank=True, help_text='Days')
    status = models.CharField(max_length=20, choices=STATUSES, default=ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-effective_from', '-id')
        indexes = [models.Index(fields=('listing', 'status', 'effective_from', 'effective_to'))]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gte=0), name='price_amount_nonnegative'),
            models.CheckConstraint(condition=Q(deposit_amount__gte=0), name='price_deposit_nonnegative'),
            models.CheckConstraint(condition=Q(maintenance_amount__isnull=True) | Q(maintenance_amount__gte=0), name='price_maintenance_nonnegative'),
            models.CheckConstraint(condition=Q(effective_to__isnull=True) | Q(effective_to__gt=models.F('effective_from')), name='price_valid_period'),
        ]

    def clean(self):
        errors = {}
        if self.effective_to and self.effective_to <= self.effective_from:
            errors['effective_to'] = 'Must be after effective_from.'
        if self.status == self.ACTIVE and self.listing_id:
            overlap = PricePlan.objects.filter(listing_id=self.listing_id, status=self.ACTIVE).exclude(pk=self.pk)
            overlap = overlap.filter(Q(effective_to__isnull=True) | Q(effective_to__gt=self.effective_from))
            if self.effective_to:
                overlap = overlap.filter(effective_from__lt=self.effective_to)
            if overlap.exists():
                errors['effective_from'] = 'Active price-plan periods may not overlap.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.currency = self.currency.upper()
        self.full_clean()
        return super().save(*args, **kwargs)


class Availability(models.Model):
    AVAILABLE, BLOCKED, UNAVAILABLE = 'AVAILABLE', 'BLOCKED', 'UNAVAILABLE'
    STATUSES = tuple((value, value.title()) for value in (AVAILABLE, BLOCKED, UNAVAILABLE))

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='availability_records')
    unit = models.ForeignKey(Unit, null=True, blank=True, on_delete=models.PROTECT, related_name='availability_records')
    inventory_item = models.ForeignKey(InventoryItem, null=True, blank=True, on_delete=models.PROTECT, related_name='availability_records')
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('start', 'id')
        indexes = [models.Index(fields=('listing', 'status', 'start', 'end'))]
        constraints = [
            models.CheckConstraint(condition=Q(end__isnull=True) | Q(end__gt=models.F('start')), name='availability_valid_period'),
            models.CheckConstraint(condition=Q(quantity__isnull=True) | Q(quantity__gt=0), name='availability_quantity_positive'),
        ]

    def clean(self):
        errors = {}
        if self.end and self.end <= self.start:
            errors['end'] = 'Must be after start.'
        if self.unit_id and self.unit.property_id != self.listing.property_id:
            errors['unit'] = 'Availability unit must belong to the listing property.'
        if self.inventory_item_id and self.inventory_item.property_id != self.listing.property_id:
            errors['inventory_item'] = 'Availability inventory item must belong to the listing property.'
        if self.unit_id and self.inventory_item_id and self.inventory_item.unit_id != self.unit_id:
            errors['inventory_item'] = 'Inventory item must belong to the selected unit.'
        if self.quantity is not None and self.listing.target.target_type != ListingTarget.CAPACITY_POOL:
            errors['quantity'] = 'Quantity is only valid for capacity-pool listings.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class ListingMedia(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='media_items')
    property_media = models.ForeignKey(PropertyMedia, null=True, blank=True, on_delete=models.PROTECT, related_name='listing_uses')
    file = models.FileField(upload_to='listing_media/', null=True, blank=True)
    caption = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('sort_order', 'id')
        indexes = [models.Index(fields=('listing', 'sort_order'))]
        constraints = [
            models.CheckConstraint(condition=(Q(property_media__isnull=False, file='') | Q(property_media__isnull=True) & ~Q(file='')), name='listing_media_one_source'),
            models.UniqueConstraint(fields=('listing',), condition=Q(is_primary=True), name='one_primary_listing_media'),
        ]

    def clean(self):
        if bool(self.property_media_id) == bool(self.file):
            raise ValidationError('Choose exactly one media source.')
        if self.property_media_id and self.property_media.property_id != self.listing.property_id:
            raise ValidationError({'property_media': 'Media must belong to the listing property.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class ListingDraft(models.Model):
    STEPS = tuple((value, value.replace('_', ' ').title()) for value in (
        'PROPERTY_TYPE', 'LOCATION', 'PROPERTY_DETAILS', 'SPACE_DETAILS', 'AMENITIES',
        'MEDIA', 'PRICING', 'AVAILABILITY', 'PREVIEW', 'PUBLISH'))
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    listing = models.OneToOneField(Listing, on_delete=models.CASCADE, related_name='draft')
    current_step = models.CharField(max_length=30, choices=STEPS, default='PROPERTY_TYPE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
