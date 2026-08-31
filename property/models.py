import os
import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from django.db.models import Q

def property_image_path(instance, filename):
    folder_name = instance.name.replace(" ", "_").lower()
    return os.path.join('properties', folder_name, filename)

class Location(models.Model):
    """Model for storing location data"""
    name = models.CharField(max_length=255, unique=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.name}, {self.city}"
    
    class Meta:
        ordering = ['name']

class Property(models.Model):
    TYPE_PG = 'PG'
    TYPE_APARTMENT = 'APARTMENT'
    TYPE_VILLA = 'VILLA'
    TYPE_OFFICE = 'OFFICE'
    CANONICAL_PROPERTY_TYPES = (TYPE_PG, TYPE_APARTMENT, TYPE_VILLA, TYPE_OFFICE)
    PROPERTY_TYPE_CHOICES = (
        ('PG', 'PG'),
        ('APARTMENT', 'Apartment'),
        ('VILLA', 'Villa'),
        ('OFFICE', 'Office'),
        # Legacy values remain readable during the compatibility window.
        ('Co-living', 'Co-living'),
        ('Rented Building', 'Rented Building'),
        ('Room', 'Room'),
        ('Apartment', 'Apartment'),
        ('Villa', 'Villa'),
        ('Residence', 'Residence'),
    )
    
    GENDER_FILTER_CHOICES = (
        ('Men', 'Men Only'),
        ('Women', 'Women Only'),
        ('Unisex', 'Unisex'),
    )

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    # LEGACY compatibility owner. V2 authorization uses organization.
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='properties')
    organization = models.ForeignKey('organizations.Organization', on_delete=models.PROTECT, related_name='properties')
    name = models.CharField(max_length=255)
    property_type = models.CharField(max_length=50, choices=PROPERTY_TYPE_CHOICES)
    slug = models.SlugField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, default='active', db_index=True)
    locality = models.CharField(max_length=150, blank=True)
    country = models.CharField(max_length=100, default='India')
    postal_code = models.CharField(max_length=20, blank=True)
    timezone = models.CharField(max_length=64, default='Asia/Kolkata')
    currency = models.CharField(max_length=3, default='INR')
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='properties')
    
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    description = models.TextField(blank=True, null=True)
    amenities = models.JSONField(default=list, blank=True)  # Array of amenities
    
    # Pricing and availability
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    rating = models.FloatField(default=4.0)
    
    # Images - main property image
    image = models.ImageField(upload_to=property_image_path, null=True, blank=True)
    
    # Stats
    total_rooms = models.PositiveIntegerField(default=0)
    gender_filter = models.CharField(max_length=20, choices=GENDER_FILTER_CHOICES, default='Unisex')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=('organization', 'property_type')),
            models.Index(fields=('organization', 'status')),
            models.Index(fields=('organization', 'slug')),
        ]
        constraints = [models.UniqueConstraint(fields=('organization', 'slug'), name='unique_property_slug_per_org')]


class CategoryDetailsBase(models.Model):
    expected_property_type = None
    property = models.OneToOneField(Property, on_delete=models.CASCADE)

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if self.property_id and self.property.property_type != self.expected_property_type:
            raise ValidationError({'property': f'{self.__class__.__name__} requires {self.expected_property_type} property type.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class PGDetails(CategoryDetailsBase):
    expected_property_type = Property.TYPE_PG
    GENDER_POLICIES = (('MEN', 'Men'), ('WOMEN', 'Women'), ('UNISEX', 'Unisex'))
    gender_policy = models.CharField(max_length=20, choices=GENDER_POLICIES, default='UNISEX')
    meal_available = models.BooleanField(default=False)
    meal_policy = models.CharField(max_length=255, blank=True)
    curfew_policy = models.CharField(max_length=255, blank=True)
    housekeeping_available = models.BooleanField(default=False)
    laundry_available = models.BooleanField(default=False)
    electricity_policy = models.CharField(max_length=255, blank=True)
    wifi_available = models.BooleanField(default=False)
    visitor_policy = models.CharField(max_length=255, blank=True)
    minimum_stay = models.PositiveIntegerField(null=True, blank=True, help_text='Days')
    notice_period = models.PositiveIntegerField(null=True, blank=True, help_text='Days')


class ApartmentDetails(CategoryDetailsBase):
    expected_property_type = Property.TYPE_APARTMENT
    bedrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    bathrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    balconies = models.PositiveSmallIntegerField(null=True, blank=True)
    furnishing_status = models.CharField(max_length=30, blank=True)
    preferred_tenant_type = models.CharField(max_length=50, blank=True)
    maintenance_charge = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    parking_available = models.BooleanField(default=False)
    floor_number = models.IntegerField(null=True, blank=True)
    total_floors = models.PositiveSmallIntegerField(null=True, blank=True)
    year_built = models.PositiveSmallIntegerField(null=True, blank=True)


class VillaDetails(CategoryDetailsBase):
    expected_property_type = Property.TYPE_VILLA
    bedrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    bathrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    balconies = models.PositiveSmallIntegerField(null=True, blank=True)
    furnishing_status = models.CharField(max_length=30, blank=True)
    parking_capacity = models.PositiveSmallIntegerField(default=0)
    plot_area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    built_up_area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    floors = models.PositiveSmallIntegerField(null=True, blank=True)
    private_garden = models.BooleanField(default=False)
    gated_property = models.BooleanField(default=False)


class OfficeDetails(CategoryDetailsBase):
    expected_property_type = Property.TYPE_OFFICE
    office_type = models.CharField(max_length=40, blank=True)
    total_area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    fitout_status = models.CharField(max_length=30, blank=True)
    total_workstations = models.PositiveIntegerField(null=True, blank=True)
    meeting_rooms = models.PositiveSmallIntegerField(null=True, blank=True)
    cabins = models.PositiveSmallIntegerField(null=True, blank=True)
    parking_capacity = models.PositiveSmallIntegerField(default=0)
    power_backup = models.BooleanField(default=False)
    access_hours = models.CharField(max_length=100, blank=True)
    lease_type = models.CharField(max_length=40, blank=True)


class Unit(models.Model):
    UNIT_TYPES = tuple((value, value.replace('_', ' ').title()) for value in
                       ('ROOM', 'APARTMENT', 'VILLA', 'FLOOR', 'OFFICE_SUITE', 'CABIN', 'DESK_ZONE', 'OTHER'))
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='units')
    parent_unit = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='children')
    legacy_room = models.OneToOneField('rooms.Room', null=True, blank=True, on_delete=models.SET_NULL, related_name='canonical_unit')
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=150, blank=True)
    unit_type = models.CharField(max_length=30, choices=UNIT_TYPES, db_index=True)
    floor = models.CharField(max_length=30, blank=True)
    capacity = models.PositiveIntegerField(default=0)
    area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    area_unit = models.CharField(max_length=20, default='sq_ft')
    status = models.CharField(max_length=20, default='active', db_index=True)
    attributes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('property_id', 'code')
        indexes = [models.Index(fields=('property', 'unit_type')), models.Index(fields=('property', 'status'))]
        constraints = [
            models.UniqueConstraint(fields=('property', 'parent_unit', 'code'), name='unique_unit_code_in_parent'),
            models.UniqueConstraint(fields=('property', 'code'), condition=Q(parent_unit__isnull=True), name='unique_root_unit_code'),
            models.CheckConstraint(condition=Q(capacity__gte=0), name='unit_capacity_nonnegative'),
            models.CheckConstraint(condition=Q(area__isnull=True) | Q(area__gte=0), name='unit_area_nonnegative'),
        ]

    def clean(self):
        if self.parent_unit_id and self.parent_unit.property_id != self.property_id:
            raise ValidationError({'parent_unit': 'Parent unit must belong to the same property.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class InventoryItem(models.Model):
    ITEM_TYPES = tuple((value, value.replace('_', ' ').title()) for value in ('BED', 'DESK', 'PARKING_SLOT', 'LOCKER', 'OTHER'))
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='inventory_items')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='inventory_items')
    item_type = models.CharField(max_length=30, choices=ITEM_TYPES, db_index=True)
    code = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default='active', db_index=True)
    attributes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('unit_id', 'code')
        constraints = [models.UniqueConstraint(fields=('unit', 'code'), name='unique_inventory_code_per_unit')]
        indexes = [models.Index(fields=('unit', 'item_type')), models.Index(fields=('unit', 'status'))]

    def clean(self):
        if self.unit_id and self.unit.property_id != self.property_id:
            raise ValidationError({'property': 'Inventory property must match its unit property.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class PropertyMedia(models.Model):
    MEDIA_TYPES = (('IMAGE', 'Image'), ('VIDEO', 'Video'), ('DOCUMENT', 'Document'), ('OTHER', 'Other'))
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='media_items')
    file = models.FileField(upload_to='property_media/')
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPES, default='IMAGE')
    caption = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('sort_order', 'id')
        indexes = [models.Index(fields=('property', 'sort_order'))]


class Amenity(models.Model):
    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)


class PropertyAmenity(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='property_amenities')
    amenity = models.ForeignKey(Amenity, on_delete=models.PROTECT, related_name='property_links')
    value = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('property', 'amenity'), name='unique_property_amenity')]
        indexes = [models.Index(fields=('property', 'amenity'))]


class LegacyMappingIssue(models.Model):
    """Persistent, reviewable record of legacy values that were not guessed."""
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='legacy_mapping_issues')
    source_field = models.CharField(max_length=80)
    source_value = models.TextField()
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('property', 'source_field', 'source_value'), name='unique_legacy_mapping_issue')]


class RoomConfiguration(models.Model):
    ROOM_TYPE_CHOICES = (
        ('Single Sharing', 'Single Sharing'),
        ('Double Sharing', 'Double Sharing'),
        ('Triple Sharing', 'Triple Sharing'),
        ('Four Sharing', 'Four Sharing'),
        ('Single', 'Single'),
    )

    property = models.ForeignKey(Property, related_name='room_configs', on_delete=models.CASCADE)
    room_type = models.CharField(max_length=50, choices=ROOM_TYPE_CHOICES)
    rent = models.DecimalField(max_digits=10, decimal_places=2)
    deposit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_beds = models.PositiveIntegerField(default=0)
    available_beds = models.PositiveIntegerField(default=0)
    room_image = models.ImageField(upload_to='rooms/', null=True, blank=True)

    def __str__(self):
        return f"{self.property.name} - {self.room_type}"
    
    class Meta:
        ordering = ['room_type']
