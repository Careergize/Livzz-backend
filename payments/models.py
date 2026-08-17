import uuid
from django.db import models
from django.utils import timezone
from property.models import Property
from Tenant.models import Tenant


class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('SUCCESSFUL', 'Successful'),
        ('FAILED', 'Failed'),
        ('PENDING', 'Pending'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('UPI', 'UPI'),
        ('CASH', 'Cash'),
        ('TRANSFER', 'Bank Transfer'),
    ]

    # Links
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='payments')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='income')
    
    # Details
    transaction_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    month_for = models.CharField(max_length=20)  # e.g., "May 2026"
    
    # Receipt/Notes
    notes = models.TextField(blank=True, null=True)
    receipt_url = models.URLField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = str(uuid.uuid4())
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tenant.full_name} - ₹{self.amount} ({self.month_for})"
    
    class Meta:
        ordering = ['-payment_date']


class Complaint(models.Model):
    STATUS = [
        ('PENDING', 'Pending'),
        ('RESOLVED', 'Resolved'),
        ('IN_PROGRESS', 'In Progress'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    reply = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']


class Notification(models.Model):
    TYPES = [
        ('PAYMENT', 'Payment'),
        ('COMPLAINT', 'Complaint'),
        ('REPLY', 'Reply'),
        ('MAINTENANCE', 'Maintenance'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']