from django.db import models
from property.models import Property
from rooms.models import Room

class Visitor(models.Model):
    PURPOSE_CHOICES = [
        ('Relative', 'Relative'),
        ('Delivery', 'Delivery'),
        ('Maintenance', 'Maintenance'),
        ('Guest', 'Guest'),
    ]

    CHECKIN_CHOICES =[
        ('Checked-In', 'Checked-In'),
        ('Checked-Out', 'Checked-OUT'),
    ]


    # Linkages
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='visitors')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='visitors_room')
    
    # Details
    full_name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=15)
    resident_name = models.CharField(max_length=200) # The tenant being visited
    purpose = models.CharField(max_length=50, choices=PURPOSE_CHOICES, default='Relative')
    
    # Log Times
    entry_time = models.DateTimeField(auto_now_add=True)
    exit_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=CHECKIN_CHOICES, default='Checked-In') # Checked-In / Checked-Out

    def __str__(self):
        return f"{self.full_name} - {self.property.name}"