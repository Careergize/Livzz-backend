# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Room
from .RoomSerializer import RoomSerializer
from django.shortcuts import get_object_or_404

class RoomListCreateAPIView(APIView):
    
    def get(self, request):
        """Fetch all rooms"""
        rooms = Room.objects.all().order_by('-created_at')
        serializer = RoomSerializer(rooms, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Add a new room"""
        serializer = RoomSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        # Return errors if validation fails (e.g., missing fields)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RoomDetailAPIView(APIView):
    def get(self, request, pk):
        room = get_object_or_404(Room, pk=pk)
        serializer = RoomSerializer(room)
        return Response(serializer.data)

    def patch(self, request, pk):
        room = get_object_or_404(Room, pk=pk)
        # partial=True allows us to update just one field (like occupied_beds)
        serializer = RoomSerializer(room, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        room = get_object_or_404(Room, pk=pk)
        room.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)