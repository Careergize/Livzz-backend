from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Tenant, Payment, Complaint, Notification, Property

from .serializers import (
 PaymentSerializer, 
    ComplaintSerializer, NotificationSerializer,
)
from Tenant.serializers import TenantSerializer
from payments.serializers import PaymentSerializer, ComplaintSerializer, NotificationSerializer
# --- PAYMENT API ---
class PaymentListCreateView(APIView):
    def get(self, request):
        # FIX: Changed from 'created_at' to 'payment_date' to match your model
        payments = Payment.objects.all().order_by('-payment_date')
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PaymentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save() # Triggers signal to mark tenant paid
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- COMPLAINT API ---
class ComplaintListCreateView(APIView):
    def get(self, request):
        # Complaints usually have 'created_at'
        complaints = Complaint.objects.all().order_by('-created_at')
        serializer = ComplaintSerializer(complaints, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ComplaintSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- NOTIFICATION API ---
class NotificationListView(APIView):
    def get(self, request):
        # Notifications usually have 'created_at'
        notifications = Notification.objects.all().order_by('-created_at')
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

    def post(self, request):
        Notification.objects.filter(is_read=False).update(is_read=True)
        return Response({"message": "Notifications marked as read"})

# --- COMPLAINT REPLY ---
class ComplaintReplyView(APIView):
    def patch(self, request, pk):
        complaint = get_object_or_404(Complaint, pk=pk)
        reply_text = request.data.get('reply')
        
        if not reply_text:
            return Response({"error": "Reply text is required"}, status=400)
            
        complaint.reply = reply_text
        complaint.status = 'RESOLVED'
        complaint.save() # Triggers signal to notify tenant
        
        serializer = ComplaintSerializer(complaint)
        return Response(serializer.data)