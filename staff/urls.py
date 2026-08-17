from django.urls import path
from .views import StaffAPIView, StaffDetailAPIView

urlpatterns = [
    # List and Create
    path('staff/', StaffAPIView.as_view(), name='staff-list-create'),
    
    # Detail, Update, and Delete
    path('staff/<int:pk>/', StaffDetailAPIView.as_view(), name='staff-detail'),
]