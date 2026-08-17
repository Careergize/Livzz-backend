from django.contrib import admin
from .models import Location, Property, RoomConfiguration

# Register your models here.
admin.site.register(Location)
admin.site.register(Property)
admin.site.register(RoomConfiguration)