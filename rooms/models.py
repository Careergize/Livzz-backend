from django.db import models
from property.models import Property

class Room(models.Model):
    SHARING_CHOICES = (
        ('Single Sharing', 'Single Sharing'),
        ('Double Sharing', 'Double Sharing'),
        ('Triple Sharing', 'Triple Sharing'),
        ('Four Sharing', 'Four Sharing'),
    )

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='rooms')

    room_number = models.CharField(max_length=20)
    sharing_type = models.CharField(max_length=50, choices=SHARING_CHOICES)

    total_beds = models.IntegerField()
    occupied_beds = models.IntegerField(default=0)

    rent = models.DecimalField(max_digits=10, decimal_places=2)
    deposit = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def available_beds(self):
        return self.total_beds - self.occupied_beds

    def is_full(self):
        return self.occupied_beds >= self.total_beds

    def __str__(self):
        return f"{self.property.name} - Room {self.room_number}"
    
    class Meta:
        ordering = ['room_number']