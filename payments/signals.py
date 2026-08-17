from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment, Complaint, Notification

@receiver(post_save, sender=Payment)
def handle_payment_notification(sender, instance, created, **kwargs):
    if created:
        tenant = instance.tenant
        tenant.is_paid = True
        tenant.save()
        
        Notification.objects.create(
            tenant=tenant,
            notification_type='PAYMENT',
            message=f"Rent Payment of ₹{instance.amount} confirmed for {instance.month_for}."
        )

@receiver(post_save, sender=Complaint)
def handle_complaint_updates(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            tenant=instance.tenant,
            notification_type='COMPLAINT',
            message=f"Complaint received: {instance.title}."
        )
    elif instance.reply and instance.status != 'RESOLVED':
        # Use filter().update() to prevent re-triggering the signal
        Complaint.objects.filter(id=instance.id).update(status='RESOLVED')
        
        Notification.objects.create(
            tenant=instance.tenant,
            notification_type='REPLY',
            message=f"Owner replied to: {instance.title}. Reply: {instance.reply}"
        )