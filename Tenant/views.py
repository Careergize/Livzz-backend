# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from .models import Tenant
from .serializers import TenantSerializer
from organizations.access import properties_accessible_to
from organizations.legacy import require_posted_property_access

class TenantListCreateAPIView(APIView):
    # Parser classes allow the API to handle file uploads (images)
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request):
        """Fetch all tenants"""
        tenants = Tenant.objects.filter(property__in=properties_accessible_to(request.user, 'tenant.view')).order_by('-created_at')
        serializer = TenantSerializer(tenants, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Add a new tenant with ID proof"""
        require_posted_property_access(request, 'tenant.manage')
        serializer = TenantSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TenantDetailAPIView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request, pk):
        """Fetch a single tenant's details"""
        tenant = get_object_or_404(Tenant, pk=pk, property__in=properties_accessible_to(request.user, 'tenant.view'))
        serializer = TenantSerializer(tenant)
        return Response(serializer.data)

    def patch(self, request, pk):
        """Update tenant (e.g., changing room or uploading new ID)"""
        tenant = get_object_or_404(Tenant, pk=pk, property__in=properties_accessible_to(request.user, 'tenant.manage'))
        serializer = TenantSerializer(tenant, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Remove a tenant"""
        tenant = get_object_or_404(Tenant, pk=pk, property__in=properties_accessible_to(request.user, 'tenant.manage'))
        tenant.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
