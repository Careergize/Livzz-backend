"""Global API Views"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from property.models import Location
from property.serializers import LocationSerializer


class LocationsView(APIView):
    """API to fetch all locations"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        locations = Location.objects.all().order_by('name')
        serializer = LocationSerializer(locations, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
