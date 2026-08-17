from django.contrib import admin
from .models import Booking, Tenant

# Register your models here.
admin.site.register(Tenant)
admin.site.register(Booking)