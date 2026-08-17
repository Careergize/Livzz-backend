from django.urls import path
from .views import MaintenanceTicketAPIView, MaintenanceTicketDetailAPIView

urlpatterns = [
    path('tickets/', MaintenanceTicketAPIView.as_view(), name='maintenance-list'),
    path('tickets/<int:pk>/', MaintenanceTicketDetailAPIView.as_view(), name='maintenance-detail'),
]