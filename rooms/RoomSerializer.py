# serializers.py
from rest_framework import serializers
from .models import Room

class RoomSerializer(serializers.ModelSerializer):
    # We can include the property name in the response for the UI
    property_name = serializers.ReadOnlyField(source='property.name')

    class Meta:
        model = Room
        fields = [
            'id', 'property', 'property_name', 'room_number', 
            'sharing_type', 'total_beds', 'occupied_beds', 
            'rent', 'is_active', 'created_at'
        ]