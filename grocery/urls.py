from django.urls import path
from .views import GroceryExpenseAPIView, GroceryExpenseDetailAPIView

urlpatterns = [
    path('expenses/', GroceryExpenseAPIView.as_view(), name='grocery-list'),
    path('expenses/<int:pk>/', GroceryExpenseDetailAPIView.as_view(), name='grocery-detail'),
]