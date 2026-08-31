import uuid

from django.conf import settings
from django.db import models


class Organization(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_CHOICES = ((STATUS_ACTIVE, 'Active'), (STATUS_INACTIVE, 'Inactive'))

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    default_currency = models.CharField(max_length=3, default='INR')
    timezone = models.CharField(max_length=64, default='Asia/Kolkata')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class OrganizationMembership(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_INVITED = 'invited'
    STATUS_SUSPENDED = 'suspended'
    STATUS_CHOICES = (
        (STATUS_ACTIVE, 'Active'), (STATUS_INVITED, 'Invited'),
        (STATUS_SUSPENDED, 'Suspended'),
    )

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organization_memberships')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='memberships')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    roles = models.JSONField(default=list, blank=True)
    all_properties = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='organization_invitations_sent')

    class Meta:
        constraints = [models.UniqueConstraint(fields=('user', 'organization'), name='unique_user_organization_membership')]


class PropertyAccess(models.Model):
    membership = models.ForeignKey(OrganizationMembership, on_delete=models.CASCADE, related_name='property_accesses')
    property = models.ForeignKey('property.Property', on_delete=models.CASCADE, related_name='access_grants')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('membership', 'property'), name='unique_membership_property_access')]


class OrganizationPayoutAccount(models.Model):
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name='payout_account')
    payee_name = models.CharField(max_length=255, blank=True)
    upi_id = models.CharField(max_length=255, blank=True)
    bank_account_reference = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PropertyOrganizationHistory(models.Model):
    property = models.ForeignKey('property.Property', on_delete=models.CASCADE, related_name='organization_history')
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='property_history')
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=500, blank=True)
