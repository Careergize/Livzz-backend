from rest_framework import serializers
from .models import Staff

class StaffSerializer(serializers.ModelSerializer):
    # We include these to show the name of the property instead of just the ID
    property_name = serializers.CharField(source='property.name', read_only=True)

    class Meta:
        model = Staff
        fields = [
            'id', 'property', 'property_name', 'name', 'role', 
            'email', 'phone', 'status', 'joined_at', 'salary_amount'
        ]   