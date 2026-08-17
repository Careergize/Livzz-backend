import os
from django.db import models
from django.conf import settings

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
    PROPERTY_TYPE_CHOICES = (
        ('PG', 'PG'),
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

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='properties')
    name = models.CharField(max_length=255)
    property_type = models.CharField(max_length=50, choices=PROPERTY_TYPE_CHOICES)
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