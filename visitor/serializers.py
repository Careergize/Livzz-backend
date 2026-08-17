from rest_framework import serializers
from .models import Visitor

class VisitorSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True)
    room_number = serializers.CharField(source='room.room_number', read_only=True)
    entry_time_formatted = serializers.DateTimeField(source='entry_time', format="%d %b, %I:%M %p", read_only=True)

    class Meta:
        model = Visitor
        fields = '__all__'