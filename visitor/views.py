from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Visitor
from .serializers import VisitorSerializer
from organizations.access import properties_accessible_to
from organizations.legacy import require_posted_property_access

class VisitorAPIView(APIView):
    def get(self, request):
        # Filters visitors based on the property selected in the dashboard
        property_id = request.query_params.get('property_id')
        
        if property_id:
            queryset = Visitor.objects.filter(property_id=property_id, property__in=properties_accessible_to(request.user)).order_by('-entry_time')
        else:
            queryset = Visitor.objects.filter(property__in=properties_accessible_to(request.user)).order_by('-entry_time')
            
        serializer = VisitorSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        require_posted_property_access(request, 'property.manage')
        serializer = VisitorSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VisitorDetailAPIView(APIView):
    def patch(self, request, pk):
        """ Used for checking out a visitor (updating exit_time) """
        try:
            visitor = Visitor.objects.get(pk=pk, property__in=properties_accessible_to(request.user, 'property.manage'))
            serializer = VisitorSerializer(visitor, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Visitor.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
