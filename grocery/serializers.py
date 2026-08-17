from rest_framework import serializers
from .models import GroceryExpense

class GroceryExpenseSerializer(serializers.ModelSerializer):
    # This shows the property name in the response for the frontend
    property_name = serializers.ReadOnlyField(source='property.name')
    
    class Meta:
        model = GroceryExpense
        fields = [
            'id', 'property', 'property_name', 'date', 'amount', 
            'vendor', 'category', 'payment_mode', 'status', 
            'receipt_image', 'created_at'
        ]