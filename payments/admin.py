from django.contrib import admin
from .models import Payment , Complaint , Notification
# Register your models here.
admin.site.register(Payment)
admin.site.register(Complaint)
admin.site.register(Notification)