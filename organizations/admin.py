from django.contrib import admin
from .models import Organization, OrganizationMembership, OrganizationPayoutAccount, PropertyAccess, PropertyOrganizationHistory

admin.site.register((Organization, OrganizationMembership, OrganizationPayoutAccount, PropertyAccess, PropertyOrganizationHistory))
