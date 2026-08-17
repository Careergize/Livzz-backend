from django.urls import path
from .views import VisitorAPIView, VisitorDetailAPIView

urlpatterns = [
    path('visitors/', VisitorAPIView.as_view(), name='visitor-list-create'),
    path('visitors/<int:pk>/', VisitorDetailAPIView.as_view(), name='visitor-detail'),
]