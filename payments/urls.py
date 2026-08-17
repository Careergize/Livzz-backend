from django.urls import path
from .views import (
    PaymentListCreateView, 
    ComplaintListCreateView, 
    ComplaintReplyView,
    NotificationListView
)

urlpatterns = [
    # Property Management
    
    # Payments (Triggers Tenant status update & Notification)
    path('payments/', PaymentListCreateView.as_view(), name='payment-list'),
    
    # Complaints (Tenant perspective & List)
    path('complaints/', ComplaintListCreateView.as_view(), name='complaint-list'),
    
    # Owner Response (Triggers Notification)
    # Using <int:pk> allows you to target a specific complaint ID
    path('complaints/<int:pk>/reply/', ComplaintReplyView.as_view(), name='complaint-reply'),
    
    # Activity Log / Notifications
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
]