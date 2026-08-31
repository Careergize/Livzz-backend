from django.contrib import admin
from .models import (Amenity, ApartmentDetails, InventoryItem, LegacyMappingIssue,
                     Location, OfficeDetails, PGDetails, Property, PropertyAmenity,
                     PropertyMedia, RoomConfiguration, Unit, VillaDetails)

# Register your models here.
admin.site.register(Location)
admin.site.register(Property)
admin.site.register(RoomConfiguration)
admin.site.register(Unit)
admin.site.register(InventoryItem)
admin.site.register(PropertyMedia)
admin.site.register(Amenity)
admin.site.register(PropertyAmenity)
admin.site.register(PGDetails)
admin.site.register(ApartmentDetails)
admin.site.register(VillaDetails)
admin.site.register(OfficeDetails)
admin.site.register(LegacyMappingIssue)
