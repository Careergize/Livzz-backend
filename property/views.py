from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .models import Property
from .serializers import PropertyDetailSerializer
from django.shortcuts import get_object_or_404

class PropertyListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # 1. Fetch all active properties from DB
        properties = Property.objects.filter(is_active=True)
        
        # 2. Serialize the data (convert to JSON format)
        # context={'request': request} ensures absolute URLs for images
        serializer = PropertyDetailSerializer(properties, many=True, context={'request': request})
        
        # 3. Return the response
        return Response(serializer.data, status=status.HTTP_200_OK)

class PropertyDetailAPIView(APIView):
    """
    Retrieve details of a single property including its room configurations.
    """
    def get(self, request, pk, format=None):
        try:
            # Fetch property or return 404
            property_obj = get_object_or_404(Property, pk=pk)
            
            # Serialize the data
            serializer = PropertyDetailSerializer(property_obj, context={'request': request})
            
            # Return JSON response
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )