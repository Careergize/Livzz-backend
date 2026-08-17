# urls.py
from django.urls import path
from .views import TenantListCreateAPIView, TenantDetailAPIView

urlpatterns = [
    path('tenants/', TenantListCreateAPIView.as_view(), name='tenant-list-create'),
    path('tenants/<int:pk>/', TenantDetailAPIView.as_view(), name='tenant-detail'),
]