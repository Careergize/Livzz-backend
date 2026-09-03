from django.urls import include, path

from .views import (InventoryListView, MeView, MembershipListView, OrganizationDetailView,
                    OrganizationListView, OrganizationPropertyDetailView,
                    OrganizationPropertyListView, UnitDetailView, UnitListView)
from marketplace.api import (ListingActionView, ListingAvailabilityView, ListingPriceView,
                             OrganizationListingDetailView, OrganizationListingListView,
                             PublicListingDetailView, PublicListingListView)
from .self_service import (DraftDetailView, DraftListCreateView, DraftMediaDetailView,
                           DraftMediaView, DraftPublishView, ListerProfileView, LoginView,
                           LogoutView, MyListingsView, RegisterView)

auth_patterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
class PGListings(PublicListingListView): category = 'PG'
class ApartmentListings(PublicListingListView): category = 'APARTMENT'
class VillaListings(PublicListingListView): category = 'VILLA'
class OfficeListings(PublicListingListView): category = 'OFFICE'
class PublishListing(ListingActionView): action = 'publish'
class PauseListing(ListingActionView): action = 'pause'

marketplace_patterns = [
    path('listings/', PublicListingListView.as_view(), name='listing-list'),
    path('listings/<slug:slug>/', PublicListingDetailView.as_view(), name='listing-detail'),
    path('pg/', PGListings.as_view(), name='pg-list'),
    path('apartments/', ApartmentListings.as_view(), name='apartment-list'),
    path('villas/', VillaListings.as_view(), name='villa-list'),
    path('office/', OfficeListings.as_view(), name='office-list'),
]
portal_patterns = []  # Tenancy portal intentionally deferred.

urlpatterns = [
    path('auth/', include((auth_patterns, 'v2-auth'))),
    path('me/', MeView.as_view(), name='v2-me'),
    path('me/lister-profile/', ListerProfileView.as_view(), name='v2-lister-profile'),
    path('me/listing-drafts/', DraftListCreateView.as_view(), name='v2-my-listing-drafts'),
    path('me/listings/', MyListingsView.as_view(), name='v2-my-listings'),
    path('listing-drafts/', DraftListCreateView.as_view(), name='v2-listing-drafts'),
    path('listing-drafts/<uuid:draft_id>/', DraftDetailView.as_view(), name='v2-listing-draft-detail'),
    path('listing-drafts/<uuid:draft_id>/publish/', DraftPublishView.as_view(), name='v2-listing-draft-publish'),
    path('listing-drafts/<uuid:draft_id>/media/', DraftMediaView.as_view(), name='v2-listing-draft-media'),
    path('listing-drafts/<uuid:draft_id>/media/<int:media_id>/', DraftMediaDetailView.as_view(), name='v2-listing-draft-media-detail'),
    path('me/memberships/', MembershipListView.as_view(), name='v2-me-memberships'),
    path('organizations/', OrganizationListView.as_view(), name='v2-organizations'),
    path('organizations/<uuid:organization_id>/', OrganizationDetailView.as_view(), name='v2-organization-detail'),
    path('organizations/<uuid:organization_id>/properties/', OrganizationPropertyListView.as_view(), name='v2-organization-properties'),
    path('organizations/<uuid:organization_id>/properties/<uuid:property_id>/', OrganizationPropertyDetailView.as_view(), name='v2-organization-property-detail'),
    path('organizations/<uuid:organization_id>/properties/<uuid:property_id>/units/', UnitListView.as_view(), name='v2-property-units'),
    path('organizations/<uuid:organization_id>/properties/<uuid:property_id>/units/<uuid:unit_id>/', UnitDetailView.as_view(), name='v2-property-unit-detail'),
    path('organizations/<uuid:organization_id>/properties/<uuid:property_id>/inventory/', InventoryListView.as_view(), name='v2-property-inventory'),
    path('organizations/<uuid:organization_id>/properties/<uuid:property_id>/units/<uuid:unit_id>/inventory/', InventoryListView.as_view(), name='v2-unit-inventory'),
    path('organizations/<uuid:organization_id>/listings/', OrganizationListingListView.as_view(), name='v2-organization-listings'),
    path('organizations/<uuid:organization_id>/listings/<uuid:listing_id>/', OrganizationListingDetailView.as_view(), name='v2-organization-listing-detail'),
    path('organizations/<uuid:organization_id>/listings/<uuid:listing_id>/publish/', PublishListing.as_view(), name='v2-listing-publish'),
    path('organizations/<uuid:organization_id>/listings/<uuid:listing_id>/pause/', PauseListing.as_view(), name='v2-listing-pause'),
    path('organizations/<uuid:organization_id>/listings/<uuid:listing_id>/prices/', ListingPriceView.as_view(), name='v2-listing-prices'),
    path('organizations/<uuid:organization_id>/listings/<uuid:listing_id>/availability/', ListingAvailabilityView.as_view(), name='v2-listing-availability'),
    path('marketplace/', include((marketplace_patterns, 'v2-marketplace'))),
    path('portal/', include((portal_patterns, 'v2-portal'))),
]
