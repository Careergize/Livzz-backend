from django.urls import include, path

from .views import MeView, MembershipListView, OrganizationDetailView, OrganizationListView, OrganizationPropertyListView

auth_patterns = []  # Reserved v2 boundary; legacy authentication remains under /auth/.
marketplace_patterns = []  # Marketplace category/listing APIs intentionally deferred.
portal_patterns = []  # Tenancy portal intentionally deferred.

urlpatterns = [
    path('auth/', include((auth_patterns, 'v2-auth'))),
    path('me/', MeView.as_view(), name='v2-me'),
    path('me/memberships/', MembershipListView.as_view(), name='v2-me-memberships'),
    path('organizations/', OrganizationListView.as_view(), name='v2-organizations'),
    path('organizations/<uuid:organization_id>/', OrganizationDetailView.as_view(), name='v2-organization-detail'),
    path('organizations/<uuid:organization_id>/properties/', OrganizationPropertyListView.as_view(), name='v2-organization-properties'),
    path('marketplace/', include((marketplace_patterns, 'v2-marketplace'))),
    path('portal/', include((portal_patterns, 'v2-portal'))),
]
