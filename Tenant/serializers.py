from rest_framework import serializers
from .models import Tenant, Booking

class TenantSerializer(serializers.ModelSerializer):
    """Serializer for Tenant"""
    room_number = serializers.ReadOnlyField(source='room.room_number')
    property_name = serializers.ReadOnlyField(source='property.name')
    
    class Meta:
        model = Tenant
        fields = [
            'id', 'full_name', 'phone', 'whatsapp_number', 'email',
            'room', 'room_number', 'property', 'property_name',
            'join_date', 'rent_date', 'security_deposit', 'monthly_rent',
            'id_proof_type', 'id_proof_image', 'profile_image',
            'is_paid', 'status', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        
        if ret.get('id_proof_image') and request:
            ret['id_proof_image'] = request.build_absolute_uri(instance.id_proof_image.url)
        
        if ret.get('profile_image') and request:
            ret['profile_image'] = request.build_absolute_uri(instance.profile_image.url)
        
        return ret


class BookingSerializer(serializers.ModelSerializer):
    """Serializer for Booking"""
    tenant_name = serializers.ReadOnlyField(source='tenant.full_name')
    property_name = serializers.ReadOnlyField(source='property.name')
    
    class Meta:
        model = Booking
        fields = [
            'id', 'booking_id', 'tenant', 'tenant_name', 'property',
            'property_name', 'room', 'room_type', 'check_in_date',
            'check_out_date', 'monthly_rent', 'deposit', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'booking_id', 'created_at', 'updated_at']


class BookingHistorySerializer(serializers.ModelSerializer):
    """Serializer for booking history (seeker view)"""
    property_name = serializers.ReadOnlyField(source='property.name')
    transaction = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = [
            'booking_id', 'property_name', 'room_type', 'check_in_date',
            'check_out_date', 'monthly_rent', 'status', 'transaction'
        ]
    
    def get_transaction(self, obj):
        payment = obj.tenant.payments.filter(month_for__icontains=str(obj.check_in_date.year)).first()
        if payment:
            return {
                'transaction_id': payment.transaction_id,
                'paid_amount': str(payment.amount),
                'status': payment.payment_status,
                'payment_method': payment.payment_method,
                'date': payment.payment_date
            }
        return None


class SeekerCurrentStaySerializer(serializers.Serializer):
    """Serializer for seeker's current stay details"""
    property_name = serializers.CharField()
    room_number = serializers.CharField()
    joining_date = serializers.DateField()
    owner_name = serializers.CharField()
    owner_contact = serializers.CharField()
    owner_whatsapp = serializers.CharField()
    upi_id = serializers.CharField()
    payee_name = serializers.CharField()
    monthly_history = serializers.ListField()
    maintenance_tickets = serializers.ListField()


class EditSeekerProfileSerializer(serializers.Serializer):
    """Serializer for editing seeker profile"""
    name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    whatsapp_number = serializers.CharField(required=False, allow_blank=True)
    profile_image = serializers.ImageField(required=False, allow_null=True)
