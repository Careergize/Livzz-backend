from django.db.models import Q

from .models import Organization, OrganizationMembership


ROLE_PERMISSIONS = {
    'owner': {'organization.view', 'organization.manage', 'property.view', 'property.manage',
              'listing.view', 'listing.manage', 'listing.publish', 'tenant.view', 'tenant.manage',
              'billing.view', 'billing.manage', 'billing.collect', 'maintenance.view',
              'maintenance.manage', 'maintenance.assign', 'staff.view', 'staff.manage',
              'documents.view', 'documents.manage'},
    'manager': {'organization.view', 'property.view', 'property.manage', 'listing.view',
                'listing.manage', 'listing.publish', 'tenant.view', 'tenant.manage',
                'billing.view', 'maintenance.view', 'maintenance.manage', 'maintenance.assign',
                'staff.view', 'staff.manage', 'documents.view', 'documents.manage'},
    'staff': {'organization.view', 'property.view', 'listing.view', 'tenant.view',
              'maintenance.view', 'maintenance.manage', 'documents.view'},
    'accountant': {'organization.view', 'property.view', 'tenant.view', 'billing.view',
                   'billing.manage', 'billing.collect', 'documents.view'},
}


def permissions_for_membership(membership):
    permissions = set()
    for role in membership.roles or []:
        permissions.update(ROLE_PERMISSIONS.get(role, set()))
    return permissions


def memberships_for(user):
    if not user or not user.is_authenticated:
        return OrganizationMembership.objects.none()
    return OrganizationMembership.objects.filter(user=user, status=OrganizationMembership.STATUS_ACTIVE)


def organizations_accessible_to(user):
    if not user or not user.is_authenticated:
        return Organization.objects.none()
    if user.is_superuser:
        return Organization.objects.all()
    return Organization.objects.filter(memberships__in=memberships_for(user)).distinct()


def properties_accessible_to(user, permission='property.view'):
    from property.models import Property
    if not user or not user.is_authenticated:
        return Property.objects.none()
    if user.is_superuser:
        return Property.objects.all()
    memberships = [m for m in memberships_for(user).prefetch_related('property_accesses')
                   if permission in permissions_for_membership(m)]
    query = Q(pk__in=[])
    for membership in memberships:
        if membership.all_properties:
            query |= Q(organization=membership.organization)
        else:
            query |= Q(pk__in=membership.property_accesses.values('property_id'))
    return Property.objects.filter(query).distinct()


def user_can(user, permission, obj=None):
    if user and user.is_authenticated and user.is_superuser:
        return True
    if obj is None:
        return any(permission in permissions_for_membership(m) for m in memberships_for(user))
    organization = obj if isinstance(obj, Organization) else getattr(obj, 'organization', None)
    prop = None if isinstance(obj, Organization) else (obj if obj.__class__.__name__ == 'Property' else getattr(obj, 'property', None))
    for membership in memberships_for(user).filter(organization=organization):
        if permission not in permissions_for_membership(membership):
            continue
        if prop is None or membership.all_properties or membership.property_accesses.filter(property=prop).exists():
            return True
    return False
