from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
import random
from .models import User

class SendOTPSerializer(serializers.Serializer):
    """Serializer for sending OTP"""
    phone_number = serializers.CharField(max_length=15)
    
    def validate_phone_number(self, value):
        if not value.startswith('+'):
            raise serializers.ValidationError("Phone number must start with +")
        return value


class VerifyOTPSerializer(serializers.Serializer):
    """Serializer for verifying OTP"""
    phone_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)
    otp_reference_id = serializers.CharField(max_length=50)


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone_number', 'whatsapp_number', 'role', 'profile_image'
        ]
        read_only_fields = ['id']


class SeekerProfileSerializer(serializers.ModelSerializer):
    """Serializer for seeker profile registration"""
    identity_front_image = serializers.ImageField(required=True)
    identity_back_image = serializers.ImageField(required=True)
    
    class Meta:
        model = User
        fields = [
            'first_name', 'email', 'phone_number', 'whatsapp_number',
            'identity_type', 'identity_front_image', 'identity_back_image',
            'profile_image'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'email': {'required': True},
        }
    
    def create(self, validated_data):
        validated_data['role'] = 'seeker'
        validated_data['username'] = validated_data['phone_number']
        user = User.objects.create_user(**validated_data)
        return user


class OwnerProfileSerializer(serializers.ModelSerializer):
    """Serializer for owner profile registration"""
    identity_front_image = serializers.ImageField(required=True)
    identity_back_image = serializers.ImageField(required=True)
    
    class Meta:
        model = User
        fields = [
            'first_name', 'email', 'phone_number', 'whatsapp_number',
            'identity_type', 'identity_front_image', 'identity_back_image',
            'profile_image', 'upi_id', 'payee_name', 'organization_name'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'upi_id': {'required': True},
            'payee_name': {'required': True},
            'identity_type': {'required': True},
        }
    
    def create(self, validated_data):
        validated_data['role'] = 'owner'
        validated_data['username'] = validated_data['phone_number']
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    phone_number = serializers.CharField(max_length=15)
    password = serializers.CharField(max_length=128, write_only=True)


class AuthResponseSerializer(serializers.Serializer):
    """Generic response serializer for auth endpoints"""
    success = serializers.BooleanField()
    message = serializers.CharField(required=False)
    otp_reference_id = serializers.CharField(required=False)
    token = serializers.CharField(required=False)
    user = UserProfileSerializer(required=False)
