from rest_framework import serializers
from .models import MaintenanceTicket

class MaintenanceTicketSerializer(serializers.ModelSerializer):
    """Serializer for Maintenance Ticket"""
    tenant_name = serializers.ReadOnlyField(source='tenant.full_name', required=False)
    property_name = serializers.ReadOnlyField(source='property.name')
    assigned_staff_name = serializers.ReadOnlyField(source='assigned_staff.name')
    
    class Meta:
        model = MaintenanceTicket
        fields = [
            'id', 'ticket_id', 'category', 'room_number', 'description',
            'image_urls', 'priority', 'status', 'repair_cost',
            'property', 'property_name', 'tenant', 'tenant_name',
            'assigned_staff', 'assigned_staff_name', 'created_at',
            'updated_at', 'resolved_at'
        ]
        read_only_fields = ['id', 'ticket_id', 'created_at', 'updated_at']


class MaintenanceTicketCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating maintenance tickets"""
    class Meta:
        model = MaintenanceTicket
        fields = [
            'category', 'room_number', 'description', 'image_urls',
            'property', 'tenant'
        ]


class MaintenanceTicketUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating maintenance ticket status"""
    class Meta:
        model = MaintenanceTicket
        fields = [
            'status', 'priority', 'repair_cost', 'assigned_staff', 'resolved_at'
        ]
