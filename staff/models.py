from django.db import models
from decimal import Decimal

class Staff(models.Model):
    # Status Choices
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('On Leave', 'On Leave'),
    ]

    # Specific Role Choices
    ROLE_CHOICES = [
        ('Kitchen', 'Kitchen Staff'),
        ('Takecare', 'Takecare / Caretaker'),
        ('Security', 'Security'),
        ('Manager', 'Property Manager'),
        ('Cleaning', 'Housekeeping'),
    ]

    property = models.ForeignKey('property.Property', on_delete=models.CASCADE, related_name='staff_members')
    
    # Personal Info
    name = models.CharField(max_length=200)
    
    # Updated role field with choices
    role = models.CharField(
        max_length=50, 
        choices=ROLE_CHOICES, 
        default='Takecare'
    )
    
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    
    # Work Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    joined_at = models.DateField(auto_now_add=True)

    # Salary Fields
    salary_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('12000.00'), # Set a standard starting default
        help_text="Monthly base salary"
    )
    
    is_paid = models.BooleanField(default=False, help_text="Current month payment status")
    last_paid_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.get_role_display()}) - ₹{self.salary_amount}"

    class Meta:
        verbose_name_plural = "Staff"