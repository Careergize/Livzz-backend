"""Seeker/Tenant API Views"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from math import radians, sin, cos, sqrt, atan2

from property.models import Property, Location
from property.serializers import PropertyListSerializer, PropertyDetailSerializer
from Tenant.models import Tenant, Booking
from Tenant.serializers import (
    BookingHistorySerializer, SeekerCurrentStaySerializer,
    EditSeekerProfileSerializer
)
from maintenance.models import MaintenanceTicket
from maintenance.serializers import MaintenanceTicketCreateSerializer, MaintenanceTicketSerializer
from payments.models import Payment
from payments.serializers import PaymentHistorySerializer


class NearbyPropertiesView(APIView):
    """API to fetch nearby properties based on geolocation"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        radius_km = float(request.query_params.get('radius_km', 10))
        
        if not lat or not lng:
            return Response({
                'success': False,
                'message': 'Latitude and longitude required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            lat = float(lat)
            lng = float(lng)
        except ValueError:
            return Response({
                'success': False,
                'message': 'Invalid coordinates'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get all active properties
        properties = Property.objects.filter(is_active=True)
        
        # Filter by radius (simple distance calculation)
        nearby_properties = []
        for prop in properties:
            if prop.latitude and prop.longitude:
                distance = calculate_distance(lat, lng, prop.latitude, prop.longitude)
                if distance <= radius_km:
                    nearby_properties.append(prop)
        
        serializer = PropertyListSerializer(nearby_properties, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class SearchPropertiesView(APIView):
    """API to search and filter properties"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        query = request.query_params.get('query', '')
        location = request.query_params.get('location', '')
        property_type = request.query_params.get('property_type', '')
        gender_filter = request.query_params.get('gender_filter', '')
        budget_min = request.query_params.get('budget_min')
        budget_max = request.query_params.get('budget_max')
        
        properties = Property.objects.filter(is_active=True)
        
        # Filter by query (name, description)
        if query:
            properties = properties.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )
        
        # Filter by location
        if location:
            properties = properties.filter(
                Q(city__icontains=location) | Q(location__name__icontains=location)
            )
        
        # Filter by property type
        if property_type:
            properties = properties.filter(property_type=property_type)
        
        # Filter by gender
        if gender_filter:
            properties = properties.filter(gender_filter=gender_filter)
        
        # Filter by budget
        if budget_min:
            properties = properties.filter(price__gte=budget_min)
        if budget_max:
            properties = properties.filter(price__lte=budget_max)
        
        serializer = PropertyListSerializer(properties, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': properties.count()
        }, status=status.HTTP_200_OK)


class PropertyDetailView(APIView):
    """API to fetch specific property details"""
    permission_classes = [AllowAny]
    
    def get(self, request, property_id):
        try:
            property_obj = Property.objects.get(id=property_id, is_active=True)
            
            # Get related properties (same property type and owner)
            related_properties = Property.objects.filter(
                property_type=property_obj.property_type,
                owner=property_obj.owner,
                is_active=True
            ).exclude(id=property_id)[:5]
            
            serializer = PropertyDetailSerializer(property_obj)
            data = serializer.data
            data['related_properties'] = PropertyListSerializer(related_properties, many=True).data
            
            return Response({
                'success': True,
                'data': data
            }, status=status.HTTP_200_OK)
        
        except Property.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Property not found'
            }, status=status.HTTP_404_NOT_FOUND)


class CurrentStayView(APIView):
    """API to fetch seeker's current stay details"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Get tenant associated with this user
            tenant = Tenant.objects.get(user=request.user)
            booking = Booking.objects.filter(tenant=tenant, status='active').first()
            
            if not booking:
                return Response({
                    'success': False,
                    'message': 'No active booking found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get payment history for this tenant
            payment_history = Payment.objects.filter(tenant=tenant).order_by('-payment_date')[:5]
            
            # Get maintenance tickets
            maintenance_tickets = MaintenanceTicket.objects.filter(
                tenant=tenant
            ).values('id', 'ticket_id', 'category', 'status')[:5]
            
            data = {
                'property_name': booking.property.name,
                'room_number': booking.room.room_number if booking.room else 'N/A',
                'joining_date': booking.check_in_date,
                'owner_name': booking.property.owner.first_name,
                'owner_contact': booking.property.owner.phone_number,
                'owner_whatsapp': booking.property.owner.whatsapp_number,
                'upi_id': booking.property.owner.upi_id,
                'payee_name': booking.property.owner.payee_name,
                'monthly_history': [
                    {
                        'month': payment.month_for,
                        'rent': str(payment.amount),
                        'status': payment.payment_status
                    }
                    for payment in payment_history
                ],
                'maintenance_tickets': list(maintenance_tickets)
            }
            
            return Response({
                'success': True,
                'data': data
            }, status=status.HTTP_200_OK)
        
        except Tenant.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Tenant profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


class BookingHistoryView(APIView):
    """API to fetch seeker's booking history"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        status_filter = request.query_params.get('status', 'all')
        
        try:
            tenant = Tenant.objects.get(user=request.user)
            bookings = Booking.objects.filter(tenant=tenant)
            
            if status_filter != 'all':
                bookings = bookings.filter(status=status_filter)
            
            serializer = BookingHistorySerializer(bookings, many=True)
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        except Tenant.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Tenant profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


class EditProfileView(APIView):
    """API to edit seeker profile"""
    permission_classes = [IsAuthenticated]
    
    def patch(self, request):
        serializer = EditSeekerProfileSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            user = request.user
            
            if 'name' in serializer.validated_data:
                user.first_name = serializer.validated_data['name']
            if 'email' in serializer.validated_data:
                user.email = serializer.validated_data['email']
            if 'whatsapp_number' in serializer.validated_data:
                user.whatsapp_number = serializer.validated_data['whatsapp_number']
            if 'profile_image' in serializer.validated_data:
                user.profile_image = serializer.validated_data['profile_image']
            
            user.save()
            
            return Response({
                'success': True,
                'message': 'Profile updated successfully'
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class RaiseMaintenanceView(APIView):
    """API to raise maintenance issue"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = MaintenanceTicketCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                tenant = Tenant.objects.get(user=request.user)
                ticket = serializer.save(tenant=tenant)
                
                return Response({
                    'success': True,
                    'message': 'Maintenance ticket created successfully',
                    'data': MaintenanceTicketSerializer(ticket).data
                }, status=status.HTTP_201_CREATED)
            
            except Tenant.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Tenant profile not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


# Utility function to calculate distance
def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in kilometers"""
    R = 6371  # Earth's radius in km
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return distance
