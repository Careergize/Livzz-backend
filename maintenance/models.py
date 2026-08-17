from django.db import models
from property.models import Property
from staff.models import Staff
from Tenant.models import Tenant
import os

def ticket_image_path(instance, filename):
    return os.path.join('maintenance_tickets', f"{instance.ticket_id}_{filename}")

class MaintenanceTicket(models.Model):
    # Priorities & Status Choices
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    ]
    
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Resolved', 'Resolved'),
    ]

    CATEGORY_CHOICES = [
        ('Plumbing', 'Plumbing'),
        ('Electrical', 'Electrical'),
        ('Furniture', 'Furniture'),
        ('Security', 'Security'),
        ('General', 'General'),
    ]

    # Connections
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='maintenance_tickets')
    tenant = models.ForeignKey(Tenant, on_delete=models.SET_NULL, null=True, blank=True, related_name='maintenance_requests')
    assigned_staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')

    # Ticket Details
    ticket_id = models.CharField(max_length=20, unique=True, editable=False)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='General')
    room_number = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField()
    
    # Images
    image_urls = models.JSONField(default=list, blank=True)  # Array of image URLs
    
    # Status tracking
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    # Financial tracking
    repair_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            # Auto-generate ID logic
            last_ticket = MaintenanceTicket.objects.all().order_by('id').last()
            new_id = (last_ticket.id + 8400) if last_ticket else 8400
            self.ticket_id = f"tkt_{new_id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_id} - {self.category}"