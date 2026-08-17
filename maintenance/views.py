from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import MaintenanceTicket
from .serializers import MaintenanceTicketSerializer

class MaintenanceTicketAPIView(APIView):
    def get(self, request):
        property_id = request.query_params.get('property_id')
        tickets = MaintenanceTicket.objects.filter(property_id=property_id) if property_id else MaintenanceTicket.objects.all()
        serializer = MaintenanceTicketSerializer(tickets, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MaintenanceTicketSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MaintenanceTicketDetailAPIView(APIView):
    def patch(self, request, pk):
        ticket = get_object_or_404(MaintenanceTicket, pk=pk)
        serializer = MaintenanceTicketSerializer(ticket, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        ticket = get_object_or_404(MaintenanceTicket, pk=pk)
        ticket.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)