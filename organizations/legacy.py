from rest_framework.exceptions import NotFound, PermissionDenied

from .access import properties_accessible_to


def accessible_property_ids(user, permission='property.view'):
    return properties_accessible_to(user, permission).values_list('pk', flat=True)


def require_posted_property_access(request, permission='property.manage'):
    property_id = request.data.get('property') or request.data.get('property_id')
    if property_id is None:
        return None
    prop = properties_accessible_to(request.user, permission).filter(pk=property_id).first()
    if prop is None:
        # Hide whether an ID exists outside the caller's scope.
        raise NotFound('Property not found.')
    return prop
