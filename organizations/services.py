from django.db import transaction

from .models import Organization, OrganizationMembership


@transaction.atomic
def ensure_lister_organization(user):
    """Return the stable self-service organization owned by this user."""
    membership = next((item for item in OrganizationMembership.objects.select_related('organization')
                       .filter(user=user, status=OrganizationMembership.STATUS_ACTIVE,
                               all_properties=True).order_by('id')
                       if 'owner' in (item.roles or [])), None)
    if membership:
        return membership.organization, membership
    organization = Organization.objects.create(name=f'{user.get_full_name().strip() or user.username} listings')
    membership = OrganizationMembership.objects.create(
        user=user, organization=organization, roles=['owner'], all_properties=True)
    return organization, membership
