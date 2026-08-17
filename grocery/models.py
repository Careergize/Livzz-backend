from django.db import models
from django.core.validators import FileExtensionValidator
from property.models import Property

class GroceryExpense(models.Model):
    CATEGORY_CHOICES = [
        ('Vegetables', 'Vegetables'),
        ('Dairy', 'Dairy'),
        ('Groceries', 'Groceries'),
        ('Cleaning', 'Cleaning'),
        ('Staples', 'Staples'),
        ('Other', 'Other'),
    ]

    PAYMENT_MODE_CHOICES = [
        ('UPI', 'UPI'),
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
    ]

    STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Pending', 'Pending'),
    ]

    # Links the expense to a specific property (important for your multi-PG setup)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='grocery_expenses')
    
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    vendor = models.CharField(max_length=255, verbose_name="Vendor/Store Name")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Groceries')
    payment_mode = models.CharField(max_length=50, choices=PAYMENT_MODE_CHOICES, default='UPI')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Paid')
    
    # Receipt Upload handling
    receipt_image = models.ImageField(
        upload_to='receipts/%Y/%m/', 
        null=True, 
        blank=True,
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Grocery Expense"

    def __str__(self):
        return f"{self.vendor} - ₹{self.amount} ({self.date})"