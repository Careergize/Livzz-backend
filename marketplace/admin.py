from django.contrib import admin

from .models import Availability, Listing, ListingMedia, ListingTarget, PricePlan

admin.site.register((Listing, ListingTarget, PricePlan, Availability, ListingMedia))
