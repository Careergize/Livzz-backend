from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Tenant, Booking
import uuid


@receiver(post_save, sender=Tenant)
def create_booking_on_tenant_creation(sender, instance, created, **kwargs):
    """
    Signal to automatically create a Booking when a Tenant is created.
    Status is set to 'upcoming' by default.
    """
    if created:
        # Generate unique booking ID
        booking_id = f"BK-{instance.id}-{uuid.uuid4().hex[:6].upper()}"
        
        # Create booking with 'upcoming' status
        Booking.objects.create(
            booking_id=booking_id,
            tenant=instance,
            property=instance.property,
            room=instance.room,
            room_type=instance.room.sharing_type if instance.room else 'N/A',
            check_in_date=instance.join_date,
            monthly_rent=instance.monthly_rent,
            deposit=instance.security_deposit,
            status='upcoming'  # Status set to 'upcoming' on creation
        )
