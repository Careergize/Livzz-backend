from rest_framework import serializers
from .models import Payment, Complaint, Notification

class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment"""
    tenant_name = serializers.ReadOnlyField(source='tenant.full_name')
    property_name = serializers.ReadOnlyField(source='property.name')
    
    class Meta:
        model = Payment
        fields = [
            'id', 'transaction_id', 'tenant', 'tenant_name', 'property',
            'property_name', 'amount', 'payment_date', 'payment_method',
            'payment_status', 'month_for', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PaymentHistorySerializer(serializers.ModelSerializer):
    """Serializer for payment history (seeker view)"""
    class Meta:
        model = Payment
        fields = [
            'month_for', 'amount', 'payment_date', 'payment_status',
            'payment_method', 'transaction_id'
        ]


class PaymentResponseSerializer(serializers.Serializer):
    """Response format for payment data"""
    total_monthly_rent = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_advanced_deposit = serializers.DecimalField(max_digits=15, decimal_places=2)
    collected_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_spend = serializers.DecimalField(max_digits=15, decimal_places=2)
    rent_transactions = PaymentSerializer(many=True)
    staff_payroll = serializers.DictField()


class ComplaintSerializer(serializers.ModelSerializer):
    """Serializer for Complaint"""
    tenant_name = serializers.ReadOnlyField(source='tenant.full_name')
    
    class Meta:
        model = Complaint
        fields = [
            'id', 'tenant', 'tenant_name', 'title', 'description',
            'reply', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification"""
    tenant_name = serializers.ReadOnlyField(source='tenant.full_name')
    
    class Meta:
        model = Notification
        fields = [
            'id', 'tenant', 'tenant_name', 'message', 'notification_type',
            'is_read', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
