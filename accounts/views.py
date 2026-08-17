from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model, authenticate
from django.core.mail import send_mail
from django.conf import settings
import random
import string
from .serializers import (
    SendOTPSerializer, VerifyOTPSerializer, SeekerProfileSerializer,
    OwnerProfileSerializer, UserProfileSerializer, AuthResponseSerializer,
    LoginSerializer
)

User = get_user_model()

class SendOTPView(APIView):
    """API endpoint to send OTP to phone number"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            
            # Generate 6-digit OTP
            otp = ''.join(random.choices(string.digits, k=6))
            otp_reference_id = f"ref_{phone_number}_{random.randint(100000, 999999)}"
            
            # In production, send via SMS gateway
            # For now, we'll store it
            
            # Try to get or create user
            user, created = User.objects.get_or_create(
                phone_number=phone_number,
                defaults={'username': phone_number}
            )
            user.otp = otp
            user.otp_reference_id = otp_reference_id
            user.save()
            
            # TODO: Send OTP via SMS gateway (Twilio, AWS SNS, etc.)
            print(f"OTP for {phone_number}: {otp}")  # Debug
            
            return Response({
                'success': True,
                'otp_reference_id': otp_reference_id,
                'message': 'OTP sent successfully'
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(APIView):
    """API endpoint to verify OTP"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            otp = serializer.validated_data['otp']
            otp_reference_id = serializer.validated_data['otp_reference_id']
            
            try:
                user = User.objects.get(phone_number=phone_number)
                
                # Verify OTP
                if user.otp == otp and user.otp_reference_id == otp_reference_id:
                    user.otp_verified = True
                    user.otp = None  # Clear OTP after verification
                    user.save()
                    
                    return Response({
                        'success': True,
                        'message': 'OTP verified successfully',
                        'user_exists': user.role is not None and user.role != ''
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'success': False,
                        'message': 'Invalid OTP'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            except User.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class RegisterSeekerView(APIView):
    """API endpoint to register seeker/tenant"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = SeekerProfileSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = User.objects.get(phone_number=request.data.get('phone_number'))
                
                if not user.otp_verified:
                    return Response({
                        'success': False,
                        'message': 'Please verify OTP first'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Update user with seeker profile
                user.first_name = serializer.validated_data.get('first_name', user.first_name)
                user.email = serializer.validated_data.get('email', user.email)
                user.whatsapp_number = serializer.validated_data.get('whatsapp_number', '')
                user.identity_type = serializer.validated_data.get('identity_type')
                user.identity_front_image = serializer.validated_data.get('identity_front_image')
                user.identity_back_image = serializer.validated_data.get('identity_back_image')
                user.profile_image = serializer.validated_data.get('profile_image')
                user.role = 'seeker'
                user.save()
                
                return Response({
                    'success': True,
                    'message': 'Seeker profile created successfully',
                    'user': UserProfileSerializer(user).data
                }, status=status.HTTP_201_CREATED)
            
            except User.DoesNotExist:
                user = serializer.save()
                return Response({
                    'success': True,
                    'message': 'Seeker profile created successfully',
                    'user': UserProfileSerializer(user).data
                }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class RegisterOwnerView(APIView):
    """API endpoint to register owner"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = OwnerProfileSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = User.objects.get(phone_number=request.data.get('phone_number'))
                
                if not user.otp_verified:
                    return Response({
                        'success': False,
                        'message': 'Please verify OTP first'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Update user with owner profile
                user.first_name = serializer.validated_data.get('first_name', user.first_name)
                user.email = serializer.validated_data.get('email', user.email)
                user.whatsapp_number = serializer.validated_data.get('whatsapp_number', '')
                user.identity_type = serializer.validated_data.get('identity_type')
                user.identity_front_image = serializer.validated_data.get('identity_front_image')
                user.identity_back_image = serializer.validated_data.get('identity_back_image')
                user.profile_image = serializer.validated_data.get('profile_image')
                user.upi_id = serializer.validated_data.get('upi_id')
                user.payee_name = serializer.validated_data.get('payee_name')
                user.organization_name = serializer.validated_data.get('organization_name')
                user.role = 'owner'
                user.save()
                
                return Response({
                    'success': True,
                    'message': 'Owner profile created successfully',
                    'user': UserProfileSerializer(user).data
                }, status=status.HTTP_201_CREATED)
            
            except User.DoesNotExist:
                user = serializer.save()
                return Response({
                    'success': True,
                    'message': 'Owner profile created successfully',
                    'user': UserProfileSerializer(user).data
                }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """API endpoint for user login with token generation"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            password = serializer.validated_data['password']
            
            try:
                # Get user by phone number
                user = User.objects.get(phone_number=phone_number)
                
                # Check password
                if user.check_password(password):
                    # Generate or retrieve token
                    token, created = Token.objects.get_or_create(user=user)
                    
                    return Response({
                        'success': True,
                        'message': 'Login successful',
                        'token': token.key,
                        'user': UserProfileSerializer(user).data
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'success': False,
                        'message': 'Invalid password'
                    }, status=status.HTTP_401_UNAUTHORIZED)
            
            except User.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """API endpoint for user logout (token deletion)"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Delete user's token
            token = Token.objects.get(user=request.user)
            token.delete()
            
            return Response({
                'success': True,
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
        except Token.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Token not found'
            }, status=status.HTTP_404_NOT_FOUND)

