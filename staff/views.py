from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Staff
from .serializers import StaffSerializer

class StaffAPIView(APIView):
    """
    Handles listing property staff and creating new staff members.
    """
    def get(self, request):
        # Get property_id from query params (e.g., /staff/?property_id=1)
        property_id = request.query_params.get('property_id')
        
        if property_id:
            staff = Staff.objects.filter(property_id=property_id).order_by('-joined_at')
        else:
            staff = Staff.objects.all().order_by('-joined_at')
            
        serializer = StaffSerializer(staff, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = StaffSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StaffDetailAPIView(APIView):
    """
    Handles retrieving, updating, and deleting a single staff member.
    """
    def get_object(self, pk):
        try:
            return Staff.objects.get(pk=pk)
        except Staff.DoesNotExist:
            return None

    def get(self, request, pk):
        staff = self.get_object(pk)
        if not staff:
            return Response({"error": "Staff member not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = StaffSerializer(staff)
        return Response(serializer.data)

    def patch(self, request, pk):
        staff = self.get_object(pk)
        if not staff:
            return Response({"error": "Staff member not found"}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = StaffSerializer(staff, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        staff = self.get_object(pk)
        if not staff:
            return Response({"error": "Staff member not found"}, status=status.HTTP_404_NOT_FOUND)
        staff.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)