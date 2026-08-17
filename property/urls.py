from django.urls import path
from .seeker_views import (
    NearbyPropertiesView, SearchPropertiesView, PropertyDetailView,
    CurrentStayView, BookingHistoryView, EditProfileView, RaiseMaintenanceView
)
from .owner_views import (
    DashboardSummaryView, PropertyManagementView, SearchUsersView,
    AddTenantView, PaymentsView, MaintenanceManagementView, BookingManagementView
)
from .global_views import LocationsView

app_name = 'property'

urlpatterns = [
    # Seeker/Tenant Module
    path('properties/nearby/', NearbyPropertiesView.as_view(), name='nearby_properties'),
    path('properties/search/', SearchPropertiesView.as_view(), name='search_properties'),
    path('properties/<int:property_id>/', PropertyDetailView.as_view(), name='property_detail'),
    path('stay/current/', CurrentStayView.as_view(), name='current_stay'),
    path('bookings/history/', BookingHistoryView.as_view(), name='booking_history'),
    path('profile/edit/', EditProfileView.as_view(), name='edit_profile'),
    path('maintenance/raise/', RaiseMaintenanceView.as_view(), name='raise_maintenance'),
    
    # Owner/Host Module
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard_summary'),
    path('properties/', PropertyManagementView.as_view(), name='create_property'),
    path('owner/properties/<int:property_id>/', PropertyManagementView.as_view(), name='update_property'),
    path('users/search/', SearchUsersView.as_view(), name='search_users'),
    path('tenants/', AddTenantView.as_view(), name='add_tenant'),
    path('payments/', PaymentsView.as_view(), name='fetch_payments'),
    path('maintenance/', MaintenanceManagementView.as_view(), name='fetch_maintenance'),
    path('maintenance/<int:ticket_id>/', MaintenanceManagementView.as_view(), name='update_maintenance'),
    path('bookings/', BookingManagementView.as_view(), name='fetch_bookings'),
    path('bookings/<int:booking_id>/', BookingManagementView.as_view(), name='update_booking'),
    
    # Global
    path('', LocationsView.as_view(), name='locations'),
]
