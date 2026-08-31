from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from organizations.access import memberships_for, organizations_accessible_to, properties_accessible_to
from organizations.models import Organization
from .pagination import V2PageNumberPagination
from .responses import data_response
from .serializers import MembershipSerializer, OrganizationSerializer, V2PropertySerializer


class V2APIView(APIView):
    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        detail = response.data.get('detail') if isinstance(response.data, dict) else None
        code = getattr(detail, 'code', None) or getattr(exc, 'default_code', 'error')
        message = str(detail if detail is not None else exc)
        response.data = {'errors': [{'code': code, 'field': None, 'message': message}]}
        return response


class MeView(V2APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = memberships_for(request.user).select_related('organization')
        user = request.user
        return data_response({'user': {
            'id': user.pk, 'username': user.username, 'phone_number': user.phone_number,
            'first_name': user.first_name, 'last_name': user.last_name, 'email': user.email,
            'legacy_role': user.role,
        }, 'memberships': MembershipSerializer(memberships, many=True).data})


class MembershipListView(V2APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = memberships_for(request.user).select_related('organization')
        return data_response(MembershipSerializer(memberships, many=True).data)


class OrganizationListView(V2APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = organizations_accessible_to(request.user).order_by('name')
        paginator = V2PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(OrganizationSerializer(page, many=True).data)


class OrganizationDetailView(V2APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        organization = get_object_or_404(organizations_accessible_to(request.user), public_id=organization_id)
        return data_response(OrganizationSerializer(organization).data)


class OrganizationPropertyListView(V2APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        organization = get_object_or_404(organizations_accessible_to(request.user), public_id=organization_id)
        queryset = properties_accessible_to(request.user).filter(organization=organization).order_by('-created_at')
        paginator = V2PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(V2PropertySerializer(page, many=True).data)
