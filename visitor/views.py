from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Visitor
from .serializers import VisitorSerializer

class VisitorAPIView(APIView):
    def get(self, request):
        # Filters visitors based on the property selected in the dashboard
        property_id = request.query_params.get('property_id')
        
        if property_id:
            queryset = Visitor.objects.filter(property_id=property_id).order_by('-entry_time')
        else:
            queryset = Visitor.objects.all().order_by('-entry_time')
            
        serializer = VisitorSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = VisitorSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VisitorDetailAPIView(APIView):
    def patch(self, request, pk):
        """ Used for checking out a visitor (updating exit_time) """
        try:
            visitor = Visitor.objects.get(pk=pk)
            serializer = VisitorSerializer(visitor, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Visitor.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)