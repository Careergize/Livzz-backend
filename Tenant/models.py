# tenants/models.py
from django.db import models
from django.conf import settings
from rooms.models import Room
import os

def id_proof_path(instance, filename):
    return os.path.join('id_proofs', f"{instance.phone}_{filename}")

class Tenant(models.Model):
    ID_PROOF_CHOICES = (
        ('Aadhar', 'Aadhar'),
        ('PAN', 'PAN'),
        ('Passport', 'Passport'),
        ('Driving License', 'Driving License'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tenant_profile'
    )

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15)
    whatsapp_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    property = models.ForeignKey('property.Property', on_delete=models.CASCADE, related_name='tenants', null=True, blank=True)
    
    join_date = models.DateField()
    rent_date = models.DateField(null=True, blank=True)
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2)
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    
    id_proof_type = models.CharField(max_length=50, choices=ID_PROOF_CHOICES)
    id_proof_image = models.ImageField(upload_to=id_proof_path, null=True, blank=True)
    
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    
    is_paid = models.BooleanField(default=False, verbose_name="Rent Paid Status")
    status = models.CharField(max_length=20, choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name
    
    class Meta:
        ordering = ['-created_at']


class Booking(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('upcoming', 'Upcoming'),
        ('past', 'Past'),
        ('cancelled', 'Cancelled'),
    )
    
    booking_id = models.CharField(max_length=50, unique=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='bookings')
    property = models.ForeignKey('property.Property', on_delete=models.CASCADE, related_name='bookings')
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    room_type = models.CharField(max_length=100)
    
    check_in_date = models.DateField()
    check_out_date = models.DateField(null=True, blank=True)
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    deposit = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Booking {self.booking_id} - {self.tenant.full_name}"
    
    class Meta:
        ordering = ['-created_at']