from django.contrib.auth.models import AbstractUser
from django.db import models
import os

def id_proof_path(instance, filename):
    return os.path.join('id_proofs', f"{instance.phone_number}_{filename}")

def profile_image_path(instance, filename):
    return os.path.join('profile_images', f"{instance.phone_number}_{filename}")

class User(AbstractUser):
    ROLE_CHOICES = (
        ('owner', 'Owner'),
        ('staff', 'Staff'),
        ('tenant', 'Tenant'),
        ('seeker', 'Seeker'),
    )
    IDENTITY_CHOICES = (
        ('Aadhar', 'Aadhar'),
        ('PAN', 'PAN'),
        ('Passport', 'Passport'),
        ('Driving License', 'Driving License'),
    )

    phone_number = models.CharField(max_length=15, unique=True)
    whatsapp_number = models.CharField(max_length=15, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='seeker')
    
    # OTP fields
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_reference_id = models.CharField(max_length=50, blank=True, null=True)
    otp_verified = models.BooleanField(default=False)
    
    # Identity verification fields
    identity_type = models.CharField(max_length=50, choices=IDENTITY_CHOICES, blank=True, null=True)
    identity_front_image = models.ImageField(upload_to=id_proof_path, blank=True, null=True)
    identity_back_image = models.ImageField(upload_to=id_proof_path, blank=True, null=True)
    
    # Profile
    profile_image = models.ImageField(upload_to=profile_image_path, blank=True, null=True)
    
    # Owner specific fields
    upi_id = models.CharField(max_length=50, blank=True, null=True)
    payee_name = models.CharField(max_length=255, blank=True, null=True)
    organization_name = models.CharField(max_length=255, blank=True, null=True)

    def is_owner(self):
        return self.role == 'owner'

    def is_staff_user(self):
        return self.role == 'staff'

    def is_tenant(self):
        return self.role == 'tenant'
    
    def is_seeker(self):
        return self.role == 'seeker'

    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class ListerProfile(models.Model):
    OWNER, BROKER, PROPERTY_MANAGER = 'OWNER', 'BROKER', 'PROPERTY_MANAGER'
    LISTER_TYPES = tuple((value, value.replace('_', ' ').title()) for value in
                         (OWNER, BROKER, PROPERTY_MANAGER))
    UNVERIFIED, PENDING, VERIFIED, REJECTED = 'UNVERIFIED', 'PENDING', 'VERIFIED', 'REJECTED'
    VERIFICATION_STATUSES = tuple((value, value.replace('_', ' ').title()) for value in
                                  (UNVERIFIED, PENDING, VERIFIED, REJECTED))

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='lister_profile')
    lister_type = models.CharField(max_length=30, choices=LISTER_TYPES)
    agency_name = models.CharField(max_length=255, blank=True)
    business_phone = models.CharField(max_length=20, blank=True)
    business_email = models.EmailField(blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUSES,
                                           default=UNVERIFIED)
    internal_verification_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
