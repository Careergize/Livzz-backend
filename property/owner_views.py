"""Owner/Host API Views"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count, F
from datetime import datetime

from property.models import Property, Location
from property.serializers import PropertyListSerializer, PropertyDetailSerializer, PropertyCreateUpdateSerializer
from Tenant.models import Tenant, Booking
from Tenant.serializers import TenantSerializer
from payments.models import Payment
from payments.serializers import PaymentSerializer
from maintenance.models import MaintenanceTicket
from maintenance.serializers import MaintenanceTicketSerializer, MaintenanceTicketUpdateSerializer
from staff.models import Staff
from staff.serializers import StaffSerializer
from rooms.models import Room

class DashboardSummaryView(APIView):
    """API to fetch owner dashboard summary"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            owner = request.user
            properties = Property.objects.filter(owner=owner)
            
            # Calculate metrics
            total_revenue = Payment.objects.filter(
                property__owner=owner,
                payment_status='SUCCESSFUL'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            pending_dues = Payment.objects.filter(
                property__owner=owner,
                payment_status='PENDING'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            total_tenants = Tenant.objects.filter(property__owner=owner).count()
            
            # Occupancy rate
            total_beds = Room.objects.filter(property__owner=owner).aggregate(total=Sum('total_beds'))['total'] or 0
            occupied_beds = Room.objects.filter(property__owner=owner).aggregate(total=Sum('occupied_beds'))['total'] or 0
            occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0
            
            staff_count = Staff.objects.filter(property__owner=owner).count()
            maintenance_count = MaintenanceTicket.objects.filter(property__owner=owner).count()
            
            # Overdue payments
            overdue_payments = Payment.objects.filter(
                property__owner=owner,
                payment_status='PENDING'
            ).select_related('tenant', 'tenant__room').values(
                'tenant__full_name', 'tenant__room__room_number', 'amount'
            )[:10]
            
            # Recent maintenance
            recent_maintenance = MaintenanceTicket.objects.filter(
                property__owner=owner
            ).order_by('-created_at').values(
                'ticket_id', 'category', 'room_number', 'status'
            )[:5]
            
            data = {
                'total_revenue_mtd': str(total_revenue),
                'pending_dues': str(pending_dues),
                'occupancy_rate': round(occupancy_rate, 1),
                'total_properties': properties.count(),
                'active_tenants': total_tenants,
                'visitors_count': 0,  # TODO: Calculate from visitor model
                'staff_count': staff_count,
                'maintenance_tickets_count': maintenance_count,
                'properties': PropertyListSerializer(properties, many=True).data,
                'overdue_payments': list(overdue_payments),
                'recent_maintenance_requests': list(recent_maintenance)
            }
            
            return Response({
                'success': True,
                'data': data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PropertyManagementView(APIView):
    """API to create and manage properties"""
    # permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Fetch all properties for the authenticated owner"""
        properties = Property.objects.all()  # In production, filter by owner: .filter(owner=request.user)
        serializer = PropertyListSerializer(properties, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    def post(self, request):
        """Create new property"""
        serializer = PropertyCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            property_obj = serializer.save(owner=request.user)
            return Response({
                'success': True,
                'message': 'Property created successfully',
                'data': PropertyDetailSerializer(property_obj).data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, property_id):
        """Update property"""
        try:
            property_obj = Property.objects.get(id=property_id, owner=request.user)
            serializer = PropertyCreateUpdateSerializer(property_obj, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'message': 'Property updated successfully',
                    'data': PropertyDetailSerializer(property_obj).data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Property.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Property not found'
            }, status=status.HTTP_404_NOT_FOUND)


class SearchUsersView(APIView):
    """API to search users by phone number"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        phone_number = request.query_params.get('phone_number')
        
        if not phone_number:
            return Response({
                'success': False,
                'message': 'Phone number required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from accounts.models import User
        try:
            user = User.objects.get(phone_number=phone_number)
            return Response({
                'success': True,
                'data': {
                    'id': user.id,
                    'name': user.first_name,
                    'email': user.email,
                    'phone_number': user.phone_number,
                    'identity_status': 'verified' if user.identity_type else 'unverified'
                }
            }, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)


class AddTenantView(APIView):
    """API to add tenant to property"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = TenantSerializer(data=request.data)
        if serializer.is_valid():
            tenant = serializer.save()
            
            # Create booking
            booking_id = f"BK-{Booking.objects.count() + 1}"
            booking = Booking.objects.create(
                booking_id=booking_id,
                tenant=tenant,
                property=tenant.property,
                room=tenant.room,
                room_type=tenant.room.sharing_type if tenant.room else 'N/A',
                check_in_date=tenant.join_date,
                monthly_rent=tenant.monthly_rent,
                deposit=tenant.security_deposit,
                status='active'
            )
            
            return Response({
                'success': True,
                'message': 'Tenant added successfully',
                'data': TenantSerializer(tenant).data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class PaymentsView(APIView):
    """API to fetch payments and dues"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        property_id = request.query_params.get('property_id')
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        
        payments = Payment.objects.filter(property__owner=request.user)
        
        if property_id:
            payments = payments.filter(property_id=property_id)
        
        if from_date:
            payments = payments.filter(payment_date__gte=from_date)
        
        if to_date:
            payments = payments.filter(payment_date__lte=to_date)
        
        # Calculate totals
        total_rent = payments.aggregate(total=Sum('amount'))['total'] or 0
        collected_total = payments.filter(payment_status='SUCCESSFUL').aggregate(total=Sum('amount'))['total'] or 0
        pending_total = payments.filter(payment_status='PENDING').aggregate(total=Sum('amount'))['total'] or 0
        
        # Get staff payroll
        staff_members = Staff.objects.filter(property__owner=request.user)
        staff_payroll = {
            'total_salary_expense': staff_members.aggregate(total=Sum('salary_amount'))['total'] or 0,
            'staff_list': [
                {
                    'staff_id': staff.id,
                    'name': staff.name,
                    'salary_amount': str(staff.salary_amount)
                }
                for staff in staff_members
            ]
        }
        
        data = {
            'total_monthly_rent': str(total_rent),
            'total_advanced_deposit': '0',  # TODO: Calculate from deposits
            'collected_total': str(collected_total),
            'pending_total': str(pending_total),
            'total_spend': str(staff_payroll['total_salary_expense']),
            'rent_transactions': PaymentSerializer(payments, many=True).data,
            'staff_payroll': staff_payroll
        }
        
        return Response({
            'success': True,
            'data': data
        }, status=status.HTTP_200_OK)


class MaintenanceManagementView(APIView):
    """API to manage maintenance tickets"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Fetch maintenance tickets for owner's properties"""
        tickets = MaintenanceTicket.objects.filter(property__owner=request.user)
        serializer = MaintenanceTicketSerializer(tickets, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    def patch(self, request, ticket_id):
        """Update maintenance ticket status"""
        try:
            ticket = MaintenanceTicket.objects.get(id=ticket_id, property__owner=request.user)
            serializer = MaintenanceTicketUpdateSerializer(ticket, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'message': 'Ticket updated successfully',
                    'data': MaintenanceTicketSerializer(ticket).data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except MaintenanceTicket.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Ticket not found'
            }, status=status.HTTP_404_NOT_FOUND)


class BookingManagementView(APIView):
    """API to manage bookings for owner's properties"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Fetch all bookings for owner's properties"""
        status_filter = request.query_params.get('status', 'all')
        property_id = request.query_params.get('property_id')
        
        bookings = Booking.objects.filter(property__owner=request.user)
        
        # Filter by property if specified
        if property_id:
            bookings = bookings.filter(property_id=property_id)
        
        # Filter by status if specified
        if status_filter != 'all':
            bookings = bookings.filter(status=status_filter)
        
        bookings = bookings.order_by('-created_at')
        
        from Tenant.serializers import BookingHistorySerializer
        serializer = BookingHistorySerializer(bookings, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'count': bookings.count()
        }, status=status.HTTP_200_OK)
    
    def patch(self, request, booking_id):
        """Update booking status (upcoming -> active -> past, etc.)"""
        try:
            booking = Booking.objects.get(id=booking_id, property__owner=request.user)
            new_status = request.data.get('status')
            
            if new_status not in ['active', 'upcoming', 'past', 'cancelled']:
                return Response({
                    'success': False,
                    'message': 'Invalid status. Must be: active, upcoming, past, or cancelled'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            booking.status = new_status
            booking.save()
            
            from Tenant.serializers import BookingHistorySerializer
            serializer = BookingHistorySerializer(booking)
            
            return Response({
                'success': True,
                'message': f'Booking status updated to {new_status}',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        except Booking.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Booking not found'
            }, status=status.HTTP_404_NOT_FOUND)
